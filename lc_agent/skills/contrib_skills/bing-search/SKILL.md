---
name: bing-search
description: >-
  必应 Bing 联网检索。search 按关键词搜索网页返回标题/链接/摘要/日期；extract 阅读指定网页提取正文。
  搜英文、国际、技术文档资料时优先用本 skill；百度搜索结果不理想时也可换本 skill 交叉搜索。
  用户要搜索、查资料、找英文文献/官方文档时用 search；要读某篇文章、看某个链接内容时用 extract。
version: 1.0.0
---

# bing-search

必应搜索 + 网页正文提取，两个命令按需选用（免费，无需 API key）：

- `search`：按关键词联网检索，返回标题/链接/摘要/日期（单次最多 10 条）。用户要"搜索""查一下""找文档"时使用。搜英文、国际内容优先用它。
- `extract`：抓取指定网页并提取正文，返回标题/正文/日期/作者。用户要"读一下这篇文章""看看这个链接"时使用。`search` 返回的 `url` 可直接传给 `extract`。

与 `baidu-search` 的分工：中文生活/国内信息用 baidu-search；英文、国际、技术文档用本 skill；重要问题两边交叉验证。

## 调用

通过 `skill__execute_script` 执行 `scripts/bing_search_cli.py`。cwd 就是 skill 根目录，命令里写相对路径即可。

### search
**使用 search 联网搜索发现关键词相关的网页，结果返回网址和内容摘要**

```shell
python scripts/bing_search_cli.py search "关键词"
# search 后面的关键词要使用引号包裹起来，这可以避免命令行参数个数识别错误
```

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词（位置参数） |
| `--num N` | 返回条数，1~10，默认 10（必应单页上限 10 条，传更大值也只返回 10 条） |
| `--mkt` | `auto`（默认，按关键词语言自动选国内版/国际版，国内版无结果自动回退国际版）；`zh-CN` 强制国内版；`en-US` 强制国际版 |
| `--client` | `curl_cffi`（默认，模拟 Chrome 指纹）或 `requests`。curl_cffi 不兼容时换 requests |

search 返回结果中的 results 的 url 就是需要调用 extract 提取正文的真实地址（国际版结果的 bing 跳转链接已自动解码还原）。如果某个 result 对你有用，你必须使用它的 url 来调用 extract。禁止完全只通过 search 的摘要就回答用户问题。

### extract
**使用extract提取指定url网页的正文内容**

```json
python scripts/bing_search_cli.py extract "https://example.com/article"

```

| 参数 | 说明 |
|------|------|
| `url` | 网页 URL（位置参数），可直接传 search 返回的 url |
| `--max-chars N` | 正文最大字符数，默认 20000，传 0 不截断 |
| `--client` | 同 search |

#### ！！注意：
很多网站直接 extract 的 http 请求主 url 拿不到正文，例如有的是 js 动态渲染页面，
如果你当前安装了 agent-browser skill，使用 agent-browser skill 来打开 url， 禁止每次使用完后主动关闭有头浏览器，你不需要重启和关闭它。

## 返回格式

stdout 输出 JSON，退出码 0 表示成功。

search 返回 `results` 数组，每条含 `title`/`url`/`abstract`/`date`/`site`/`is_advertisement`，顶层额外有 `mkt` 字段表示实际使用的市场（`zh-CN` 国内版 / `en-US` 国际版）。`url` 已解码为真实网页地址，可直接传给 `extract`。`date` 是从摘要解析的发布日期（YYYY-MM-DD），必应不保证每条都有，缺失时如实说明，不编造发布时间。`is_advertisement=true` 表示广告，应跳过。先读 `abstract` 和 `site` 判断相关性，只对确认需要的非广告链接调 `extract`。

extract 返回 `title`/`content`/`date`/`author`/`sitename`/`length`/`truncated`。`truncated=true` 表示正文已截断，需要更多内容时调大 `--max-chars` 重试。

## 出错应对

`search` 一次最多返回 10 条（必应单页上限），先读 `abstract` 判断相关性，只对真正需要的那几条调 `extract`。
**某一条 `extract` 失败很正常，不要死磕单条 url** —— 换 search 结果里下一条相关 url 继续。只有所有相关链接都失败时，才向用户说明并退回用 `abstract` 摘要回答。

需要区分的错误类型：

- **结果与关键词明显无关**（如搜 python 返回购物/新闻等不相关页面）：这是 Bing 对数据中心出口 IP 的降级投喂（实测真浏览器同样如此），不是脚本 bug。不要采信这些结果 —— 换一个包含明确品牌词/产品名的关键词重试（如 `fastapi websocket tutorial` 这类"品牌词+具体需求"的查询召回明显更好），中文内容换 `baidu-search` 交叉验证。
- **真实无结果**（`total=0`）：auto 模式已自动在国内外两个市场都试过。换更具体或更通用的关键词重试；中文内容换 `baidu-search` 再试。
- **HTTP 4xx/5xx**（如"HTTP 403 访问失败: https://真实url"）：404/410 说明页面已失效，直接换下一条；403 如果这条 url 确实关键，可换 `--client requests` 重试一次，否则也换下一条。
- **提取失败**（"提取失败: https://真实url（页面无正文）"）：页面是 JS 动态渲染或强反爬站，换下一条相关 url。
- **反爬拦截**（stderr 含"触发必应反爬拦截"）：这是全局拦截，换 url 也没用 —— 立即停止所有搜索/抓取，告知用户"搜索频率过高，稍后再试"。连续调用间隔 2 秒以上可预防。
- **依赖缺失**（ImportError）：告知用户安装对应包（`requests`/`beautifulsoup4`/`trafilatura`/`curl_cffi`）。

其他注意：

- 单次搜索最多 10 条，且不支持翻页。需要更多候选结果时，换几个不同角度/更具体的关键词分别搜索，不要重复同一个关键词。
- 搜英文资料时关键词直接用英文，召回质量更好。
- 广告结果已用 `is_advertisement=true` 标记，优先采用 `is_advertisement=false` 的非广告来源。

## 关于 references 文件夹
把特定反扒或者 http 请求拿不到内容的网站的 url，用户需要把相关提示词写到 references 文件夹下的对应文件中。 因为有些网站反扒，有些网站是需要 ajax 请求具体的接口拿到正文内容，所以很多网站直接 http 协议去请求主 url 拿不到真正的详细正文内容。
