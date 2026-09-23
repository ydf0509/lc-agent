"""Frameless pywebview demo: Vue 3 (CDN) + custom window-control buttons.

Usage:
    D:\\ProgramData\\Miniconda3\\envs\\py312\\python.exe D:\\codes\\lc-agent\\my_dir\\frameless_demo\\main.py

Window is borderless (frameless=True). The title bar is custom HTML:
- drag: title bar has class "pywebview-drag-region", easy_drag=False
- buttons: minimize / maximize-restore / close, wired via pywebview.api
"""

import webview


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
        "frameless-demo",
        html=MAIN_HTML,
        width=900,
        height=640,
        frameless=True,
        easy_drag=False,  # only the .pywebview-drag-region title bar drags
        text_select=True,
        js_api=api,
    )
    api._window = window
    webview.start(debug=False)


if __name__ == "__main__":
    main()
