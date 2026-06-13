"""
视觉服务统一层（PR9）。

本模块在 `vision_model.py` 之上做轻量增强，统一所有视觉分析请求：
- 普通视觉对话接口 `POST /api/vision-dialogue`
- Qwen 实时工具 `analyze_current_frame`

职责：
1. 问题标准化（去首尾空白、合并空白、英文小写，保留中文）
2. 图片 SHA-256
3. 缓存查询（内存 TTL，LRU 上限）
4. 并发请求去重（asyncio.Future，in-flight 共享结果）
5. 调用 `vision_model.call_vision_model`（不再有第二套调用逻辑）
6. 耗时统计（cache_lookup_ms / model_request_ms / total_ms）
7. 返回统一结果（answer / model / usage / timing / cache / image / request_id）

设计原则：
- 缓存只保存在当前后端进程内存
- 服务重启后缓存自动消失
- 不缓存失败、超时、限流、鉴权失败等异常
- 不保存图片 Base64 / 原始字节 / 用户隐私
- 缓存 Key = 图片 SHA-256 + 标准化后的问题
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from .vision_model import VisionModelError, call_vision_model

logger = logging.getLogger(__name__)


# ===== 默认配置 =====
DEFAULT_CACHE_ENABLED = True
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_CACHE_MAX_ITEMS = 100

# 问题标准化：合并空白
_WHITESPACE_RE = re.compile(r"\s+")


def _load_config() -> Dict[str, Any]:
    """从环境变量加载缓存配置。"""
    enabled_raw = (os.getenv("VISION_CACHE_ENABLED") or "").strip().lower()
    if enabled_raw in ("0", "false", "no", "off"):
        enabled = False
    elif enabled_raw in ("1", "true", "yes", "on"):
        enabled = True
    else:
        enabled = DEFAULT_CACHE_ENABLED

    try:
        ttl = int(os.getenv("VISION_CACHE_TTL_SECONDS") or DEFAULT_CACHE_TTL_SECONDS)
    except ValueError:
        ttl = DEFAULT_CACHE_TTL_SECONDS
    if ttl < 0:
        ttl = 0

    try:
        max_items = int(os.getenv("VISION_CACHE_MAX_ITEMS") or DEFAULT_CACHE_MAX_ITEMS)
    except ValueError:
        max_items = DEFAULT_CACHE_MAX_ITEMS
    if max_items < 1:
        max_items = 1

    return {
        "enabled": enabled,
        "ttl_seconds": ttl,
        "max_items": max_items,
    }


def normalize_question(question: str) -> str:
    """
    问题标准化：
    1. 去首尾空格
    2. 合并连续空白字符
    3. 英文字母转小写（不影响中文）
    """
    if not question:
        return ""
    text = question.strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.lower()
    return text


def hash_image(image_bytes: bytes) -> str:
    """计算图片 SHA-256（hex digest）。"""
    return hashlib.sha256(image_bytes).hexdigest()


def build_cache_key(image_sha256: str, normalized_question: str) -> str:
    """构造缓存 Key。"""
    return f"v1|{image_sha256}|{normalized_question}"


class VisionServiceError(Exception):
    """视觉服务统一错误（包装 VisionModelError 也可作为上游错误）。"""

    def __init__(self, message: str, status_code: int = 502, error_type: str = "vision_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class VisionService:
    """
    视觉分析服务单例。

    所有调用都通过 `analyze()` 入口，共享同一份缓存和去重池。
    """

    def __init__(self) -> None:
        # 缓存：OrderedDict 以便 LRU 淘汰
        self._cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        # in-flight：缓存 Key -> Future，避免相同请求并发
        self._inflight: Dict[str, asyncio.Future] = {}
        # 保护 in-flight 字典的锁
        self._inflight_lock = asyncio.Lock()
        # 缓存配置懒加载
        self._config_loaded_at: float = 0.0
        self._config_cache: Dict[str, Any] = {}

    # ===== 公开方法 =====

    async def analyze(
        self,
        *,
        question: str,
        image_bytes: bytes,
        content_type: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """
        统一视觉分析入口。

        Returns:
            {
                "answer": str,
                "model": str,
                "usage": Optional[dict],
                "image": {"content_type", "size_bytes", "sha256"},
                "cache": {"hit": bool, "source": "model" | "memory"},
                "timing": {"cache_lookup_ms": int, "model_request_ms": int, "total_ms": int},
                "request_id": str,
            }

        Raises:
            VisionServiceError / VisionModelError: 配置错误或上游失败
        """
        total_start = time.perf_counter()

        if not image_bytes:
            raise VisionServiceError(
                "图片内容为空", status_code=400, error_type="bad_request"
            )
        ct = (content_type or "image/jpeg").lower()

        # 标准化
        normalized_q = normalize_question(question)
        sha = hash_image(image_bytes)

        cfg = self._get_config()
        cache_key = build_cache_key(sha, normalized_q)

        # ===== 1) cache lookup =====
        lookup_start = time.perf_counter()
        cached = self._cache_get(cache_key) if cfg["enabled"] else None
        cache_lookup_ms = int((time.perf_counter() - lookup_start) * 1000)

        if cached is not None:
            total_ms = int((time.perf_counter() - total_start) * 1000)
            logger.info(
                "Vision cache hit. request_id=%s sha=%s total_ms=%d model_request_ms=0",
                request_id, sha[:12], total_ms,
            )
            return {
                "answer": cached["answer"],
                "model": cached["model"],
                "usage": cached.get("usage"),
                "image": {
                    "content_type": ct,
                    "size_bytes": len(image_bytes),
                    "sha256": sha,
                },
                "cache": {"hit": True, "source": "memory"},
                "timing": {
                    "cache_lookup_ms": cache_lookup_ms,
                    "model_request_ms": 0,
                    "total_ms": total_ms,
                },
                "request_id": request_id,
            }

        # ===== 2) in-flight 去重 =====
        # 如果已有相同 key 的请求在执行，等待其结果
        model_request_ms = 0
        async with self._inflight_lock:
            fut = self._inflight.get(cache_key)
            if fut is None:
                fut = asyncio.get_event_loop().create_future()
                self._inflight[cache_key] = fut
                is_leader = True
            else:
                is_leader = False

        if not is_leader:
            # 等 leader 的结果
            try:
                result = await fut
            except Exception as e:  # noqa: BLE001
                # leader 失败，包装后抛出
                if isinstance(e, (VisionModelError, VisionServiceError)):
                    raise e
                raise VisionServiceError(
                    f"等待并发请求失败：{type(e).__name__}",
                    status_code=502,
                    error_type="inflight_error",
                ) from e

            total_ms = int((time.perf_counter() - total_start) * 1000)
            # 标记这次请求是 dedup 命中
            result = dict(result)
            result["image"] = {
                "content_type": ct,
                "size_bytes": len(image_bytes),
                "sha256": sha,
            }
            result["cache"] = {"hit": True, "source": "inflight"}
            result["timing"] = {
                "cache_lookup_ms": cache_lookup_ms,
                "model_request_ms": 0,
                "total_ms": total_ms,
            }
            result["request_id"] = request_id
            logger.info(
                "Vision in-flight dedup. request_id=%s sha=%s total_ms=%d",
                request_id, sha[:12], total_ms,
            )
            return result

        # ===== 3) leader 调用模型 =====
        try:
            model_start = time.perf_counter()
            try:
                model_result = await call_vision_model(
                    question=normalized_q or question,
                    image_bytes=image_bytes,
                    content_type=ct,
                    request_id=request_id,
                )
            finally:
                model_request_ms = int((time.perf_counter() - model_start) * 1000)

            # 写入缓存（仅在 enabled 时）
            if cfg["enabled"]:
                self._cache_put(
                    cache_key,
                    {
                        "answer": model_result["answer"],
                        "model": model_result.get("model") or "",
                        "usage": model_result.get("usage"),
                    },
                )

            total_ms = int((time.perf_counter() - total_start) * 1000)
            logger.info(
                "Vision model call done. request_id=%s sha=%s cache_hit=false model_request_ms=%d total_ms=%d",
                request_id, sha[:12], model_request_ms, total_ms,
            )

            result = {
                "answer": model_result["answer"],
                "model": model_result.get("model") or "",
                "usage": model_result.get("usage"),
                "image": {
                    "content_type": ct,
                    "size_bytes": len(image_bytes),
                    "sha256": sha,
                },
                "cache": {"hit": False, "source": "model"},
                "timing": {
                    "cache_lookup_ms": cache_lookup_ms,
                    "model_request_ms": model_request_ms,
                    "total_ms": total_ms,
                },
                "request_id": request_id,
            }

            # 唤醒所有等待者
            async with self._inflight_lock:
                self._inflight.pop(cache_key, None)
            if not fut.done():
                fut.set_result(
                    {
                        "answer": result["answer"],
                        "model": result["model"],
                        "usage": result["usage"],
                    }
                )
            return result

        except Exception as e:  # noqa: BLE001
            # 失败时不写缓存；唤醒所有等待者抛出相同错误
            async with self._inflight_lock:
                self._inflight.pop(cache_key, None)
            if not fut.done():
                fut.set_exception(e)
            raise

    # ===== 内部 =====

    def _get_config(self) -> Dict[str, Any]:
        """懒加载并缓存配置（避免每次请求都读 env）。"""
        now = time.perf_counter()
        # 简单 60s 刷新一次
        if not self._config_cache or (now - self._config_loaded_at) > 60.0:
            self._config_cache = _load_config()
            self._config_loaded_at = now
        return self._config_cache

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        """LRU 读取。命中后把 key 移到队尾。"""
        entry = self._cache.get(key)
        if entry is None:
            return None
        # 过期检查
        cfg = self._get_config()
        if entry["expires_at"] < time.time():
            self._cache.pop(key, None)
            return None
        # LRU：移到队尾
        self._cache.move_to_end(key)
        return entry

    def _cache_put(self, key: str, value: Dict[str, Any]) -> None:
        """写入缓存。"""
        cfg = self._get_config()
        if not cfg["enabled"]:
            return
        ttl = cfg["ttl_seconds"]
        expires_at = time.time() + ttl if ttl > 0 else time.time()
        self._cache[key] = {
            **value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }
        # LRU 上限
        max_items = cfg["max_items"]
        while len(self._cache) > max_items:
            self._cache.popitem(last=False)

    # ===== 测试用钩子 =====

    def reset_for_tests(self) -> None:
        """清空缓存和 in-flight。仅供测试使用。"""
        self._cache.clear()
        self._inflight.clear()
        self._config_cache = {}
        self._config_loaded_at = 0.0

    def cache_size(self) -> int:
        """当前缓存条目数（仅供测试 / 监控使用）。"""
        return len(self._cache)


# ===== 进程级单例 =====
_service_instance: Optional[VisionService] = None
_service_lock = asyncio.Lock() if False else None  # 仅占位说明


def get_vision_service() -> VisionService:
    """获取进程级单例。"""
    global _service_instance
    if _service_instance is None:
        _service_instance = VisionService()
    return _service_instance


def reset_vision_service_for_tests() -> None:
    """重置单例（仅供测试）。"""
    global _service_instance
    _service_instance = None
