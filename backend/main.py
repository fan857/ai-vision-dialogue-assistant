from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
import base64
import json
import logging
import os
import uuid
from typing import Any, Dict

from dotenv import load_dotenv

from services.vision_model import VisionModelError
from services.vision_service import (
    VisionService,
    VisionServiceError,
    get_vision_service,
    hash_image,
)
from services.qwen_realtime import (
    QwenRealtimeError,
    QwenRealtimeSession,
)

# 加载 backend/.env（如果存在）
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH, override=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI 视觉对话助手 API")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 常量 =====
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_QUESTION_LENGTH = 1000


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "message": "服务运行正常",
        "version": "1.0.0"
    }


@app.post("/api/vision-dialogue")
async def vision_dialogue(
    question: str = Form(...),
    image: UploadFile = File(...)
):
    """
    视觉对话请求接口（PR6 阶段）。

    本次完成：
    - 接收 multipart/form-data 请求
    - 校验问题文本和图片
    - 计算图片 SHA-256
    - 调用火山方舟 Coding Plan Doubao-Seed-2.0-Pro 视觉模型
    - 返回真实 AI 回答（不伪造）

    本次不做：
    - 不保存图片、不入数据库
    - 不输出图片 Base64
    - 不自动重试、不使用流式响应
    - 不自动切换到 /api/v3
    """
    request_id = str(uuid.uuid4())

    # ===== 问题校验 =====
    question_clean = (question or "").strip()
    if not question_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问题不能为空"
        )
    if len(question_clean) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"问题长度超过限制（最大 {MAX_QUESTION_LENGTH} 字符）"
        )

    # ===== 图片格式校验 =====
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 JPEG、PNG 或 WebP 图片"
        )

    # ===== 读取并校验图片大小 / 计算 SHA-256 =====
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片内容为空"
        )
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"图片大小超过限制（最大 {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB）"
        )

    # ===== 走统一视觉服务（带缓存 / 去重 / 耗时） =====
    logger.info(
        "Vision dialogue request received. request_id=%s question_len=%d image_size=%d",
        request_id, len(question_clean), len(image_bytes),
    )

    service: VisionService = get_vision_service()
    try:
        result = await service.analyze(
            question=question_clean,
            image_bytes=image_bytes,
            content_type=content_type,
            request_id=request_id,
        )
    except (VisionModelError, VisionServiceError) as e:
        logger.warning(
            "Vision service call failed. request_id=%s error_type=%s status=%s",
            request_id, e.error_type, e.status_code,
        )
        # 图片读取后保持在内存中，错误路径上不落盘、不入库、不输出到日志
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "Unexpected error in vision service call. request_id=%s", request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="视觉模型调用出现未预期错误，请稍后重试。",
        )

    logger.info(
        "Vision dialogue completed. request_id=%s model=%s answer_len=%d cache_hit=%s total_ms=%d model_request_ms=%d",
        request_id,
        result.get("model"),
        len(result.get("answer") or ""),
        (result.get("cache") or {}).get("hit"),
        (result.get("timing") or {}).get("total_ms"),
        (result.get("timing") or {}).get("model_request_ms"),
    )

    return {
        "status": "success",
        "message": "AI 已完成视觉分析",
        "request_id": request_id,
        "answer": result["answer"],
        "model": result["model"],
        "question": question_clean,
        "image": result["image"],
        "usage": result.get("usage"),
        "cache": result.get("cache"),
        "timing": result.get("timing"),
    }


# ============================================================================
# PR8 - 实时语音视觉对话 WebSocket
# ============================================================================

# WebSocket 允许跨域（同源在 Vite 代理下已支持，ws://localhost:5173 -> ws://localhost:3001）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "ws://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 允许的实时会话图片格式与大小
REALTIME_ALLOWED_IMAGE_TYPES = ALLOWED_IMAGE_TYPES
REALTIME_MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_BYTES

# 默认图片元数据
REALTIME_DEFAULT_CONTENT_TYPE = "image/jpeg"


@app.websocket("/ws/realtime-voice")
async def ws_realtime_voice(websocket: WebSocket):
    """
    实时语音视觉对话 WebSocket 代理（PR8）。

    协议（与前端约定）：
    - 第 1 条消息（text JSON）：会话初始化
        {
          "type": "session.init",
          "image_base64": "...",
          "content_type": "image/jpeg"
        }
      后端返回 {"type": "session.ready"} 或 {"type": "session.error", "message": "..."}
    - 后续 binary 帧：16kHz 16bit 单声道 PCM 音频（直接转发到 Qwen）
    - 控制消息（text JSON）：
        {"type": "cancel"}  -> 取消当前响应
        {"type": "ping"}    -> 心跳
    - 关闭：客户端断开即可

    服务端 -> 客户端事件：直接透传 Qwen Realtime 的 JSON 事件，额外补充：
        {"type": "server.error", "error": "..."}
        {"type": "server.disconnected"}
        {"type": "vision.analyzing", "question": "..."}
        {"type": "vision.analyzed", "question": "...", "output_excerpt": "..."}
    - 音频下行：二进制帧（24kHz 16bit 单声道 PCM），与 JSON 事件分离
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info("Realtime WS opened. session_id=%s", session_id)

    # 会话状态
    qwen_session: QwenRealtimeSession | None = None
    frame_bytes: bytes = b""
    content_type: str = REALTIME_DEFAULT_CONTENT_TYPE
    initialized: bool = False

    async def forward_event(evt: Dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(evt, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            pass

    async def forward_audio(pcm: bytes) -> None:
        if not pcm:
            return
        try:
            await websocket.send_bytes(pcm)
        except Exception:  # noqa: BLE001
            pass

    try:
        while True:
            msg = await websocket.receive()

            if msg.get("type") == "websocket.disconnect":
                break

            if "bytes" in msg and msg["bytes"] is not None:
                if not initialized or qwen_session is None:
                    continue
                try:
                    await qwen_session.send_audio(msg["bytes"])
                except Exception as e:  # noqa: BLE001
                    logger.warning("send_audio failed: %s", e)
                continue

            if "text" in msg and msg["text"] is not None:
                raw = msg["text"]
                try:
                    payload = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                ptype = payload.get("type")

                if ptype == "ping":
                    try:
                        await websocket.send_text(
                        json.dumps({"type": "pong"}, ensure_ascii=False)
                    )
                    except Exception:  # noqa: BLE001
                        pass
                    continue

                if ptype == "cancel":
                    if qwen_session is not None:
                        await qwen_session.send_response_cancel()
                    continue

                if ptype == "session.init":
                    # 解析图片
                    b64 = (payload.get("image_base64") or "").strip()
                    ct = (payload.get("content_type") or "").lower().strip()
                    if not b64:
                        await forward_event(
                            {"type": "session.error", "message": "缺少 image_base64"}
                        )
                        continue
                    if not ct or ct not in REALTIME_ALLOWED_IMAGE_TYPES:
                        ct = REALTIME_DEFAULT_CONTENT_TYPE
                    try:
                        frame_bytes = base64.b64decode(b64, validate=True)
                    except Exception:  # noqa: BLE001
                        await forward_event(
                            {"type": "session.error", "message": "image_base64 无法解析"}
                        )
                        continue
                    if not frame_bytes:
                        await forward_event(
                            {"type": "session.error", "message": "图片内容为空"}
                        )
                        continue
                    if len(frame_bytes) > REALTIME_MAX_IMAGE_SIZE_BYTES:
                        await forward_event(
                            {"type": "session.error", "message": "图片超过 2 MB"}
                        )
                        continue
                    content_type = ct

                    # 建立到 Qwen 的会话
                    try:
                        qwen_session = QwenRealtimeSession(
                            on_event=forward_event,
                            on_audio_delta=forward_audio,
                        )
                        await qwen_session.open(
                            frame_bytes=frame_bytes,
                            content_type=content_type,
                        )
                        initialized = True
                        await forward_event({"type": "session.ready"})
                    except QwenRealtimeError as e:
                        logger.warning(
                            "Qwen realtime open failed. session_id=%s error_type=%s",
                            session_id, e.error_type,
                        )
                        await forward_event(
                            {"type": "session.error", "message": e.message}
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.exception(
                            "Unexpected error opening qwen session. session_id=%s", session_id
                        )
                        await forward_event(
                            {
                                "type": "session.error",
                                "message": f"实时会话启动失败：{type(e).__name__}",
                            }
                        )
                    continue

                # 其它类型暂不处理
                continue

    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Realtime WS loop crashed. session_id=%s", session_id)
    finally:
        # 清理：关闭 Qwen 会话 + 释放图片
        if qwen_session is not None:
            try:
                await qwen_session.close()
            except Exception:  # noqa: BLE001
                pass
        frame_bytes = b""
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Realtime WS closed. session_id=%s", session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
