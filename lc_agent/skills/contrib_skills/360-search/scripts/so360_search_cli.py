#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""360 搜索 CLI — 按关键词搜索网页 + 阅读网页详细内容（免费，无需 API key）。

用法示例:
    so360_search_cli.py search "python 爬虫"
    so360_search_cli.py search "langchain tutorial" --num 20
    so360_search_cli.py extract "https://example.com/article"
    so360_search_cli.py extract "https://example.com/article" --max-chars 5000

依赖: requests, beautifulsoup4, trafilatura, curl_cffi
      (pip install requests beautifulsoup4 trafilatura curl_cffi)

输出: JSON 到 stdout。退出码: 0=成功, 1=操作失败或被反爬拦截。

说明:
- 结果节点的 data-mdurl 属性直接带真实 URL，不需要解析 so.com/link 跳转。
- pn 参数翻页有效；脚本按 --num 自动翻页，去重后返回。
- 垂直模块（短视频/影视卡片）和 360 AI 摘要结果（无真实 URL）会被过滤，
  因此单页可用的自然结果通常少于 10 条。
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

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

SEARCH_URL = "https://www.so.com/s"
MAX_PAGES = 10         # 最多翻 10 页，确保默认 30 条能凑够
PAGE_DELAY = 0.5       # 翻页间隔（秒），降低触发限流概率

# 360 自家域名（垂直聚合页/AI 摘要），不是真实搜索结果
INTERNAL_HOSTS = ("so.com", "360kan.com", "hao.360.com", "ai.so.com")

# 摘要节点选择器（360 前端 class 有几种变体）
SNIPPET_SELECTORS = (
    "p.res-desc",
    "span.res-list-summary",
    "div.res-rich",
    "div.res-desc",
)

# 英文月份 -> 数字
EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


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


def _fetch_page(session, keyword: str, page: int) -> str:
    """请求一页搜索结果（pn 从 1 开始），返回 HTML 文本。

    返回空串表示 360 返回了"抱歉，未找到相关结果"页（真实无结果，或软限流）。
    命中真实验证码页时抛 RuntimeError。
    """
    resp = session.get(
        SEARCH_URL,
        params={"q": keyword, "pn": page},
        timeout=12,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    html = resp.text
    final_url = str(resp.url)

    # 真验证码页：qcaptcha 域名且不是 noresult 页，或页面含验证码字样
    if "请输入验证码" in html or ("qcaptcha.so.com" in final_url and "noresult" not in final_url):
        raise RuntimeError(
            "触发 360 验证码（HTTP 通道被限制）。请改用 agent-browser 打开 "
            f"https://www.so.com/s?q={quote(keyword)} 完成滑块验证后继续，"
            "操作步骤见 SKILL.md 的“HTTP 被验证码拦截时”一节；"
            "或改用 baidu-search / sogou-search"
        )

    # 360 的"无结果页"：查询无结果或被软限流时都会 302 到这里，交给上层判别
    if "抱歉，未找到相关结果" in html:
        return ""

    # 翻页请求被静默打回首页（final URL 丢了 pn）时，视为没有更多结果
    if page > 1 and f"pn={page}" not in final_url:
        return ""

    return html


def _is_soft_blocked(session) -> bool:
    """用对照查询判断"无结果页"是软限流还是查询本身无结果。

    360 软限流是间歇性的（个别请求会漏过真结果），所以要求连续 2 次对照查询
    都拿到真实结果，才认定"未被限流"。
    """
    for _ in range(2):
        try:
            html = _fetch_page(session, "百度", 1)
        except Exception:
            return True
        if html != "":
            time.sleep(0.5)
            continue
        return True
    return False


def _is_internal_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host.endswith(h) or host == h for h in INTERNAL_HOSTS)


def _parse_page(html: str) -> list[dict]:
    """解析单页 HTML，返回自然搜索结果列表。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    for li in soup.select("li.res-list"):
        # 跳过垂直模块（短视频/影视/百科卡片等）
        if li.find(attrs={"data-mohe-type": True}):
            continue

        h3 = li.find("h3")
        a = h3.find("a") if h3 else None
        if not a:
            continue

        # data-mdurl 是真实地址；没有的通常是 360 AI 摘要卡片，跳过
        url = (a.get("data-mdurl") or "").strip().replace("&amp;", "&")
        if not url.startswith("http") or _is_internal_url(url):
            continue

        title = a.get_text(" ", strip=True)

        abstract = ""
        for sel in SNIPPET_SELECTORS:
            node = li.select_one(sel)
            if node:
                abstract = node.get_text(" ", strip=True)
                if abstract:
                    break

        # 广告判定：广告卡片常带 ad 类名或"广告"角标
        classes = " ".join(li.get("class", []))
        linkinfo = li.select_one("p.g-linkinfo")
        linkinfo_text = linkinfo.get_text(" ", strip=True) if linkinfo else ""
        is_advertisement = (
            "ad" in classes.split()
            or "ec_ad" in classes
            or linkinfo_text.startswith("广告")
            or abstract.startswith("广告")
        )

        results.append({
            "title": title,
            "url": url,
            "abstract": abstract,
            "date": parse_date(abstract[:80]),
            "site": urlparse(url).netloc,
            "is_advertisement": is_advertisement,
        })

    return results


def search_360(keyword: str, num: int = 30, http_client: str = "curl_cffi") -> list[dict]:
    """按关键词搜索 360，自动翻页并去重，最多返回 num 条。

    num: 返回条数，1~50。360 单页自然结果通常 5~10 条，脚本会按 pn 翻页凑够。
    http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
        个别环境不兼容时可改用 "requests"。
    """
    session = _build_session(http_client)
    results: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        if len(results) >= num:
            break
        try:
            html = _fetch_page(session, keyword, page)
        except RuntimeError as exc:
            # 翻页途中被拦：返回已抓到的部分结果，不整单失败
            if results:
                sys.stderr.write(
                    f"警告: 翻页途中触发限制，返回已获取的 {len(results)} 条结果（{exc}）\n"
                )
                break
            raise
        if html == "":
            # 无结果页：区分"真无结果"和"软限流"
            if page != 1 or results:
                break
            if _is_soft_blocked(session):
                raise RuntimeError(
                    "360 触发软限流（对任何查询都返回无结果页）。该限制按 IP 生效，"
                    "HTTP 通道短时间内无法恢复。请改用 agent-browser 打开 "
                    f"https://www.so.com/s?q={quote(keyword)} "
                    "完成滑块验证后直接读取页面结果（步骤见 SKILL.md 的“HTTP 被验证码拦截时”一节）；"
                    "或改用 baidu-search / sogou-search"
                )
            # 对照查询正常：再给目标查询一次机会，排除间歇性无结果页
            time.sleep(PAGE_DELAY)
            html = _fetch_page(session, keyword, page)
            if html == "":
                break
        page_results = _parse_page(html)

        new_count = 0
        for item in page_results:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            results.append(item)
            new_count += 1
            if len(results) >= num:
                break

        # 本页没有新结果（到底了或被拦）就停止翻页
        if new_count == 0:
            break
        if page < MAX_PAGES:
            time.sleep(PAGE_DELAY)

    return results[:num]


def extract_url(url: str, max_chars: int = 20000, http_client: str = "curl_cffi") -> dict:
    """抓取网页并提取正文内容，返回 title / content / date / author / sitename。

    Args:
        url: 要阅读的网页 URL。传 search 返回的真实 url 最稳妥；
            传 so.com/link 跳转链接时可能因签名校验失败（HTTP 400）。
        max_chars: 正文最多返回的字符数，超出截断；传 0 表示不截断。
        http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
            个别站点不兼容时可改用 "requests"。
    """
    if http_client == "curl_cffi":
        resp = curl_requests.get(url, impersonate="chrome", timeout=15, allow_redirects=True)
    else:
        resp = requests.get(url, headers=HEADERS, timeout=15)

    real_url = resp.url or url

    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} 访问失败: {real_url}")

    full_text = trafilatura.extract(
        resp.content, output_format="markdown", include_links=True
    )
    if not full_text:
        raise RuntimeError(
            f"提取失败: {real_url}（页面无正文，可能是 JS 动态渲染页面或反爬，请用浏览器重新尝试打开）"
        )

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
        description="360 搜索 CLI：search 按关键词搜索网页；extract 阅读网页详细内容"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser("search", help="按关键词搜索，返回标题/链接/摘要/日期")
    p_search.add_argument("keyword", help="要搜索的关键词")
    p_search.add_argument(
        "--num", type=int, default=30,
        help="返回条数，1~50（默认 30；脚本自动翻页凑够）",
    )
    p_search.add_argument(
        "--client",
        choices=["requests", "curl_cffi"],
        default="curl_cffi",
        help="请求方式：curl_cffi（默认，模拟 Chrome 指纹）；个别环境不兼容时改用 requests",
    )

    p_extract = subparsers.add_parser("extract", help="抓取网页并提取正文内容")
    p_extract.add_argument("url", help="要阅读的网页 URL（可直接传 search 返回的 url）")
    p_extract.add_argument(
        "--max-chars", type=int, default=20000,
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
        num = min(max(args.num, 1), 50)
        try:
            results = search_360(args.keyword, num=num, http_client=args.client)
        except Exception as exc:
            sys.stderr.write(f"搜索失败: {exc}\n")
            sys.exit(1)
        payload = {
            "query": args.keyword,
            "total": len(results),
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        try:
            data = extract_url(args.url, max_chars=args.max_chars, http_client=args.client)
        except Exception as exc:
            sys.stderr.write(f"阅读失败: {exc}\n")
            sys.exit(1)
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
