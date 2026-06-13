from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import uuid

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
    视觉对话请求接口（PR5 阶段）。

    本次只完成：
    - 接收 multipart/form-data 请求
    - 校验问题文本和图片
    - 计算图片 SHA-256
    - 返回请求接收结果

    本次不调用任何 AI 模型，不保存图片，不持久化任何数据。
    """
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

    # 图片读取后保持在内存中，不落盘、不入库、不输出到日志
    return {
        "status": "accepted",
        "message": "视觉对话请求已接收，当前尚未接入 AI 模型",
        "request_id": str(uuid.uuid4()),
        "question": question_clean,
        "image": {
            "filename": image.filename or "snapshot.jpg",
            "content_type": content_type,
            "size_bytes": len(image_bytes),
            "sha256": sha256
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
