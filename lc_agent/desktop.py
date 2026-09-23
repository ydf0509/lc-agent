
import multiprocessing
import socket
import time
from pathlib import Path
import sys

from lc_agent.utils.loggers import desktop_logger


def wait_for_port(host: str, port: int, timeout: float = 30.0):
    deadline = time.monotonic() + timeout
    connect_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((connect_host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


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


# ===== Windows 无标题栏 (captionless) 补丁（Chromium 同款做法）=====
# frameless=False 正常起窗（保留 WS_THICKFRAME / Aero Snap / 系统菜单能力），
# shown 后做两件事：
# 1. 去掉 WS_CAPTION（只去标题栏，不碰左右下边框）；
# 2. 纯 ctypes SetWindowLongPtrW 子类化窗口过程：
#    WM_NCCALCSIZE -> 直接返回 0，非客户区面积归零（顶部白边/边框彻底消失，
#                     顶部就是前端 AppHeader，随明暗主题自适应，不需要涂黑）；
#    WM_NCHITTEST  -> 边缘 8 逻辑像素返回 HT*/角热区，原生 resize 满血
#                    （OS 原生拖动循环，不走 JS bridge，Aero Snap 正常）。
# 注意：不用 pythonnet 的 WinForms.NativeWindow 做子类化——实测它的 WndProc
# 重写收不到任何消息；纯 Win32 子类化必达。
# 另：DWMWA_WINDOW_CORNER_PREFERENCE=DONOTROUND 去 Win11 大圆角；
#     DwmExtendFrameIntoClientArea(1px) 保住 DWM 阴影；
#     create_window(background_color=深色) 让 WebView2 加载前底色就是深色，不闪白；
#     Form.MaximizedBounds 锁当前屏工作区（最大化不盖任务栏）。
_WS_CAPTION = 0x00C00000
_GWL_STYLE = -16
_GWLP_WNDPROC = -4
_SWP_NOMOVE = 0x0002
_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020

_WM_NCCALCSIZE = 0x0083
_WM_NCHITTEST = 0x0084
_WM_NCDESTROY = 0x0082
_WS_MAXIMIZE = 0x01000000
_HTCLIENT = 1
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17

_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_DONOTROUND = 1
# 深色 header 底（与前端 AppHeader 深色背景同系）；浅色主题下页面 body 会盖住底色，无影响
_DESKTOP_BG_COLOR = "#14161a"

# hwnd -> (wndproc回调, 旧窗口过程地址, user32实例)：必须强引用，
# 回调被 GC 后窗口过程悬空，下一条消息直接崩进程
_subclass_refs: dict = {}


def _apply_captionless_fix(window) -> None:
    """shown 回调：去 WS_CAPTION + 锁 MaximizedBounds=工作区（Windows only）。

    时机：WinForms Shown 之后 -> hwnd 必已创建；只跑一次，窗口刚露面，看不到闪烁。
    线程：pywebview 的 Event.set() 把回调跑在新起的事件线程里，
    凡是碰 WinForms Form 的操作都经 native.Invoke(Action(...)) 送回 UI 线程执行。
    """
    native = window.native  # BrowserForm；shown 时必已由 BrowserForm.__init__ 赋值
    if native is None:
        desktop_logger.warning("No native form yet, skip captionless patch")
        return

    import ctypes
    from ctypes import wintypes

    import clr

    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    import System.Windows.Forms as WinForms
    from System import Action
    from System.Drawing import Rectangle

    # NOTE: 必须用独立的 WinDLL 实例，不能碰 ctypes.windll.user32。
    # ctypes.windll.user32 是全局单例；一旦给它的 SetWindowPos 设了 argtypes，
    # pywebview 自身 winforms.py 的 move() 传 None 宽高就会炸
    # (ArgumentError: 'NoneType' cannot be interpreted as an integer)，
    # 表现为标题栏拖拽失效。独立实例的 prototype 只影响本补丁。
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    # HWND 在 64 位下是 64 位，不声明 argtypes 会被 ctypes 按 32 位 int 截断 -> 必须声明
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    user32.SetWindowLongPtrW.restype = ctypes.c_void_p
    user32.CallWindowProcW.argtypes = [
        ctypes.c_void_p,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.CallWindowProcW.restype = ctypes.c_void_p
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = ctypes.c_void_p
    # GetDpiForWindow 仅 Win10 1607+ 才有导出，旧系统 getattr 失败就按 96 处理
    _get_dpi = getattr(user32, "GetDpiForWindow", None)
    if _get_dpi is not None:
        _get_dpi.argtypes = [wintypes.HWND]
        _get_dpi.restype = wintypes.UINT

    class _Margins(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth", ctypes.c_int),
            ("cxRightWidth", ctypes.c_int),
            ("cyTopHeight", ctypes.c_int),
            ("cyBottomHeight", ctypes.c_int),
        ]

    def _hit_test(h: int, lparam: int) -> int:
        """边缘 8 逻辑像素热区 -> 原生 resize；其余客户区。最大化时不做边缘 resize。"""
        from ctypes import c_short

        style = user32.GetWindowLongW(h, _GWL_STYLE)
        if style & _WS_MAXIMIZE:
            return _HTCLIENT
        x = c_short(lparam & 0xFFFF).value
        y = c_short((lparam >> 16) & 0xFFFF).value
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        dpi = _get_dpi(h) if _get_dpi is not None else 96
        dpi = dpi or 96
        border = max(4, round(8 * dpi / 96))  # 8 逻辑像素，随显示器缩放放大
        on_left = 0 <= x - rect.left < border
        on_right = 0 <= rect.right - x < border
        on_top = 0 <= y - rect.top < border
        on_bottom = 0 <= rect.bottom - y < border
        # 角优先于边
        if on_top and on_left:
            return _HTTOPLEFT
        if on_top and on_right:
            return _HTTOPRIGHT
        if on_bottom and on_left:
            return _HTBOTTOMLEFT
        if on_bottom and on_right:
            return _HTBOTTOMRIGHT
        if on_left:
            return _HTLEFT
        if on_right:
            return _HTRIGHT
        if on_top:
            return _HTTOP
        if on_bottom:
            return _HTBOTTOM
        return _HTCLIENT

    _WNDPROC_T = ctypes.WINFUNCTYPE(
        ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    def _install_subclass(h: int) -> None:
        """纯 Win32 子类化：NCCALCSIZE 全客户区 + NCHITTEST 原生 resize。"""
        if h in _subclass_refs:
            return
        old_proc = user32.SetWindowLongPtrW(h, _GWLP_WNDPROC, None)
        if not old_proc:
            desktop_logger.warning("SetWindowLongPtrW query old proc failed, skip subclass")
            return

        @_WNDPROC_T
        def _wndproc(hw, msg, wp, lp):
            if msg == _WM_NCCALCSIZE and wp == 1:
                # 整个窗口都是客户区：非客户区（含顶部白边框）面积归零
                return 0
            if msg == _WM_NCHITTEST:
                try:
                    return _hit_test(hw, lp)
                except Exception:
                    return _HTCLIENT
            if msg == _WM_NCDESTROY:
                # 窗口销毁时恢复旧过程并释放引用，避免悬空回调
                try:
                    user32.SetWindowLongPtrW(hw, _GWLP_WNDPROC, old_proc)
                finally:
                    _subclass_refs.pop(hw, None)
                return user32.CallWindowProcW(old_proc, hw, msg, wp, lp)
            return user32.CallWindowProcW(old_proc, hw, msg, wp, lp)

        new_proc = user32.SetWindowLongPtrW(h, _GWLP_WNDPROC, _wndproc)
        if not new_proc:
            desktop_logger.warning("SetWindowLongPtrW install failed, keep captionless only")
            return
        _subclass_refs[h] = (_wndproc, old_proc, user32)
        desktop_logger.info("Win32 subclass installed (NCCALCSIZE/NCHITTEST) hwnd=%s", h)

    def _patch():
        try:
            form = window.native
            hwnd = form.Handle.ToInt64()
            before = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            user32.SetWindowLongW(hwnd, _GWL_STYLE, (before & ~_WS_CAPTION) & 0xFFFFFFFF)
            # 不移动、不改尺寸，只让 OS 重算非客户区（标题栏消失）
            user32.SetWindowPos(
                hwnd,
                None,
                0,
                0,
                0,
                0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED,
            )
            after = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            # 任务栏/窗口图标：shown 时 hwnd 已确定，在 UI 线程直接发 WM_SETICON，
            # 比 on_started 线程里 EnumWindows 猜窗口可靠（枚举可能早于窗口创建）。
            _set_window_icon_hwnd(hwnd)
            # 纯 Win32 子类化（NCCALCSIZE 全客户区 + NCHITTEST 原生 resize）：
            # 非客户区面积归零后顶部白边/边框无从绘制，顶部就是前端 AppHeader。
            _install_subclass(hwnd)
            # 去 Win11 大圆角 + 全客户区要回 DWM 阴影（extend 1px frame）。
            # 注：BORDER_COLOR 在去 CAPTION 的窗口上实测不生效，已删；NCCALCSIZE
            # 归零后边框本就不存在，无需染色。
            try:
                c_corner = ctypes.c_int(_DWMWCP_DONOTROUND)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    _DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(c_corner),
                    ctypes.sizeof(c_corner),
                )
                margins = _Margins(1, 1, 1, 1)
                dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
                # 触发一次 NCCALCSIZE，立刻按全客户区重排
                user32.SetWindowPos(
                    hwnd,
                    None,
                    0,
                    0,
                    0,
                    0,
                    _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED,
                )
            except Exception:
                desktop_logger.debug("DWM corner/shadow not supported", exc_info=True)
            # 最大化锁进当前屏工作区：任务栏露出来
            wa = WinForms.Screen.FromHandle(form.Handle).WorkingArea
            form.MaximizedBounds = Rectangle(wa.X, wa.Y, wa.Width, wa.Height)
            desktop_logger.info(
                "Captionless patch: style 0x%08X -> 0x%08X caption_removed=%s "
                "MaximizedBounds=(%d,%d,%d,%d)",
                before & 0xFFFFFFFF,
                after & 0xFFFFFFFF,
                not (after & _WS_CAPTION),
                wa.X,
                wa.Y,
                wa.Width,
                wa.Height,
            )
        except Exception:
            desktop_logger.exception("Captionless patch failed")

    native.Invoke(Action(_patch))


class _DesktopApi:
    """js_api：前端三个窗口按钮 + 标题栏双击的后端实现。

    NOTE: 窗口引用必须是下划线开头。pywebview 会枚举 js_api 上所有公开属性并
    递归展开；公开的 `window` 属性会让它爬进整个 WinForms 原生对象图
    (window.native.AccessibilityObject.Bounds.Empty.Empty...)，
    报 "maximum recursion depth exceeded" 并卡死窗口。
    """

    def __init__(self):
        self._window = None
        self._maximized = False

    def minimize(self):
        if self._window:
            self._window.minimize()

    def maximize(self):
        if self._window:
            self._window.maximize()
            self._maximized = True

    def restore(self):
        if self._window:
            self._window.restore()
            self._maximized = False

    def toggle_max(self):
        if self._window:
            if self._maximized:
                self._window.restore()
                self._maximized = False
            else:
                self._window.maximize()
                self._maximized = True


def _set_window_icon_hwnd(hwnd: int) -> bool:
    """给确定 hwnd 发 WM_SETICON（闪电 logo，16/32 双尺寸）。

    在 UI 线程的 shown 补丁里调用，hwnd 已确定，比 EnumWindows 猜窗口可靠。
    返回是否成功，便于调用方降级到旧的枚举方式。
    """
    try:
        import ctypes
        from ctypes import wintypes

        ico_path = str(Path(__file__).parent / "web" / "dist" / "favicon.ico")
        if not Path(ico_path).exists():
            return False
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.LoadImageW.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        u.LoadImageW.restype = wintypes.HANDLE
        u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u.SendMessageW.restype = wintypes.LPARAM
        big = u.LoadImageW(None, ico_path, 1, 32, 32, 0x0010)
        small = u.LoadImageW(None, ico_path, 1, 16, 16, 0x0010)
        ok = False
        if big:
            u.SendMessageW(hwnd, 0x0080, 1, big)
            ok = True
        if small:
            u.SendMessageW(hwnd, 0x0080, 0, small)
            ok = True
        # NOTE: icon handle 交给窗口后由系统持有，不 Destroy，避免任务栏图标变空白
        desktop_logger.info("Window icon set via hwnd=%s ok=%s", hwnd, ok)
        return ok
    except Exception:
        desktop_logger.exception("Failed to set window icon via hwnd")
        return False


def _apply_window_icon(title: str):
    """Set the window/taskbar icon to favicon.ico via Win32 API."""
    import os

    try:
        import ctypes
        from ctypes import wintypes

        ico_path = str(Path(__file__).parent / "web" / "dist" / "favicon.ico")
        if not Path(ico_path).exists():
            return

        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        WM_SETICON = 0x0080
        ICON_BIG = 1
        ICON_SMALL = 0

        pid = os.getpid()
        candidates: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _enum_cb(h, _lp):
            wpid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(wpid))
            if wpid.value == pid and user32.IsWindowVisible(h):
                candidates.append(h)
            return True

        user32.EnumWindows(_enum_cb, 0)

        for hwnd in candidates:
            big = user32.LoadImageW(0, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            small = user32.LoadImageW(0, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
            if big:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
            if small:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
            desktop_logger.info("Window icon set (hwnd=%s)", hwnd)
    except Exception:
        desktop_logger.exception("Failed to set window icon")


def _build_home_button_js(home_url: str) -> str:
    """Build JS snippet that injects a floating 'Home' button on non-app pages."""
    import json
    safe_url = json.dumps(home_url)
    return f"""
(function() {{
    if (document.getElementById('lc-home-btn')) return;
    var homeUrl = {safe_url};
    try {{
        if (window.location.origin === new URL(homeUrl).origin) return;
    }} catch(e) {{}}
    if (!document.body) return;
    var btn = document.createElement('button');
    btn.id = 'lc-home-btn';
    btn.innerHTML = '&#8962; 返回 lc-agent';
    btn.style.cssText = [
        'position:fixed', 'top:10px', 'left:10px', 'z-index:2147483647',
        'padding:8px 16px', 'border:none', 'border-radius:8px',
        'background:rgba(64,158,255,.92)', 'color:#fff',
        'font-size:14px', 'font-weight:500', 'cursor:pointer',
        'box-shadow:0 2px 12px rgba(0,0,0,.35)',
        'backdrop-filter:blur(6px)',
        'opacity:.9', 'transition:opacity .2s,transform .2s',
    ].join(';');
    btn.onmouseover = function() {{ btn.style.opacity='1'; btn.style.transform='scale(1.05)'; }};
    btn.onmouseout  = function() {{ btn.style.opacity='.9'; btn.style.transform='scale(1)'; }};
    btn.onclick = function() {{ window.location.href = homeUrl; }};
    document.body.appendChild(btn);
}})();
"""


def _webview_process(url: str, title: str):
    """Entry point for the webview subprocess."""
    try:
        import webview
    except ImportError:
        desktop_logger.warning("pywebview not installed, skipping desktop window")
        return

    captionless = sys.platform == "win32"  # 目前只在 Windows 上验证过去标题栏
    desktop_url = url + ("&" if "?" in url else "?") + "desktop=1"
    if captionless:
        desktop_url += "&frameless=1"

    x, y, width, height = get_work_area()
    api = _DesktopApi()
    window = webview.create_window(
        title=title,
        url=desktop_url,
        x=x,
        y=y,
        width=width,
        height=height,
        min_size=(800, 600),
        easy_drag=False,  # 只让前端局部 .pywebview-drag-region 区域可拖
        text_select=True,
        # WebView2 加载前底色：深色，不闪白（页面 body 渲染后会盖住，浅色主题无影响）
        background_color=_DESKTOP_BG_COLOR,
        js_api=api if captionless else None,
    )
    api._window = window

    home_js = _build_home_button_js(url)

    def on_loaded():
        try:
            window.evaluate_js(home_js)  # type: ignore[union-attr]
        except Exception:
            desktop_logger.debug("Failed to inject home button JS", exc_info=True)

    window.events.loaded += on_loaded  # type: ignore[union-attr]

    if captionless:
        # shown 只 fire 一次（BrowserForm.Shown）：去标题栏 + 锁最大化工作区
        window.events.shown += lambda: _apply_captionless_fix(window)  # type: ignore[union-attr]

    def on_started():
        _apply_window_icon(title)

    webview.start(private_mode=False, storage_path=get_webview_storage_path(), func=on_started)


def launch_desktop(host: str, port: int, title: str = "lc-agent") -> multiprocessing.Process | None:
    """Launch a webview window in a subprocess pointing at the server.

    Returns the Process object (or None if the server is not reachable).
    The caller (uvicorn main process) keeps running regardless of whether
    the webview is open or closed.
    """
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{url_host}:{port}/"
    if not wait_for_port(host, port, timeout=5.0):
        desktop_logger.error("Server %s:%s did not respond", host, port)
        sys.exit(1)
    _webview_process(url, title)

    # proc = multiprocessing.Process(
    #     target=_webview_process,
    #     args=(url, title),
    #     daemon=True,
    # )
    # proc.start()
    # return proc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Open lc-agent desktop window")
    parser.add_argument("--url", default=None, help="Server URL to open")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--title", default="lc-agent", help="Window title")
    args = parser.parse_args()

    url = args.url or f"http://{args.host}:{args.port}/"
    desktop_logger.info("Opening %s", url)

    if not wait_for_port(args.host, args.port, timeout=5.0):
        desktop_logger.warning("Server at %s:%s not reachable, opening anyway", args.host, args.port)

    _webview_process(url, args.title)
