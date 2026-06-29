from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn


def wait_for_port(host: str, port: int, timeout: float = 30.0):
    deadline = time.monotonic() + timeout
    connect_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((connect_host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"lc_agent desktop server did not listen on {connect_host}:{port} within {timeout:.0f}s")


def get_work_area() -> tuple[int, int, int, int]:
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        pass
    return 0, 0, 1400, 900


def get_webview_storage_path() -> str:
    path = Path.cwd() / ".tmp" / "webview2-data"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def run_desktop(app: Any, host: str, port: int, title: str = "lc-agent"):
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("Desktop mode requires pywebview. Install it with: pip install pywebview") from exc

    config = uvicorn.Config(app.fastapi_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    wait_for_port(host, port)

    x, y, width, height = get_work_area()
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    webview.create_window(
        title=title,
        url=f"http://{url_host}:{port}/?desktop=1",
        x=x,
        y=y,
        width=width,
        height=height,
        min_size=(width, height),
        frameless=True,
        easy_drag=False,
        resizable=False,
    )

    try:
        webview.start(private_mode=False, storage_path=get_webview_storage_path())
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
