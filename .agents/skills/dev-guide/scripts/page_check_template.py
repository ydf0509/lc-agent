"""页面 UI 验证骨架：注入登录态 → 打开页面 → 等元素 → DOM 断言 → 截图。

复制本文件改【配置区】和【断言区】即可。实测要点（2026-09-10）：
- 必须显式 executable_path 指向已装的 chromium（Python playwright 自带版本与本机装的常不一致）
- 不要用 agent-browser，它在本机工具会话里 open 会卡死
- secret 从 bfzs config.jsonc 的 auth.secret 读，dev 环境专用，别外传

运行：D:\\ProgramData\\Miniconda3\\envs\\py312\\python.exe page_check_template.py
"""
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from playwright.sync_api import sync_playwright

# ---------------- 配置区 ----------------
CHROME_EXE = r'C:\Users\ydf6\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe'
BFZS_DIR = r'D:\codes\lc-agent-bfzs'
URL = 'http://127.0.0.1:8001/#/admin/usage'
WAIT_SELECTOR = '.usage-admin'          # 页面加载完成的标志元素
VIEWPORT = {'width': 1800, 'height': 900}
SHOT = r'D:\codes\lc-agent\my_dir\page_check.png'
# ----------------------------------------


def read_secret() -> str:
    """从 config.jsonc 抓 auth.secret（jsonc 有注释，用正则抓）。"""
    raw = open(BFZS_DIR + r'\config.jsonc', encoding='utf-8').read()
    m = re.search(r'"auth"\s*:\s*\{[^}]*?"secret"\s*:\s*"([^"]+)"', raw, re.S)
    if not m:
        raise SystemExit('config.jsonc 里找不到 auth.secret')
    return m.group(1)


def read_admin() -> tuple[str, str]:
    """从 users 表取一个 admin 的 (id, username)。"""
    con = sqlite3.connect(BFZS_DIR + r'\bfzs_data.db')
    try:
        row = con.execute(
            "select id, username from users where role='admin' limit 1"
        ).fetchone()
    finally:
        con.close()
    if not row:
        raise SystemExit('users 表里没有 admin 用户')
    return row[0], row[1]


def main():
    uid, uname = read_admin()
    token = jwt.encode(
        {
            'sub': uid, 'username': uname, 'role': 'admin',
            'exp': datetime.now(timezone.utc) + timedelta(hours=2),
        },
        read_secret(),
        algorithm='HS256',
    )

    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_EXE)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1.4)
        # 打开任何页面之前注入 token，路由守卫直接放过
        ctx.add_init_script(
            "try { localStorage.setItem('token', %s); } catch (e) {}" % json.dumps(token)
        )
        page = ctx.new_page()
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)))

        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_selector(WAIT_SELECTOR, timeout=25000)

        # ---------------- 断言区（按页面改这里）----------------
        page.wait_for_timeout(1000)  # 等异步数据渲染
        print('页面标题:', page.title())
        print('当前 URL:', page.url)
        body = page.inner_text('body')
        print('页面文本前 200 字:', repr(body[:200]))
        # ------------------------------------------------------

        page.screenshot(path=SHOT, full_page=True)
        browser.close()

    print('截图:', SHOT)
    print('控制台错误:', '\n'.join(errors) if errors else '(无)')


if __name__ == '__main__':
    main()
