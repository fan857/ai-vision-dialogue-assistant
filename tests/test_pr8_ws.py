"""
PR8 后端 WebSocket 结构测试（不连接真实百炼）。

依赖：httpx 0.27.x（与 starlette TestClient 兼容）。
"""
import base64
import binascii
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402


def _make_png_bytes() -> bytes:
    """用于测试的图片字节。PR8 只校验 content_type 和大小，不强制解码。"""
    # 1KB 的伪 PNG 数据，content_type 已声明为 image/png
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024


def test_routes_registered():
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/ws/realtime-voice" in routes
    assert "/api/health" in routes
    assert "/api/vision-dialogue" in routes


def test_ws_rejects_no_image():
    """没有 image_base64 应立即返回 session.error。"""
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({"type": "session.init"})
        evt = ws.receive_json()
        assert evt["type"] == "session.error"
        assert "image" in evt["message"]


def test_ws_rejects_invalid_base64():
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({"type": "session.init", "image_base64": "!!!not-base64!!!"})
        evt = ws.receive_json()
        assert evt["type"] == "session.error"


def test_ws_no_api_key_returns_error():
    """缺 DASHSCOPE_API_KEY 时返回 session.error。"""
    # 临时移除 DASHSCOPE_API_KEY
    saved = os.environ.pop("DASHSCOPE_API_KEY", None)
    try:
        client = TestClient(app)
        png_bytes = _make_png_bytes()
        with client.websocket_connect("/ws/realtime-voice") as ws:
            ws.send_json({
                "type": "session.init",
                "image_base64": base64.b64encode(png_bytes).decode("ascii"),
                "content_type": "image/png"
            })
            evt = ws.receive_json()
            assert evt["type"] == "session.error"
            assert "DASHSCOPE_API_KEY" in evt["message"] or "未配置" in evt["message"]
    finally:
        if saved is not None:
            os.environ["DASHSCOPE_API_KEY"] = saved


def test_ws_image_too_large():
    client = TestClient(app)
    big = b"\x00" * (3 * 1024 * 1024)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({
            "type": "session.init",
            "image_base64": base64.b64encode(big).decode("ascii"),
            "content_type": "image/jpeg"
        })
        evt = ws.receive_json()
        assert evt["type"] == "session.error"
        assert "2 MB" in evt["message"] or "超过" in evt["message"]


def test_ws_ping_pong():
    """控制帧 ping 应返回 pong。"""
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({"type": "ping"})
        evt = ws.receive_json()
        assert evt["type"] == "pong"


def test_ws_binary_frame_before_init_is_silently_dropped():
    """在 session.init 之前发送 binary 应被静默忽略，不抛错。"""
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_bytes(b"\x00\x01")
        # 不应崩，服务端不应返回任何东西
        # 我们发送一个 ping 来证明连接还活着
        ws.send_json({"type": "ping"})
        evt = ws.receive_json()
        assert evt["type"] == "pong"


if __name__ == "__main__":
    import subprocess
    code = subprocess.call(
        ["python", "-m", "pytest", __file__, "-v", "-x"],
        cwd=str(Path(__file__).resolve().parent)
    )
    sys.exit(code)
