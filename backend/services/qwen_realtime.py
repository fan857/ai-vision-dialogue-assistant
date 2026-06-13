"""
阿里云百炼 Qwen3.5-Omni-Flash-Realtime 实时语音客户端（PR8）。

职责：
- 异步连接 DashScope Realtime WebSocket
- 发送 session.update（音频配置、工具定义、voice、转写）
- 转发前端麦克风音频（input_audio_buffer.append）
- 接收用户转写、AI 文本、音频和 Function Calling 事件
- 解析 analyze_current_frame 工具调用并复用现有 Doubao 视觉服务
- 通过回调把事件透传给 FastAPI WebSocket
- 处理连接关闭与异常

参考：
- DashScope Realtime 协议基于 OpenAI Realtime 兼容协议
- wss://dashscope.aliyuncs.com/api-ws/v1/realtime
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from dotenv import load_dotenv

from .vision_model import VisionModelError, call_vision_model

logger = logging.getLogger(__name__)

# 默认配置常量
DEFAULT_QWEN_REALTIME_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
DEFAULT_QWEN_REALTIME_MODEL = "qwen3.5-omni-flash-realtime"
DEFAULT_QWEN_REALTIME_VOICE = "Tina"

# 工具名（与 Qwen 会话中注册的 name 完全一致）
TOOL_ANALYZE_FRAME = "analyze_current_frame"


def _load_env() -> None:
    """从 backend/.env 加载配置（如果存在）。"""
    try:
        # main.py 已经加载过一次了，这里再加载一次也无副作用
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(backend_dir, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load .env in qwen_realtime: %s", e)


def _get_config() -> Dict[str, str]:
    _load_env()
    return {
        "api_key": (os.getenv("DASHSCOPE_API_KEY") or "").strip(),
        "url": (os.getenv("QWEN_REALTIME_URL") or DEFAULT_QWEN_REALTIME_URL).strip(),
        "model": (os.getenv("QWEN_REALTIME_MODEL") or DEFAULT_QWEN_REALTIME_MODEL).strip(),
        "voice": (os.getenv("QWEN_REALTIME_VOICE") or DEFAULT_QWEN_REALTIME_VOICE).strip(),
    }


# 工具定义：analyze_current_frame
TOOLS_DEF = [
    {
        "type": "function",
        "name": TOOL_ANALYZE_FRAME,
        "description": (
            "当用户询问当前摄像头截图中的人物、物体、文字、动作、"
            "位置或场景时调用。返回该画面针对问题的真实视觉理解结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "用户针对当前画面的具体问题",
                }
            },
            "required": ["question"],
        },
    }
]


SYSTEM_PROMPT = (
    "你是 AI 视觉语音助手。"
    "当用户询问当前画面中的人物、物体、文字、动作、位置或场景时，"
    "必须调用 analyze_current_frame 工具，不要自行猜测图片内容。"
    "获得工具结果后，用简洁、自然、适合口语朗读的中文回答。"
    "非视觉问题可以直接回答。"
)


def build_session_update(model: str, voice: str) -> Dict[str, Any]:
    """构造 session.update 事件 payload。"""
    return {
        "type": "session.update",
        "session": {
            "model": model,
            "modalities": ["text", "audio"],
            "voice": voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "gummy-realtime-v1"},
            "turn_detection": {
                "type": "semantic_vad",
                # semantic_vad / server_vad 在不同 DashScope 版本下行为略有差异
                # 这里使用较保守的默认值
            },
            "tools": TOOLS_DEF,
            "tool_choice": "auto",
            "instructions": SYSTEM_PROMPT,
        },
    }


class QwenRealtimeSession:
    """
    单个语音会话的代理。

    生命周期：
    - open(cfg, frame_bytes, content_type) -> 建立到 Qwen 的连接并发送 session.update
    - send_audio(pcm_bytes) -> 把麦克风 PCM 追加到 Qwen
    - send_cancel() / send_response_cancel() -> 取消当前响应
    - close() -> 关闭
    """

    def __init__(
        self,
        on_event: Callable[[Dict[str, Any]], Awaitable[None]],
        on_audio_delta: Callable[[bytes], Awaitable[None]],
        on_log: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self._on_event = on_event
        self._on_audio_delta = on_audio_delta
        self._on_log = on_log
        self._ws: Optional[Any] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._closed = False
        # 当前响应累积的 function_call：item_id -> {"name": str, "arguments": str}
        self._pending_function_calls: Dict[str, Dict[str, str]] = {}
        # 当前响应累积的 assistant 文本（用于 function_call 路径调试）
        self._pending_assistant_text: Dict[str, str] = {}

    # ===== 公开方法 =====
    async def open(self, frame_bytes: bytes, content_type: str) -> None:
        cfg = _get_config()
        if not cfg["api_key"]:
            raise QwenRealtimeError(
                "后端未配置 DASHSCOPE_API_KEY，无法连接阿里云百炼实时语音服务。",
                error_type="config_error",
            )

        if not frame_bytes:
            raise QwenRealtimeError(
                "当前没有可用画面，请先打开摄像头并截取当前画面。",
                error_type="no_frame",
            )
        if len(frame_bytes) > 2 * 1024 * 1024:
            raise QwenRealtimeError(
                "图片超过 2 MB，无法用于实时视觉问答。",
                error_type="frame_too_large",
            )

        # 把图片和 content_type 保存在闭包中，工具调用时使用
        self._frame_bytes = frame_bytes
        self._content_type = (content_type or "image/jpeg").lower()

        url = f"{cfg['url']}?model={cfg['model']}"
        headers = [
            ("Authorization", f"Bearer {cfg['api_key']}"),
        ]

        try:
            self._ws = await websockets.connect(
                url,
                additional_headers=headers,
                max_size=16 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
            )
        except Exception as e:  # noqa: BLE001
            raise QwenRealtimeError(
                f"无法连接阿里云百炼实时语音服务：{type(e).__name__}",
                error_type="connect_error",
            ) from e

        # 发送 session.update
        await self._send_json(build_session_update(cfg["model"], cfg["voice"]))

        # 启动读取循环
        self._reader_task = asyncio.create_task(self._read_loop())

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """把浏览器传来的 16kHz 16bit mono PCM 二进制追加到 Qwen。"""
        if self._closed or not self._ws:
            return
        if not pcm_bytes:
            return
        b64 = base64.b64encode(pcm_bytes).decode("ascii")
        await self._send_json(
            {
                "type": "input_audio_buffer.append",
                "audio": b64,
            }
        )

    async def send_response_cancel(self) -> None:
        """取消当前正在生成的响应。"""
        if self._closed or not self._ws:
            return
        try:
            await self._send_json({"type": "response.cancel"})
        except Exception as e:  # noqa: BLE001
            logger.warning("response.cancel failed: %s", e)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None
        if self._reader_task:
            try:
                self._reader_task.cancel()
            except Exception:  # noqa: BLE001
                pass
            self._reader_task = None
        # 释放图片
        self._frame_bytes = b""

    # ===== 内部 =====
    async def _send_json(self, payload: Dict[str, Any]) -> None:
        if not self._ws:
            return
        try:
            await self._ws.send(json.dumps(payload, ensure_ascii=False))
        except ConnectionClosed:
            self._closed = True
        except Exception as e:  # noqa: BLE001
            logger.warning("send_json failed: %s", e)

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if isinstance(raw, (bytes, bytearray)):
                    # 百炼 Realtime 一般不通过二进制帧下行音频
                    # 若有，按 24kHz pcm16 直接转发
                    try:
                        await self._on_audio_delta(bytes(raw))
                    except Exception:  # noqa: BLE001
                        pass
                    continue

                try:
                    evt = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue

                etype = evt.get("type") or ""

                # 透传给上层
                try:
                    await self._on_event(evt)
                except Exception:  # noqa: BLE001
                    logger.exception("on_event handler failed")

                # 处理音频分片
                if etype == "response.audio.delta":
                    audio_b64 = evt.get("delta")
                    if audio_b64:
                        try:
                            await self._on_audio_delta(base64.b64decode(audio_b64))
                        except Exception:  # noqa: BLE001
                            logger.exception("audio delta decode failed")

                # 处理 Function Calling
                if etype == "response.output_item.added":
                    item = evt.get("item") or {}
                    if item.get("type") == "function_call":
                        item_id = item.get("id") or evt.get("item_id") or ""
                        name = item.get("name") or ""
                        self._pending_function_calls[item_id] = {
                            "name": name,
                            "arguments": "",
                            "call_id": item.get("call_id") or "",
                        }

                elif etype == "response.function_call_arguments.delta":
                    item_id = (
                        evt.get("item_id")
                        or evt.get("response_id")
                        or ""
                    )
                    delta = evt.get("delta") or ""
                    fc = self._pending_function_calls.get(item_id)
                    if fc is not None:
                        fc["arguments"] += delta

                elif etype == "response.function_call_arguments.done":
                    item_id = (
                        evt.get("item_id")
                        or evt.get("response_id")
                        or ""
                    )
                    arguments = evt.get("arguments") or ""
                    fc = self._pending_function_calls.get(item_id)
                    if fc is not None:
                        fc["arguments"] = arguments
                        # 触发工具执行
                        asyncio.create_task(self._run_function_call(item_id, fc))

                elif etype == "response.done" or etype == "response.completed":
                    # 清空累积
                    self._pending_function_calls.clear()
                    self._pending_assistant_text.clear()

                elif etype == "error":
                    msg = evt.get("error") or evt
                    logger.warning(
                        "Qwen realtime error event: %s",
                        json.dumps(msg, ensure_ascii=False)[:300],
                    )
                    try:
                        await self._on_event(
                            {"type": "server.error", "error": msg}
                        )
                    except Exception:  # noqa: BLE001
                        pass
        except ConnectionClosed:
            pass
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("Qwen realtime read loop crashed")
        finally:
            # 通知上层连接已关闭
            try:
                await self._on_event({"type": "server.disconnected"})
            except Exception:  # noqa: BLE001
                pass

    async def _run_function_call(
        self, item_id: str, fc: Dict[str, str]
    ) -> None:
        """执行 analyze_current_frame 工具并回传结果给 Qwen。"""
        name = fc.get("name") or ""
        args_raw = fc.get("arguments") or "{}"
        call_id = fc.get("call_id") or item_id

        if name != TOOL_ANALYZE_FRAME:
            output = "未知工具，无法执行。"
        else:
            try:
                args = json.loads(args_raw) if args_raw.strip().startswith("{") else {}
            except Exception:  # noqa: BLE001
                args = {}
            question = (args.get("question") or "").strip()
            if not question:
                output = "工具调用缺少 question 参数。"
            else:
                # 通知前端：开始分析画面
                try:
                    await self._on_event(
                        {
                            "type": "vision.analyzing",
                            "question": question,
                        }
                    )
                except Exception:  # noqa: BLE001
                    pass
                # 调用 Doubao 视觉服务（PR6）
                try:
                    res = await call_vision_model(
                        question=question,
                        image_bytes=self._frame_bytes,
                        content_type=self._content_type,
                        request_id=item_id,
                    )
                    output = res.get("answer") or "豆包视觉服务未返回内容。"
                except VisionModelError as e:
                    output = f"视觉服务调用失败：{e.message}"
                except Exception as e:  # noqa: BLE001
                    output = f"视觉服务异常：{type(e).__name__}"

        # 通知前端：分析完成
        try:
            await self._on_event(
                {
                    "type": "vision.analyzed",
                    "question": fc.get("arguments") or "",
                    "output_excerpt": (output or "")[:200],
                }
            )
        except Exception:  # noqa: BLE001
            pass

        # 回传 function_call_output
        await self._send_json(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output,
                },
            }
        )

        # 触发最终响应生成
        await self._send_json({"type": "response.create"})


class QwenRealtimeError(Exception):
    """Qwen Realtime 错误，包含 error_type 便于上层分类。"""

    def __init__(self, message: str, error_type: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
