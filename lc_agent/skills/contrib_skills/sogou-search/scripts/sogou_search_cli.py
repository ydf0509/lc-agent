#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜狗搜索 CLI — 按关键词搜索网页 + 阅读网页详细内容（免费，无需 API key）。

用法示例:
    sogou_search_cli.py search "python 爬虫"
    sogou_search_cli.py search "微信 公众号 文章" --num 20
    sogou_search_cli.py extract "https://example.com/article"
    sogou_search_cli.py extract "https://example.com/article" --max-chars 5000

依赖: requests, beautifulsoup4, trafilatura, curl_cffi
      (pip install requests beautifulsoup4 trafilatura curl_cffi)

输出: JSON 到 stdout。退出码: 0=成功, 1=操作失败或被反爬拦截。

说明:
- search 结果页每页 10 条，本脚本按 page 参数自动翻页凑够 --num 条，上限 50 条。
- 搜索结果里的真实 URL 优先取自 r-sech 节点的 data-url 属性（搜狗跳转链接是
  JS 跳转，不能靠 HTTP 302 跟随）；没有 data-url 时才退回 /link?url= 链接，
  extract 会先解析 JS 跳转拿到真实地址。
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

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
    "Referer": "https://www.sogou.com/",
}

SEARCH_URL = "https://www.sogou.com/web"
# 搜狗结果页固定 10 条/页，num 参数不生效，只能靠 page 参数翻页
PAGE_SIZE = 10
MAX_NUM = 50
# 翻页间隔，降低触发反爬的概率
PAGE_DELAY = 1.0

# 英文月份 -> 数字
EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(text: str) -> str:
    """从文本解析发布日期，支持绝对日期和相对时间（中英文）。

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

    # 英文: Dec 29, 2025
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

    # 相对时间（英文）: 3 days ago
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


def _fetch_search_page(session, keyword: str, page: int) -> str:
    """请求第 page 页搜索结果，返回 HTML 文本。被拦截时抛 RuntimeError。"""
    resp = session.get(
        SEARCH_URL, params={"query": keyword, "page": page}, timeout=10
    )
    resp.raise_for_status()
    # 搜狗页面为 UTF-8；响应头缺失 charset 时 requests 默认 ISO-8859-1 会乱码
    resp.encoding = "utf-8"
    html = resp.text
    # 反爬判定：跳转 antispider 验证页或页面出现验证提示
    if ("antispider" in resp.url) or ("请输入验证码" in html) or ("网络中存在异常访问请求" in html):
        raise RuntimeError("触发搜狗反爬拦截。请降低调用频率（建议间隔 2 秒以上）后重试")
    return html


def _resolve_result_url(block, href: str) -> str:
    """还原结果真实 URL。

    搜狗标题链接是 /link?url=... 的 JS 跳转页；结果块内 r-sech 节点的
    data-url 属性直接带真实地址，优先使用。标题链接本身是绝对地址时
    （例如公众号文章）以标题链接为准。
    """
    if href and not href.startswith("/link"):
        return urljoin("https://www.sogou.com", href)
    node = block.select_one("[data-url]")
    data_url = (node.get("data-url") or "").strip() if node else ""
    if data_url.startswith("http"):
        return data_url
    return urljoin("https://www.sogou.com", href)


def _parse_results(html: str) -> list[dict]:
    """解析单页 HTML，返回结果列表（最多 10 条）。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for block in soup.select("div.vrwrap"):
        h3 = block.find("h3")
        a = h3.find("a") if h3 else None
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        url = _resolve_result_url(block, a.get("href", ""))

        # 摘要：fz-mid 是纯摘要节点；部分卡片式结果没有，退回 text-layout 并去掉引用信息
        abstract = ""
        node = block.select_one("div.fz-mid")
        cite = block.select_one("a.citeLinkClass")
        if node:
            abstract = node.get_text(" ", strip=True)
        else:
            node = block.select_one("div.text-layout")
            if node:
                abstract = node.get_text(" ", strip=True)
        if cite and abstract:
            cite_text = cite.get_text(" ", strip=True)
            if cite_text:
                abstract = abstract.replace(cite_text, "", 1).strip()

        # 引用信息：span 依次是站点名、展示 URL、日期
        site = ""
        date = ""
        cite_text = cite.get_text(" ", strip=True) if cite else ""
        if cite:
            spans = [s.get_text(" ", strip=True) for s in cite.find_all("span")]
            spans = [s for s in spans if s]
            if spans:
                site = spans[0]
            date = parse_date(" ".join(spans)) or parse_date(cite_text)
        if not date:
            date = parse_date(abstract[:80])

        # 站点优先用真实 URL 的域名，和 bing-search 保持一致
        netloc = urlparse(url).netloc if url.startswith("http") else ""
        if netloc:
            site = netloc

        is_advertisement = (
            "广告" in cite_text
            or block.select_one(".ico-ads") is not None
        )

        results.append({
            "title": title,
            "url": url,
            "abstract": abstract,
            "date": date,
            "site": site,
            "is_advertisement": is_advertisement,
        })
    return results


def search_sogou(keyword: str, num: int = 10, http_client: str = "curl_cffi") -> list[dict]:
    """按关键词搜索搜狗，自动翻页返回最多 num 条结果。

    num: 返回条数，1~50（每页 10 条，脚本内部按 page 翻页）。
    http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
        个别环境对 curl_cffi 不兼容时可改用 "requests"。
    """
    session = _build_session(http_client)
    collected: list[dict] = []
    seen: set[str] = set()
    max_pages = (num + PAGE_SIZE - 1) // PAGE_SIZE

    for page in range(1, max_pages + 1):
        html = _fetch_search_page(session, keyword, page)
        page_results = _parse_results(html)
        if not page_results:
            break

        added = 0
        for item in page_results:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            collected.append(item)
            added += 1
            if len(collected) >= num:
                break

        # 整页都是重复结果，说明已经翻到底了
        if added == 0:
            break
        if len(collected) < num and page < max_pages:
            time.sleep(PAGE_DELAY)

    return collected[:num]


def _resolve_sogou_link(url: str) -> str:
    """解析 sogou.com/link?url=... 的 JS 跳转页，返回真实 URL。

    非搜狗跳转链接原样返回；解析失败也原样返回（后续抓取会失败并报错）。
    """
    if "/link?" not in url or "sogou.com" not in urlparse(url).netloc:
        return url
    try:
        resp = curl_requests.get(url, impersonate="chrome", timeout=10, allow_redirects=True)
        resp.encoding = "utf-8"
        m = re.search(r'window\.location\.replace\(\s*["\']([^"\']+)["\']', resp.text)
        if m:
            target = m.group(1)
            return target.replace("\\/", "/")
    except Exception:
        pass
    return url


def extract_url(url: str, max_chars: int = 20000, http_client: str = "curl_cffi") -> dict:
    """抓取网页并提取正文内容，返回 title / content / date / author / sitename。

    Args:
        url: 要阅读的网页 URL。传搜狗 /link?url= 跳转链接时会先解析成真实 URL。
        max_chars: 正文最多返回的字符数，超出截断；传 0 表示不截断。
        http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
            个别站点对 curl_cffi 不兼容（如证书、HTTP/2 异常）时改用 "requests"。
    """
    url = _resolve_sogou_link(urljoin("https://www.sogou.com", url))

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

    # 元数据：extract_metadata() 返回 Document 对象
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
        description="搜狗搜索 CLI：search 按关键词搜索网页；extract 阅读网页详细内容"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search 子命令
    p_search = subparsers.add_parser("search", help="按关键词搜索，返回标题/链接/摘要/日期")
    p_search.add_argument("keyword", help="要搜索的关键词")
    p_search.add_argument(
        "--num", type=int, default=10,
        help="返回条数，1~50（默认 10；每页 10 条，脚本自动翻页）",
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
        num = min(max(args.num, 1), MAX_NUM)
        try:
            results = search_sogou(args.keyword, num=num, http_client=args.client)
        except Exception as exc:
            sys.stderr.write(f"搜索失败: {exc}\n")
            sys.exit(1)
        payload = {"query": args.keyword, "total": len(results), "results": results}
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
