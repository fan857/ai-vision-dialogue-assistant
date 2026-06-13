"""
火山方舟 Coding Plan 视觉模型服务。

本模块负责：
- 从环境变量读取模型配置（API Key、Base URL、模型名等）
- 将图片字节编码为 Base64 Data URL
- 构造 OpenAI 兼容格式的多模态请求
- 通过 httpx.AsyncClient 异步调用 /chat/completions
- 提取模型真实回答（不伪造、不缓存、不重试）
- 处理上游错误（按错误类型返回明确的状态码与脱敏信息）

注意：
- 禁止使用 OpenAI SDK，仅使用 httpx + python-dotenv
- 禁止记录 API Key、Authorization 头或图片 Base64
- 禁止自动重试、不使用流式响应
- 禁止自动切换到 /api/v3（避免产生 Coding Plan 之外的费用）
"""

import base64
import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


# ===== 默认配置（仅在被环境变量覆盖时使用） =====
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"
DEFAULT_MODEL = "doubao-seed-2.0-pro"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_TOKENS = 300


class VisionModelError(Exception):
    """视觉模型调用错误。"""

    def __init__(self, message: str, status_code: int = 502, error_type: str = "upstream_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


def _load_config() -> Dict[str, Any]:
    """
    从环境变量加载配置。

    允许通过 backend/.env 文件覆盖（开发环境）。
    """
    try:
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
    except Exception as e:  # noqa: BLE001
        # 加载 .env 失败不应阻塞服务启动
        logger.warning("Failed to load .env file: %s", e)

    api_key = (os.getenv("ARK_API_KEY") or "").strip()
    base_url = (os.getenv("ARK_API_BASE") or DEFAULT_BASE_URL).strip().rstrip("/")
    model = (os.getenv("ARK_MODEL") or DEFAULT_MODEL).strip()

    try:
        timeout_seconds = int(os.getenv("ARK_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT_SECONDS)
    except ValueError:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    try:
        max_tokens = int(os.getenv("ARK_MAX_TOKENS") or DEFAULT_MAX_TOKENS)
    except ValueError:
        max_tokens = DEFAULT_MAX_TOKENS

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "max_tokens": max_tokens,
    }


def _ensure_coding_plan_base(base_url: str) -> None:
    """
    安全检查：禁止自动切换到 /api/v3（避免产生 Coding Plan 之外的费用）。

    只接受形如 .../api/coding/v3 的 Base URL。
    """
    if "/api/coding/v3" not in base_url:
        raise VisionModelError(
            "当前 PR6 只允许使用火山方舟 Coding Plan 端点（必须包含 /api/coding/v3）。"
            "为避免产生 Coding Plan 之外的费用，已拒绝继续调用。",
            status_code=500,
            error_type="config_error",
        )


def build_image_data_url(content_type: str, image_bytes: bytes) -> str:
    """
    将图片字节编码为 Base64 Data URL（OpenAI 兼容格式）。
    """
    if not image_bytes:
        raise VisionModelError("图片内容为空", status_code=400, error_type="bad_request")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    ct = (content_type or "image/jpeg").lower()
    return f"data:{ct};base64,{encoded}"


def _safe_status(status_code: int) -> int:
    """防止把上游 5xx 直接透传给前端造成混淆，统一收敛为 502/504。"""
    if status_code in (401, 403):
        return 401
    if status_code == 404:
        return 404
    if status_code == 408:
        return 504
    if status_code == 429:
        return 429
    if status_code >= 500:
        return 502
    return 502


def _describe_error(status_code: int, body_text: str) -> Tuple[int, str, str]:
    """
    根据上游 HTTP 状态码和响应体，生成脱敏的友好错误描述。

    不会回显原始 body，避免泄漏内部信息。
    """
    text = (body_text or "").lower()
    if status_code in (401, 403):
        return (
            _safe_status(status_code),
            "视觉模型鉴权失败，请检查 ARK_API_KEY 是否正确或是否有 Coding Plan 权限。",
            "auth_error",
        )
    if status_code == 404:
        return (
            404,
            "视觉模型端点或模型名称未找到，请确认 ARK_API_BASE 与 ARK_MODEL 配置。",
            "not_found",
        )
    if status_code == 408:
        return (504, "视觉模型请求超时，请稍后重试。", "timeout")
    if status_code == 429:
        return (429, "视觉模型请求被限流，请稍后重试。", "rate_limited")
    if status_code >= 500:
        return (502, "视觉模型服务暂时不可用，请稍后重试。", "upstream_error")
    # 其它状态码
    if "image" in text and ("not support" in text or "unsupported" in text):
        return (
            400,
            "当前模型不支持图片输入，请联系七牛云/火山方舟确认 doubao-seed-2.0-pro 是否支持视觉能力。",
            "image_not_supported",
        )
    if "model" in text and ("not exist" in text or "invalid" in text or "unknown" in text):
        return (
            404,
            "模型名称不被识别，请确认 ARK_MODEL 是否正确。",
            "model_invalid",
        )
    if "coding plan" in text or "subscribe" in text or "subscription" in text:
        return (
            401,
            "当前账号没有 Coding Plan 订阅，请检查火山方舟 Coding Plan 授权状态。",
            "no_coding_plan",
        )
    return (502, "视觉模型调用失败，请稍后重试。", "upstream_error")


async def call_vision_model(
    *,
    question: str,
    image_bytes: bytes,
    content_type: str,
    request_id: str,
) -> Dict[str, Any]:
    """
    调用 Coding Plan Doubao-Seed-2.0-Pro 视觉模型。

    Returns:
        {
            "answer": str,
            "model": str,
            "usage": Optional[Dict[str, int]],
        }

    Raises:
        VisionModelError: 当配置缺失、调用失败、响应结构异常或回答为空时抛出。
    """
    cfg = _load_config()

    if not cfg["api_key"]:
        raise VisionModelError(
            "后端未配置 ARK_API_KEY，无法调用视觉模型。",
            status_code=500,
            error_type="config_error",
        )

    _ensure_coding_plan_base(cfg["base_url"])

    image_data_url = build_image_data_url(content_type, image_bytes)

    url = f"{cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是可靠的 AI 视觉对话助手。"
                    "请仔细观察整张图片（包括边缘、角落、人物的手部、桌面、背景）。"
                    "用户经常把想让你看的物体举在画面中央或一侧，请主动扫描整个画面寻找。"
                    "只描述能够确认的内容；"
                    "如果在画面中看到了相关物体，请直接、明确地回答（颜色、形状、类别、可能的物品名）。"
                    "如果确实无法看到任何相关物体，再说明'画面中未看到'，并建议用户调整角度或重新截取。"
                    "注意：物体在边缘、较小或被部分遮挡时也要尽量识别，不要轻易放弃。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                    {
                        "type": "text",
                        "text": question,
                    },
                ],
            },
        ],
        "max_tokens": cfg["max_tokens"],
    }

    timeout = httpx.Timeout(cfg["timeout_seconds"], connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise VisionModelError(
                "视觉模型请求超时，请稍后重试。",
                status_code=504,
                error_type="timeout",
            )
        except httpx.RequestError as e:
            raise VisionModelError(
                f"无法连接视觉模型服务：{type(e).__name__}",
                status_code=502,
                error_type="network_error",
            )

    # ===== 处理非 2xx =====
    if response.status_code >= 400:
        # 仅记录脱敏信息：状态码 + 截断的 body 前 200 字符（不记录 base64）
        try:
            body_text = response.text
        except Exception:  # noqa: BLE001
            body_text = ""
        truncated = body_text[:200] if body_text else ""
        logger.warning(
            "Vision model returned error. request_id=%s status=%s body_prefix=%s",
            request_id,
            response.status_code,
            truncated.replace("\n", " "),
        )
        status, message, error_type = _describe_error(response.status_code, body_text)
        raise VisionModelError(message, status_code=status, error_type=error_type)

    # ===== 解析成功响应 =====
    try:
        data = response.json()
    except ValueError:
        raise VisionModelError(
            "视觉模型返回了非 JSON 数据，请稍后重试。",
            status_code=502,
            error_type="bad_response",
        )

    if not isinstance(data, dict):
        raise VisionModelError(
            "视觉模型返回结构异常，请稍后重试。",
            status_code=502,
            error_type="bad_response",
        )

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise VisionModelError(
            "视觉模型未返回任何结果，请稍后重试。",
            status_code=502,
            error_type="empty_choices",
        )

    first = choices[0]
    if not isinstance(first, dict):
        raise VisionModelError(
            "视觉模型返回结构异常，请稍后重试。",
            status_code=502,
            error_type="bad_response",
        )

    message = first.get("message") or {}
    answer = message.get("content") if isinstance(message, dict) else None

    if isinstance(answer, list):
        # 兼容多 part 形式：拼接 text 部分
        parts = []
        for part in answer:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        answer = "".join(parts)

    if answer is None or (isinstance(answer, str) and not answer.strip()):
        raise VisionModelError(
            "视觉模型返回了空内容，请更换问题或截图后重试。",
            status_code=502,
            error_type="empty_answer",
        )

    usage_raw = data.get("usage")
    usage: Optional[Dict[str, int]] = None
    if isinstance(usage_raw, dict):
        usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
            "total_tokens": int(usage_raw.get("total_tokens") or 0),
        }

    return {
        "answer": answer.strip() if isinstance(answer, str) else str(answer),
        "model": cfg["model"],
        "usage": usage,
    }
