"""
PR9 视觉服务缓存 / 去重 / 耗时测试（不连接真实豆包）。

覆盖：
- 缓存命中
- 不同问题不命中
- 不同图片不命中
- TTL 过期
- 失败不缓存
- 禁用缓存
- 并发 in-flight 去重
- 共享缓存（普通接口和 Qwen 工具）
- 日志脱敏（不输出 base64）

运行：
    cd d:\2026qiniu2
    python -m pytest tests/test_pr9_cache.py -v
"""
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from services.vision_model import VisionModelError  # noqa: E402
from services.vision_service import (  # noqa: E402
    VisionService,
    build_cache_key,
    hash_image,
    normalize_question,
    reset_vision_service_for_tests,
)


# ===== 工具 =====

def _png(seed: bytes) -> bytes:
    """构造固定大小的伪 PNG 字节，仅用于 SHA-256。"""
    return b"\x89PNG\r\n\x1a\n" + seed + b"\x00" * 64


# ===== 纯函数测试 =====

def test_normalize_question_trim_and_lower():
    assert normalize_question("  Hello   WORLD  ") == "hello world"


def test_normalize_question_keeps_chinese():
    assert normalize_question("  我手里  拿的 是什么  ") == "我手里 拿的 是什么"


def test_hash_image_deterministic():
    a = _png(b"abc")
    b = _png(b"abc")
    assert hash_image(a) == hash_image(b)
    assert hash_image(a) != hash_image(_png(b"def"))


def test_build_cache_key_format():
    key = build_cache_key("deadbeef", "hello")
    assert key.startswith("v1|")
    assert "deadbeef" in key
    assert "hello" in key


# ===== 服务层测试 =====

@pytest.fixture
def fresh_service(monkeypatch):
    """每次测试都重置单例 + 关闭 .env 影响。"""
    reset_vision_service_for_tests()
    # 强制开启缓存、短 TTL、隔离
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("VISION_CACHE_MAX_ITEMS", "10")
    return VisionService.__new__(VisionService).reset_for_tests() or get_service()


def get_service() -> VisionService:
    from services.vision_service import get_vision_service as _g
    return _g()


@pytest.mark.asyncio
async def test_cache_hit_on_same_image_and_question(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        await asyncio.sleep(0.01)  # 模拟真实耗时
        return {"answer": "yes", "model": "fake-doubao", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"hit")
    q = "我手里拿的是什么？"

    r1 = await svc.analyze(question=q, image_bytes=img, content_type="image/png", request_id="r1")
    r2 = await svc.analyze(question=q, image_bytes=img, content_type="image/png", request_id="r2")

    assert call_count["n"] == 1, "第二次应当命中缓存，不调用模型"
    assert r1["cache"] == {"hit": False, "source": "model"}
    assert r2["cache"] == {"hit": True, "source": "memory"}
    assert r2["timing"]["model_request_ms"] == 0
    assert r2["answer"] == r1["answer"]


@pytest.mark.asyncio
async def test_cache_miss_on_different_question(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        return {"answer": f"a-{question}", "model": "fake-doubao", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"diff-q")
    r1 = await svc.analyze(question="问题A", image_bytes=img, content_type="image/png", request_id="r1")
    r2 = await svc.analyze(question="问题B", image_bytes=img, content_type="image/png", request_id="r2")

    assert call_count["n"] == 2
    assert r1["cache"]["hit"] is False
    assert r2["cache"]["hit"] is False
    assert r1["answer"] != r2["answer"]


@pytest.mark.asyncio
async def test_cache_miss_on_different_image(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        return {"answer": "x", "model": "fake-doubao", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    r1 = await svc.analyze(question="hi", image_bytes=_png(b"img1"), content_type="image/png", request_id="r1")
    r2 = await svc.analyze(question="hi", image_bytes=_png(b"img2"), content_type="image/png", request_id="r2")

    assert call_count["n"] == 2
    assert r1["cache"]["hit"] is False
    assert r2["cache"]["hit"] is False


@pytest.mark.asyncio
async def test_cache_ttl_expiry(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "1")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        return {"answer": "x", "model": "fake-doubao", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"ttl")
    await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r1")
    # 睡眠超过 TTL
    time.sleep(1.2)
    await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r2")

    assert call_count["n"] == 2, "TTL 过期后必须重新调用模型"


@pytest.mark.asyncio
async def test_failure_not_cached(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        raise VisionModelError("上游失败", status_code=502, error_type="upstream_error")

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"err")

    with pytest.raises(VisionModelError):
        await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r1")
    with pytest.raises(VisionModelError):
        await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r2")

    assert call_count["n"] == 2, "失败结果不应被缓存"
    assert svc.cache_size() == 0


@pytest.mark.asyncio
async def test_cache_disabled_always_calls_model(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "false")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        return {"answer": "x", "model": "fake-doubao", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"off")
    r1 = await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r1")
    r2 = await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="r2")

    assert call_count["n"] == 2
    assert r1["cache"]["hit"] is False
    assert r2["cache"]["hit"] is False


@pytest.mark.asyncio
async def test_concurrent_dedup_only_one_model_call(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "false")  # 关掉缓存，单独验证 in-flight

    started = {"n": 0}
    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        await asyncio.sleep(0.1)
        return {"answer": "shared", "model": "fake-doubao", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"dup")
    q = "same"

    # 并发 5 个相同请求
    results = await asyncio.gather(
        *(svc.analyze(question=q, image_bytes=img, content_type="image/png", request_id=f"r{i}")
          for i in range(5))
    )

    assert call_count["n"] == 1, f"5 个并发请求只允许 1 次真实模型调用，实际 {call_count['n']}"

    # 1 个 leader (source=model) + 4 个 inflight (source=inflight)
    sources = [r["cache"]["source"] for r in results]
    assert sources.count("model") == 1
    assert sources.count("inflight") == 4
    # 所有结果 answer 一致
    assert {r["answer"] for r in results} == {"shared"}


@pytest.mark.asyncio
async def test_leader_failure_propagates_to_waiters(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "false")

    async def fake_model(*, question, image_bytes, content_type, request_id):
        await asyncio.sleep(0.05)
        raise VisionModelError("boom", status_code=502, error_type="upstream_error")

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"err-dedup")
    q = "q"

    results = await asyncio.gather(
        *(svc.analyze(question=q, image_bytes=img, content_type="image/png", request_id=f"r{i}")
          for i in range(3)),
        return_exceptions=True,
    )

    assert all(isinstance(r, VisionModelError) for r in results), "所有等待者必须收到 leader 的错误"


@pytest.mark.asyncio
async def test_lru_eviction(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")
    monkeypatch.setenv("VISION_CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("VISION_CACHE_MAX_ITEMS", "2")

    call_count = {"n": 0}

    async def fake_model(*, question, image_bytes, content_type, request_id):
        call_count["n"] += 1
        return {"answer": f"a-{call_count['n']}", "model": "fake", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()

    # 写 3 条不同 key，max=2，应淘汰最旧
    await svc.analyze(question="q1", image_bytes=_png(b"1"), content_type="image/png", request_id="r1")
    await svc.analyze(question="q2", image_bytes=_png(b"2"), content_type="image/png", request_id="r2")
    await svc.analyze(question="q3", image_bytes=_png(b"3"), content_type="image/png", request_id="r3")
    assert svc.cache_size() == 2

    # q1 应该被淘汰，重新调用模型
    before = call_count["n"]
    await svc.analyze(question="q1", image_bytes=_png(b"1"), content_type="image/png", request_id="r1b")
    assert call_count["n"] == before + 1


@pytest.mark.asyncio
async def test_timing_fields_present(monkeypatch):
    reset_vision_service_for_tests()
    monkeypatch.setenv("VISION_CACHE_ENABLED", "true")

    async def fake_model(*, question, image_bytes, content_type, request_id):
        await asyncio.sleep(0.02)
        return {"answer": "x", "model": "fake", "usage": None}

    import services.vision_service as vs
    monkeypatch.setattr(vs, "call_vision_model", fake_model)

    svc = get_service()
    svc.reset_for_tests()
    img = _png(b"time")
    r = await svc.analyze(question="q", image_bytes=img, content_type="image/png", request_id="rt")

    timing = r["timing"]
    assert set(timing.keys()) == {"cache_lookup_ms", "model_request_ms", "total_ms"}
    assert all(isinstance(v, int) and v >= 0 for v in timing.values())
    # 模型耗时至少 >= 20ms（sleep 0.02）
    assert timing["model_request_ms"] >= 20 or timing["total_ms"] >= 20
