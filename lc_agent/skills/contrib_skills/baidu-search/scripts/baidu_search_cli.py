#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度搜索 CLI — 按关键词搜索网页 + 阅读网页详细内容。

用法示例:
    baidu_search_cli.py search "python 爬虫"
    baidu_search_cli.py search "langchain" --num 30
    baidu_search_cli.py extract "https://example.com/article"
    baidu_search_cli.py extract "https://example.com/article" --max-chars 5000

依赖: requests, beautifulsoup4, trafilatura, curl_cffi
      (pip install requests beautifulsoup4 trafilatura curl_cffi)

输出: JSON 到 stdout。退出码: 0=成功, 1=操作失败或被反爬拦截。
"""
import argparse
import json
import re
import sys
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.baidu.com/",
}

# 摘要节点选择器（百度前端 class 会变化，多备几个）
ABSTRACT_SELECTORS = (
    "span.content-right_8Zs40",
    "div.c-abstract",
    "span.c-abstract",
    "div[class*=content-right]",
    "span[class*=content-right]",
    "div.c-span-last",
)

# 站点/来源选择器：自然结果是真实域名，广告结果是广告主公司名
SITE_SELECTORS = (
    "div.cosc-source",
    "a.cosc-source-link",
    "span.cosc-source-text",
    "div[class*=source-pc]",
    "span.ec-showurl-line",
    "a.c-showurl",
)

# 发布日期选择器：百度把发布时间放在专门的 prefix-time 节点，不是正文里
TIME_SELECTORS = (
    "span[class*=prefix-time]",
)


def search_baidu(keyword: str, num: int = 30, http_client: str = "curl_cffi") -> list[dict]:
    """按关键词搜索百度，返回每条结果的 title / url / abstract / date。

    http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
        个别站点对 curl_cffi 不兼容（如证书、HTTP/2 异常）时可改用 "requests"。
    """
    if http_client == "curl_cffi":
        session = curl_requests.Session(impersonate="chrome")
    else:
        session = requests.Session()
    session.headers.update(HEADERS)
    # 先访问首页拿必要 cookie，降低被拦概率
    session.get("https://www.baidu.com/", timeout=10)

    resp = session.get(
        "https://www.baidu.com/s", params={"wd": keyword, "rn": num}, timeout=10
    )
    resp.raise_for_status()
    # 百度页面（含验证码页）均为 UTF-8；响应头缺失 charset 时 requests 默认
    # ISO-8859-1 会导致中文乱码，必须强制 utf-8
    resp.encoding = "utf-8"
    html = resp.text

    # 反爬判定：优先查重定向 URL（wappass 验证码页），再查页面内容
    if ("wappass.baidu.com" in resp.url) or ("百度安全验证" in html) or ("通过验证码" in html):
        raise RuntimeError("触发百度安全验证，被反爬拦截。请降低调用频率（建议间隔 5 秒以上）后重试")

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for div in soup.select("div.result, div.result-op, div.c-container"):
        h3 = div.find("h3")
        if not h3:
            continue
        a = h3.find("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        # 百度部分卡片（如视频聚合）的 href 是相对路径（/sf/vsearch?...），补全为绝对 URL
        url = urljoin("https://www.baidu.com/", a.get("href", ""))

        # 摘要
        abstract = ""
        for sel in ABSTRACT_SELECTORS:
            node = div.select_one(sel)
            if node:
                abstract = node.get_text(" ", strip=True)
                break
        if not abstract:  # 兜底：容器全文去掉标题
            abstract = div.get_text(" ", strip=True).replace(title, "", 1).strip()

        # 时间：优先从百度专门的 prefix-time 节点取发布日期（稳定，是真正的发布时间，
        # 不会抓到正文里的非发布日期）；没有该节点再退回从摘要里正则兜底
        date = ""
        date_text = ""
        for sel in TIME_SELECTORS:
            node = div.select_one(sel)
            if node:
                date_text = node.get_text(" ", strip=True)
                break
        if not date_text:
            date_text = abstract or ""
        m = re.search(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})", date_text)
        if m:
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # 站点：自然结果是真实域名（百度显示时常截断成 "www.langchain.com/stateo..."），
        # 广告结果是广告主公司名（ec-showurl-line 较干净，c-showurl 混了日期+"广告"）
        site_raw = ""
        for sel in SITE_SELECTORS:
            node = div.select_one(sel)
            if node:
                site_raw = node.get_text(" ", strip=True)
                break
        is_advertisement = ("baidu.php?url=" in url) or ("广告" in site_raw)
        site = site_raw
        if is_advertisement:
            site = re.sub(r"\d{4}[-年].*$", "", site_raw.replace("广告", "")).strip()
        elif "/" in site and not site.startswith("http"):
            site = site.split("/")[0].strip()
        if not site:
            site = urlparse(url).netloc  # 站点名取不到时用真实域名兜底

        item = {
            "title": title,
            "url": url,
            "abstract": abstract,
            "date": date,
            "site": site,
            "is_advertisement": is_advertisement,
        }
        results.append(item)
        if len(results) >= num:
            break
    return results


def extract_url(url: str, max_chars: int = 20000, http_client: str = "curl_cffi") -> dict:
    """抓取网页并提取正文内容，返回 title / content / date / author / sitename。

    Args:
        url: 要阅读的网页 URL。
        max_chars: 正文最多返回的字符数，超出截断；传 0 表示不截断。
        http_client: 请求方式。"curl_cffi"（默认，模拟 Chrome 浏览器指纹）；
            个别站点对 curl_cffi 不兼容（如证书、HTTP/2 异常）时改用 "requests"。
    """
    # 传百度跳转链接时，这里会自动跟随 302 到目标页；传普通 URL 时保持原样
    if http_client == "curl_cffi":
        resp = curl_requests.get(url, impersonate="chrome", timeout=15, allow_redirects=True)
    else:
        resp = requests.get(url, headers=HEADERS, timeout=15)

    # 跟随重定向后的真实地址（传入百度跳转链接时即为目标网页）
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
        description="百度搜索 CLI：search 按关键词搜索网页；extract 阅读网页详细内容"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search 子命令
    p_search = subparsers.add_parser("search", help="按关键词搜索，返回标题/链接/摘要/时间")
    p_search.add_argument("keyword", help="要搜索的关键词")
    p_search.add_argument("--num", type=int, default=30, help="返回条数，最大 50（默认 30）")
    p_search.add_argument(
        "--client",
        choices=["requests", "curl_cffi"],
        default="curl_cffi",
        help="请求方式：curl_cffi（默认，模拟 Chrome 指纹）；个别站点不兼容时改用 requests",
    )

    # extract 子命令
    p_extract = subparsers.add_parser("extract", help="抓取网页并提取正文内容")
    p_extract.add_argument("url", help="要阅读的网页 URL（可直接传 search 返回的百度跳转链接）")
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
        num = min(max(args.num, 1), 50)
        try:
            results = search_baidu(args.keyword, num=num, http_client=args.client)
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
