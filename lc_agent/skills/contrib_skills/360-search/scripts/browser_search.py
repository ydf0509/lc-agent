"""通过 agent-browser 在浏览器里执行 360 搜索（HTTP 通道被限流时使用）。

与 so360_search_cli.py search 的区别：
- 走真实浏览器会话，复用已通过滑块验证的 cookie/状态
- 自动读取页面上的真实翻页链接（带 psid，手工拼 pn 会被打回第一页）
- 跨页按 URL/标题去重
- 输出 JSON 结构与 so360_search_cli.py search 完全一致

用法:
    python scripts/browser_search.py --session so360 --keyword "关键词" --num 30
    python scripts/browser_search.py --session so360 --keyword "关键词" --num 10 --debug
    python scripts/browser_search.py --session so360 --keyword "关键词" --dry-run

退出码:
    0  成功（可能少于 --num，取决于 360 实际可翻页深度）
    4  页面处于验证码状态，需要先运行 solve_slider.py
    2  其他错误
"""
import argparse
import json
import sys
import time
from urllib.parse import parse_qs, quote, urlparse

from solve_slider import ab_eval, ab_run, current_url

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
from so360_search_cli import parse_date

SEARCH_URL = "https://www.so.com/s"

# 提取一条结果：过滤垂直模块（data-mohe-type）、无 mdurl 的 AI 卡片、360 自有域名
RESULTS_JS = """JSON.stringify((()=>{
const out=[];
for(const li of document.querySelectorAll('li.res-list')){
  if(li.querySelector('[data-mohe-type]')||li.matches('[data-mohe-type]'))continue;
  const a=li.querySelector('h3 a');if(!a)continue;
  const u=a.getAttribute('data-mdurl')||'';
  if(!u.startsWith('http'))continue;
  let host='';try{host=new URL(u).hostname}catch(e){continue}
  if(/(^|\\.)(so\\.com|360kan\\.com|hao\\.360\\.com)$/.test(host))continue;
  const p=li.querySelector('p.res-desc,.res-list-summary');
  out.push({title:a.innerText.trim(),url:u,abstract:p?p.innerText.trim():''});
}
return out;
})())"""

PAGE_LINKS_JS = """JSON.stringify([...document.querySelectorAll('a')]
  .filter(a=>/pn=\\d+/.test(a.href))
  .map(a=>({t:a.innerText.trim(),h:a.href}))
  .slice(0,30))"""

CLICK_PAGE_TMPL = """JSON.stringify((()=>{
const a=[...document.querySelectorAll('a')].find(a=>a.innerText.trim()==='%d'&&/pn=\\d+/.test(a.href));
if(a){a.click();return 'OK:'+a.href.slice(0,200)}
const n=[...document.querySelectorAll('a')].find(a=>a.innerText.includes('下一页'));
if(n){n.click();return 'NEXT:'+n.href.slice(0,200)}
return 'NOT_FOUND';
})())"""

CAPTCHA_JS = """JSON.stringify({
  captcha: !!document.querySelector('.v-target-btn'),
  noResult: document.body.innerText.includes('抱歉，未找到相关结果'),
  url: location.href
})"""


def _norm_url(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/").lower()
    except Exception:
        return url.lower()


def _pn_of(href: str) -> int | None:
    try:
        vals = parse_qs(urlparse(href).query).get("pn")
        return int(vals[0]) if vals else None
    except Exception:
        return None


def _open_page(session: str, url: str, debug: bool) -> None:
    """打开页面；首条命令可能因 daemon 启动而超时，超时属正常。"""
    ab_run(["--session", session, "open", url], timeout=20)
    ab_run(["--session", session, "wait", "--load", "networkidle"], timeout=20)
    time.sleep(1.5)
    if debug:
        sys.stderr.write(f"[open] {url} -> {current_url(session)}\n")


def browser_search(session: str, keyword: str, num: int, max_pages: int, debug: bool):
    start_url = f"{SEARCH_URL}?q={quote(keyword)}"
    _open_page(session, start_url, debug)

    state = ab_eval(session, CAPTCHA_JS, timeout=20) or {}
    if state.get("captcha"):
        return {"error": "captcha", "hint": f"先运行 python scripts/solve_slider.py --session {session}"}, 4

    results: list[dict] = []
    seen_url: set[str] = set()
    seen_title: set[tuple] = set()
    current_pn = 1

    for page in range(1, max_pages + 1):
        items = ab_eval(session, RESULTS_JS, timeout=20) or []
        added = 0
        for it in items:
            url = (it.get("url") or "").strip()
            title = (it.get("title") or "").strip()
            if not url or not title:
                continue
            nu = _norm_url(url)
            site = urlparse(url).netloc
            key = (title, site)
            if nu in seen_url or key in seen_title:
                continue
            seen_url.add(nu)
            seen_title.add(key)
            abstract = (it.get("abstract") or "").strip()
            results.append({
                "title": title,
                "url": url,
                "abstract": abstract,
                "date": parse_date(abstract[:120]) if abstract else "",
                "site": site,
                "is_advertisement": False,
            })
            added += 1

        if debug:
            sys.stderr.write(
                f"[page {page}] pn={current_pn} got={len(items)} new={added} "
                f"total={len(results)} url={current_url(session)}\n"
            )

        if len(results) >= num:
            break

        target_pn = current_pn + 1
        # 关键：必须在页面内点击页码链接（a.click()）。
        # 实测直接 open 带 pn 的 URL 会被 360 静默打回第 1 页；agent-browser 的
        # 选择器 click 也可能点到非页码元素而不跳转。
        clicked = ab_eval(session, CLICK_PAGE_TMPL % target_pn, timeout=20)
        if not clicked or str(clicked).startswith("NOT_FOUND"):
            if debug:
                sys.stderr.write(f"[stop] 页面上没有可点击的第 {target_pn} 页链接，结束\n")
            break
        if debug:
            sys.stderr.write(f"[click] {clicked}\n")

        ab_run(["--session", session, "wait", "--load", "networkidle"], timeout=20)
        time.sleep(1.8)

        cur = current_url(session)
        if f"pn={target_pn}" not in cur:
            sys.stderr.write(
                f"警告: 点击第 {target_pn} 页后 URL 未带 pn（可能被打回第 1 页），"
                f"已返回前 {len(results)} 条结果\n"
            )
            break
        current_pn = target_pn

        st = ab_eval(session, CAPTCHA_JS, timeout=20) or {}
        if st.get("captcha"):
            sys.stderr.write("警告: 翻页途中触发验证码，返回已获取的部分结果\n")
            break

        time.sleep(0.8)

    return results[:num], 0


def main() -> None:
    p = argparse.ArgumentParser(description="用 agent-browser 在浏览器里执行 360 搜索（HTTP 被限流时用）")
    p.add_argument("--keyword", required=True, help="搜索关键词")
    p.add_argument("--session", default="so360", help="agent-browser 会话名（默认 so360，必须与验证码会话一致）")
    p.add_argument("--num", type=int, default=30, help="目标条数，1~50（默认 30）")
    p.add_argument("--max-pages", type=int, default=8, help="最多翻页数（默认 8）")
    p.add_argument("--debug", action="store_true", help="在 stderr 输出每页的 url/条数")
    p.add_argument("--dry-run", action="store_true", help="只检查页面状态，不搜索")
    args = p.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.dry_run:
        state = ab_eval(args.session, CAPTCHA_JS, timeout=20)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return

    num = min(max(args.num, 1), 50)
    payload, code = browser_search(args.session, args.keyword, num, args.max_pages, args.debug)

    if code != 0:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(code)

    out = {
        "query": args.keyword,
        "mkt": "so360-browser",
        "total": len(payload),
        "results": payload,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
