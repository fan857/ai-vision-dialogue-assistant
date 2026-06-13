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


def test_ws_init_without_image_succeeds():
    """PR11: 没有 image_base64 也能 init 成功 —— 启动实时对话不再强制要求先有画面。
    后续用户提问命中视觉关键词时再通过 session.update_image 补图。
    """
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({"type": "session.init"})
        evt = ws.receive_json()
        assert evt["type"] == "session.ready"


def test_ws_rejects_invalid_base64():
    client = TestClient(app)
    with client.websocket_connect("/ws/realtime-voice") as ws:
        ws.send_json({"type": "session.init", "image_base64": "!!!not-base64!!!"})
        evt = ws.receive_json()
        assert evt["type"] == "session.error"


def test_ws_no_api_key_returns_error(monkeypatch):
    """缺 DASHSCOPE_API_KEY 时返回 session.error。"""
    # 替换 _get_config，让它返回空 api_key
    import services.qwen_realtime as qr

    def _empty_config():
        return {
            "api_key": "",
            "url": "wss://example.invalid/realtime",
            "model": "qwen-test",
            "voice": "Tina",
        }
    monkeypatch.setattr(qr, "_get_config", _empty_config)

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
