#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""必应搜索 CLI — 按关键词搜索网页 + 阅读网页详细内容（免费，无需 API key）。

用法示例:
    bing_search_cli.py search "python 爬虫"
    bing_search_cli.py search "langchain tutorial" --num 5
    bing_search_cli.py search "fastapi" --mkt zh-CN
    bing_search_cli.py extract "https://example.com/article"
    bing_search_cli.py extract "https://example.com/article" --max-chars 5000

依赖: requests, beautifulsoup4, trafilatura, curl_cffi
      (pip install requests beautifulsoup4 trafilatura curl_cffi)

输出: JSON 到 stdout。退出码: 0=成功, 1=操作失败或被反爬拦截。

说明:
- search 单页上限 10 条，不支持翻页（必应服务端锁死翻页：first 参数、
  官方下一页链接、带 cookie 会话、RSS、浏览器指纹客户端均只能拿到第一页）。
  需要更多候选结果时，换几个不同角度的关键词分别搜索。
- search 默认自动按关键词语言选择市场（中文→国内版，其他→国际版），
  国内版无结果时自动回退到国际版重试。
- 国际版结果的 url 是 bing.com/ck/a 跳转链接，本脚本直接解码其中的
  base64 参数还原真实 URL，extract 拿到的就是真实地址。
"""
import argparse
import base64
import json
import re
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# 缺少依赖时直接抛 ImportError，由用户自行安装
import requests
import trafilatura
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SEARCH_URL = "https://www.bing.com/search"
# Bing 单页上限 10 条（count 传大值也只返回 10；实测 first 翻页参数被服务端忽略，
# HTML/RSS/官方下一页链接/带 cookie 会话全都只能拿第一页），所以不做翻页
PAGE_SIZE = 10

# 摘要节点选择器（Bing 前端 class 可能变化，多备几个）
SNIPPET_SELECTORS = (
    "p.b_lineclamp4",
    "p.b_lineclamp3",
    "p.b_lineclamp2",
    ".b_caption p",
    ".b_caption",
    "p",
)

# 英文月份 -> 数字
EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def decode_bing_redirect(url: str) -> str:
    """解码 bing.com/ck/a 跳转链接里的 u=a1<base64url> 参数，还原真实 URL。

    非跳转链接原样返回；解码失败也原样返回。
    """
    try:
        parsed = urlparse(url)
        if "bing.com" not in parsed.netloc or not parsed.path.startswith("/ck/"):
            return url
        u = parse_qs(parsed.query).get("u", [""])[0]
        if not u.startswith("a1"):
            return url
        b64 = u[2:].replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        real = base64.b64decode(b64).decode("utf-8", errors="replace")
        return real if real.startswith("http") else url
    except Exception:
        return url


def parse_date(text: str) -> str:
    """从摘要文本解析发布日期，支持绝对日期和相对时间（中英文）。

    返回 YYYY-MM-DD；解析不出返回空串。
    """
    now = datetime.now()

    # ISO: 2026-01-08
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 中文: 2026年1月8日
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 英文: Dec 29, 2025 / Mar 2, 2026
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),\s*(\d{4})", text)
    if m:
        month = EN_MONTHS.get(m.group(1)[:3].lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(2))).strftime("%Y-%m-%d")
            except ValueError:
                pass

    # 相对时间（中文）: 1 天前 / 3 小时前 / 2 个月前
    m = re.search(r"(\d+)\s*(分钟|小时|天|周|个月|月|年)前", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"分钟": timedelta(minutes=n), "小时": timedelta(hours=n),
                 "天": timedelta(days=n), "周": timedelta(weeks=n),
                 "个月": timedelta(days=30 * n), "月": timedelta(days=30 * n),
                 "年": timedelta(days=365 * n)}[unit]
        return (now - delta).strftime("%Y-%m-%d")

    # 相对时间（英文）: 3 days ago / 2 hours ago
    m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)s?\s+ago", text, re.IGNORECASE)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        delta = {"minute": timedelta(minutes=n), "hour": timedelta(hours=n),
                 "day": timedelta(days=n), "week": timedelta(weeks=n),
                 "month": timedelta(days=30 * n), "year": timedelta(days=365 * n)}[unit]
        return (now - delta).strftime("%Y-%m-%d")

    return ""


def _build_session(http_client: str):
    if http_client == "curl_cffi":
        session = curl_requests.Session(impersonate="chrome")
    else:
        session = requests.Session()
    session.headers.update(HEADERS)
    return session


def _fetch_search_page(session, keyword: str, mkt: str) -> str:
    """请求搜索结果页（固定第一页），返回 HTML 文本。被拦截时抛 RuntimeError。"""
    params = {"q": keyword, "mkt": mkt, "first": 1, "count": PAGE_SIZE}
    if mkt == "en-US":
        params["setlang"] = "en"
    resp = session.get(SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    html = resp.text
    # 反爬判定：正常无结果页有 li.b_no 节点；被拦时是验证码/异常页
    blocked_markers = ("异常流量", "unusual traffic", "verify you are human", "验证您是真人")
    if any(marker in html for marker in blocked_markers):
        raise RuntimeError("触发必应反爬拦截。请降低调用频率（建议间隔 2 秒以上）后重试")
    return html


def _parse_results(html: str, num: int) -> list[dict]:
    """解析单页 HTML，最多返回 num 条结果。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for li in soup.select("li.b_algo"):
        h2 = li.find("h2")
        a = h2.find("a") if h2 else None
        if not a:
            continue
        title = a.get_text(strip=True)
        raw_url = a.get("href", "")
        url = decode_bing_redirect(raw_url)

        abstract = ""
        for sel in SNIPPET_SELECTORS:
            node = li.select_one(sel)
            if node:
                abstract = node.get_text(" ", strip=True)
                break

        # 广告判定：b_algo 内带 Ad/广告 角标或链接走广告点击域
        classes = " ".join(li.get("class", []))
        is_advertisement = (
            "b_ad" in classes
            or li.select_one(".b_adSlug, .b_moppromo") is not None
            or abstract.startswith(("Ad ·", "广告 ·"))
            or "/aclick" in raw_url
        )

        # site：真实 URL 的域名（跳转链接已解码，比页面展示的截断域名可靠）
        site = urlparse(url).netloc if url.startswith("http") else ""

        results.append({
            "title": title,
            "url": url,
            "abstract": abstract,
            "date": parse_date(abstract[:80]),
            "site": site,
            "is_advertisement": is_advertisement,
        })
        if len(results) >= num:
            break
    return results


def _search_with_mkt(session, keyword: str, num: int, mkt: str) -> list[dict]:
    """用指定市场请求搜索结果（单页上限 10 条）。"""
    html = _fetch_search_page(session, keyword, mkt)
    return _parse_results(html, num)


def search_bing(keyword: str, num: int = 10, mkt: str = "auto",
                http_client: str = "curl_cffi") -> tuple[list[dict], str]:
    """按关键词搜索必应，返回 (结果列表, 实际使用的市场)。

    num: 返回条数，单页上限 10。
    mkt: "auto"（默认，按关键词语言自动选择并带无结果回退）、"zh-CN"（国内版）、
        "en-US"（国际版）。
    http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
        个别环境对 curl_cffi 不兼容时可改用 "requests"。
    """
    session = _build_session(http_client)

    if mkt != "auto":
        return _search_with_mkt(session, keyword, num, mkt), mkt

    # auto：中文关键词用国内版，其他用国际版；无结果时互换市场重试一次
    primary = "zh-CN" if _has_cjk(keyword) else "en-US"
    secondary = "en-US" if primary == "zh-CN" else "zh-CN"
    results = _search_with_mkt(session, keyword, num, primary)
    if not results:
        results = _search_with_mkt(session, keyword, num, secondary)
        return results, (secondary if results else primary)
    return results, primary


def extract_url(url: str, max_chars: int = 20000, http_client: str = "curl_cffi") -> dict:
    """抓取网页并提取正文内容，返回 title / content / date / author / sitename。

    Args:
        url: 要阅读的网页 URL。传 bing.com/ck/a 跳转链接时会先解码成真实 URL 再抓取。
        max_chars: 正文最多返回的字符数，超出截断；传 0 表示不截断。
        http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
            个别站点对 curl_cffi 不兼容（如证书、HTTP/2 异常）时改用 "requests"。
    """
    url = decode_bing_redirect(url)

    if http_client == "curl_cffi":
        resp = curl_requests.get(url, impersonate="chrome", timeout=15, allow_redirects=True)
    else:
        resp = requests.get(url, headers=HEADERS, timeout=15)

    real_url = resp.url or url

    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} 访问失败: {real_url}")

    # 正文：extract() 稳定可用（trafilatura 2.2.0 的 bare_extraction text 字段有 bug）
    full_text = trafilatura.extract(
        resp.content, output_format="markdown", include_links=True
    )
    if not full_text:
        raise RuntimeError(f"提取失败: {real_url}（页面无正文，可能是 JS 动态渲染页面或反爬，请用浏览器重新尝试打开）")

    meta = trafilatura.extract_metadata(resp.content)

    content = full_text
    truncated = False
    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars]
        truncated = True

    return {
        "url": real_url,
        "title": (getattr(meta, "title", "") if meta else "") or "",
        "date": (getattr(meta, "date", "") if meta else "") or "",
        "author": (getattr(meta, "author", "") if meta else "") or "",
        "sitename": (getattr(meta, "sitename", "") if meta else "") or "",
        "content": content,
        "length": len(full_text),
        "truncated": truncated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="必应搜索 CLI：search 按关键词搜索网页；extract 阅读网页详细内容"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search 子命令
    p_search = subparsers.add_parser("search", help="按关键词搜索，返回标题/链接/摘要/日期")
    p_search.add_argument("keyword", help="要搜索的关键词")
    p_search.add_argument("--num", type=int, default=10, help="返回条数，1~10（默认 10，必应单页上限 10 条）")
    p_search.add_argument(
        "--mkt",
        choices=["auto", "zh-CN", "en-US"],
        default="auto",
        help="市场：auto（默认，按关键词语言自动选择，国内版无结果自动回退国际版）；zh-CN 国内版；en-US 国际版",
    )
    p_search.add_argument(
        "--client",
        choices=["requests", "curl_cffi"],
        default="curl_cffi",
        help="请求方式：curl_cffi（默认，模拟 Chrome 指纹）；个别环境不兼容时改用 requests",
    )

    # extract 子命令
    p_extract = subparsers.add_parser("extract", help="抓取网页并提取正文内容")
    p_extract.add_argument("url", help="要阅读的网页 URL（可直接传 search 返回的 url）")
    p_extract.add_argument(
        "--max-chars",
        type=int,
        default=20000,
        help="正文最大返回字符数，超出截断（默认 20000，传 0 表示不截断）",
    )
    p_extract.add_argument(
        "--client",
        choices=["requests", "curl_cffi"],
        default="curl_cffi",
        help="请求方式：curl_cffi（默认，模拟 Chrome 指纹）；个别站点不兼容时改用 requests",
    )

    args = parser.parse_args()

    if args.command == "search":
        num = min(max(args.num, 1), PAGE_SIZE)
        try:
            results, mkt_used = search_bing(
                args.keyword, num=num, mkt=args.mkt, http_client=args.client
            )
        except Exception as exc:
            sys.stderr.write(f"搜索失败: {exc}\n")
            sys.exit(1)
        payload = {
            "query": args.keyword,
            "mkt": mkt_used,
            "total": len(results),
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:  # extract
        try:
            data = extract_url(
                args.url, max_chars=args.max_chars, http_client=args.client
            )
        except Exception as exc:
            sys.stderr.write(f"阅读失败: {exc}\n")
            sys.exit(1)
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
