from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import logging
import uuid

from services.vision_model import VisionModelError, call_vision_model

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

    sha256 = hashlib.sha256(image_bytes).hexdigest()

    # ===== 调用视觉模型 =====
    logger.info(
        "Vision dialogue request received. request_id=%s question_len=%d image_size=%d",
        request_id, len(question_clean), len(image_bytes),
    )

    try:
        model_result = await call_vision_model(
            question=question_clean,
            image_bytes=image_bytes,
            content_type=content_type,
            request_id=request_id,
        )
    except VisionModelError as e:
        logger.warning(
            "Vision model call failed. request_id=%s error_type=%s status=%s",
            request_id, e.error_type, e.status_code,
        )
        # 图片读取后保持在内存中，错误路径上不落盘、不入库、不输出到日志
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(
            "Unexpected error in vision model call. request_id=%s", request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="视觉模型调用出现未预期错误，请稍后重试。",
        )

    logger.info(
        "Vision dialogue completed. request_id=%s model=%s answer_len=%d",
        request_id, model_result.get("model"), len(model_result.get("answer") or ""),
    )

    return {
        "status": "success",
        "message": "AI 已完成视觉分析",
        "request_id": request_id,
        "answer": model_result["answer"],
        "model": model_result["model"],
        "question": question_clean,
        "image": {
            "content_type": content_type,
            "size_bytes": len(image_bytes),
            "sha256": sha256,
        },
        "usage": model_result.get("usage"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
