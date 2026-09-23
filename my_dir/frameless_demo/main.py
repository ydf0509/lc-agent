"""Captionless (not frameless) pywebview demo: Vue 3 (CDN) + custom window buttons.

Q1 整套验证：frameless=False 正常起窗（保留 WS_THICKFRAME，原生 resize 满血），
等 shown 事件后用 ctypes 去掉 WS_CAPTION（只去标题栏，不碰左右下边框），
再把 Form.MaximizedBounds 锁到当前屏工作区（最大化不盖任务栏）。

Windows-only（用到 ctypes.windll + WinForms）。

Usage:
    D:\\ProgramData\\Miniconda3\\envs\\py312\\python.exe D:\\codes\\lc-agent\\my_dir\\frameless_demo\\main.py

- drag: title bar has class "pywebview-drag-region", easy_drag=False
- buttons: minimize / maximize-restore / close, wired via pywebview.api
"""

import ctypes
import traceback
from ctypes import wintypes

import webview


WS_CAPTION = 0x00C00000
GWL_STYLE = -16
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020


def _apply_captionless_fix(window):
    """shown 回调：去 WS_CAPTION + 锁 MaximizedBounds=工作区（Q1 整套）。

    时机：WinForms Shown 之后 -> hwnd 必已创建；只跑一次，窗口刚露面，看不到闪烁。
    线程：pywebview 的 Event.set() 把回调跑在新起的事件线程里，
    凡是碰 WinForms Form 的操作都经 native.Invoke(Action(...)) 送回 UI 线程执行。
    """
    native = window.native  # BrowserForm；shown 时必已由 BrowserForm.__init__ 赋值
    if native is None:
        print("[fix] native is None, skip patch")
        return
    print("[fix] shown fired, patching on UI thread...")

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
    # 表现为标题栏拖拽失效。独立实例的 prototype 只影响本 demo。
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    # HWND 在 64 位下是 64 位，不声明 argtypes 会被 ctypes 按 32 位 int 截断 -> 必须声明
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL

    def _patch():
        try:
            form = window.native
            hwnd = form.Handle.ToInt64()
            before = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, (before & ~WS_CAPTION) & 0xFFFFFFFF)
            # 不移动、不改尺寸，只让 OS 重算非客户区（多余边框消失）
            user32.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
            after = user32.GetWindowLongW(hwnd, GWL_STYLE)
            # 最大化锁进当前屏工作区：任务栏露出来
            wa = WinForms.Screen.FromHandle(form.Handle).WorkingArea
            form.MaximizedBounds = Rectangle(wa.X, wa.Y, wa.Width, wa.Height)
            print(
                f"[fix] style before=0x{before & 0xFFFFFFFF:08X} "
                f"after=0x{after & 0xFFFFFFFF:08X} "
                f"caption_removed={not (after & WS_CAPTION)}"
            )
            print(f"[fix] MaximizedBounds=({wa.X},{wa.Y},{wa.Width},{wa.Height})")
        except Exception:
            traceback.print_exc()

    native.Invoke(Action(_patch))
    print("[fix] patch done")


MAIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { height: 100%; font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif; }
  body { background: #f3f4f6; display: flex; flex-direction: column; overflow: hidden; }

  /* ===== custom title bar ===== */
  #titlebar {
    height: 42px; flex: 0 0 42px;
    background: #111827; color: #e5e7eb;
    display: flex; align-items: center;
    user-select: none; -webkit-user-select: none;
  }
  #titlebar .logo { padding: 0 12px; font-size: 15px; font-weight: 600; color: #93c5fd; }
  #titlebar .title { font-size: 13px; color: #9ca3af; flex: 1; overflow: hidden;
                     white-space: nowrap; text-overflow: ellipsis; }
  .win-btn {
    width: 46px; height: 42px; border: none; background: transparent;
    color: #d1d5db; font-size: 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
  }
  .win-btn:hover { background: #374151; }
  .win-btn.close:hover { background: #e81123; color: #fff; }

  /* ===== content ===== */
  #app { flex: 1; padding: 16px; overflow: auto; }
  .card { background: #fff; border-radius: 10px; padding: 18px 20px;
          box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 14px; }
  .card h2 { font-size: 16px; margin-bottom: 10px; color: #1f2937; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  button.action { padding: 8px 16px; border: none; border-radius: 6px;
                  background: #2563eb; color: #fff; font-size: 13px; cursor: pointer; }
  button.action:hover { background: #1d4ed8; }
  button.action.green { background: #059669; } button.action.green:hover { background: #047857; }
  button.action.amber { background: #d97706; } button.action.amber:hover { background: #b45309; }
  input[type=text] { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px;
                     font-size: 13px; width: 280px; }
  .msg { margin-top: 10px; font-size: 13px; color: #374151; word-break: break-all; }
  .hint { font-size: 12px; color: #6b7280; margin-top: 8px; line-height: 1.8; }
</style>
<script src="https://unpkg.com/vue@3.4.38/dist/vue.global.prod.js"></script>
</head>
<body>
  <!-- drag region: only THIS bar moves the window (easy_drag=False) -->
  <div id="titlebar" class="pywebview-drag-region">
    <span class="logo">&#9670; frameless-demo</span>
    <span class="title">pywebview frameless + Vue3 &#8212; drag me anywhere on this bar</span>
    <button class="win-btn" id="btn-min" title="&#26368;&#23567;&#21270;">&#8211;</button>
    <button class="win-btn" id="btn-max" title="&#26368;&#22823;&#21270;/&#36824;&#21407;">&#9744;</button>
    <button class="win-btn close" id="btn-close" title="&#20851;&#38381;">&#10005;</button>
  </div>

  <div id="app">
    <div class="card">
      <h2>Vue 3 &#20439;&#39564; (CDN &#21152;&#36733;)</h2>
      <div class="row">
        <input type="text" v-model="name" placeholder="&#36755;&#20837;&#21517;&#23383;" />
        <button class="action" @click="greet">&#21628;&#21483; Python &#21518;&#31471;</button>
      </div>
      <div class="msg" v-if="reply">{{ reply }}</div>
      <div class="msg">&#35745;&#25968;&#22120;: {{ count }}
        <button class="action green" @click="count++">+1</button>
      </div>
      <div class="hint">1. &#25302;&#21160;&#28145;&#33394;&#26631;&#39064;&#26639;&#31227;&#21160;&#31383;&#21475;&#65288;&#20854;&#20182;&#21306;&#22495;&#19981;&#21487;&#25302;&#21160;&#65289;<br/>
      2. &#21491;&#19978;&#35282;&#19977;&#20010;&#25353;&#38062;&#20998;&#21035;&#26159;&#26368;&#23567;&#21270;&#12289;&#26368;&#22823;&#21270;&#20999;&#25442;&#12289;&#20851;&#38381;&#31383;&#21475;&#12290;</div>
    </div>
    <div class="card">
      <h2>&#31383;&#21475;&#25805;&#20316; (Vue &#35843;&#29992; pywebview.api)</h2>
      <div class="row">
        <button class="action amber" @click="minWin">&#26368;&#23567;&#21270;</button>
        <button class="action amber" @click="maxWin">&#26368;&#22823;&#21270;</button>
        <button class="action amber" @click="restoreWin">&#36824;&#21407;</button>
      </div>
    </div>
  </div>

<script>
const { createApp, ref } = Vue;
createApp({
  setup() {
    const name = ref('');
    const reply = ref('');
    const count = ref(0);
    async function callApi(fn, arg) {
      if (window.pywebview && window.pywebview.api && window.pywebview.api[fn]) {
        // NOTE: pywebview JS bridge always forwards `arguments` as an array and
        // Python side does func(*param). No-arg Python methods MUST be called
        // with zero JS args, otherwise an extra `undefined` arrives and
        // minimize()/maximize()/restore()/close() get one arg too many.
        return arg === undefined
          ? await window.pywebview.api[fn]()
          : await window.pywebview.api[fn](arg);
      }
      return '[pywebview bridge not ready]';
    }
    return {
      name, reply, count,
      greet: async () => { reply.value = await callApi('greet', name.value || 'world'); },
      minWin: () => callApi('minimize'),
      maxWin: () => callApi('maximize'),
      restoreWin: () => callApi('restore'),
    };
  }
}).mount('#app');

// plain-JS wiring for the titlebar buttons (work even before Vue mounts)
document.getElementById('btn-min').onclick = () => window.pywebview.api.minimize();
document.getElementById('btn-max').onclick = () => window.pywebview.api.toggle_max();
document.getElementById('btn-close').onclick = () => window.pywebview.api.close();
</script>
</body>
</html>
"""


class Api:
    # NOTE: window ref MUST be underscore-prefixed. pywebview enumerates all
    # public attributes of js_api and recurses into them; a public `window`
    # attr makes it walk the whole native WinForms object graph
    # (window.native.AccessibilityObject.Bounds.Empty.Empty...), causing
    # "maximum recursion depth exceeded" and a hung/busy window.
    def __init__(self):
        self._window = None
        self._maximized = False

    def greet(self, name):
        return f"Hello, {name}! from Python backend."

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

    def close(self):
        if self._window:
            self._window.destroy()


def main():
    api = Api()
    window = webview.create_window(
        "captionless-demo",
        html=MAIN_HTML,
        width=900,
        height=640,
        frameless=False,  # 保持 WS_THICKFRAME：原生 resize 满血；标题栏稍后用 ctypes 去掉
        easy_drag=False,  # only the .pywebview-drag-region title bar drags
        text_select=True,
        js_api=api,
    )
    api._window = window
    # shown 只 fire 一次（BrowserForm.Shown）：封口，走 _apply_captionless_fix
    window.events.shown += lambda: _apply_captionless_fix(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
