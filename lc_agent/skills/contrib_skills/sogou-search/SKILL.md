---
name: sogou-search
description: >-
  搜狗联网检索。search 按关键词搜索网页返回标题/链接/摘要/日期；extract 阅读指定网页提取正文。
  搜微信公众号文章、中文生活/国内信息时优先用本 skill；百度/必应结果不理想时也可换本 skill 交叉搜索。
  用户要搜索、查资料时用 search；要读某篇文章、看某个链接内容时用 extract。
version: 1.0.0
---

# sogou-search

搜狗搜索 + 网页正文提取，两个命令按需选用（免费，无需 API key）：

- `search`：按关键词联网检索，返回标题/链接/摘要/日期。用户要"搜索""查一下""找文章"时使用。
- `extract`：抓取指定网页并提取正文，返回标题/正文/日期/作者。用户要"读一下这篇文章""看看这个链接"时使用。`search` 返回的 `url` 可直接传给 `extract`。

与另外两个搜索 skill 的分工：微信公众号文章、腾讯系内容和中文口语化查询优先用本 skill；中文生活/国内信息用 baidu-search；英文、国际、技术文档用 bing-search；重要问题多边交叉验证。

## 调用

通过 `skill__execute_script` 执行 `scripts/sogou_search_cli.py`。cwd 就是 skill 根目录，命令里写相对路径即可。

### search
**使用 search 联网搜索发现关键词相关的网页，返回网址和内容摘要**

```shell
python scripts/sogou_search_cli.py search "关键词" --num 20
# search 后面的关键词要使用引号包裹起来，这可以避免命令行参数个数识别错误
```

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词（位置参数） |
| `--num N` | 返回条数，1~50，默认 10（每页 10 条，脚本自动翻页凑够条数） |
| `--client` | `curl_cffi`（默认，模拟 Chrome 指纹）或 `requests`。curl_cffi 不兼容时换 requests |

search 返回的 results 里的 `url` 已经是真实网页地址，可直接传给 extract。如果某个 result 对你有用，你必须使用它的 `url` 来调用 extract。禁止完全只通过 search 的摘要就回答用户问题。

### extract
**使用 extract 提取指定 url 网页的正文内容**

```json
python scripts/sogou_search_cli.py extract "https://example.com/article"

```

| 参数 | 说明 |
|------|------|
| `url` | 网页 URL（位置参数），可直接传 search 返回的 `url`，也兼容搜狗 `/link?url=` 跳转链接 |
| `--max-chars N` | 正文最大字符数，默认 20000，传 0 不截断 |
| `--client` | 同 search |

#### ！！注意：
很多网站直接 extract 的 http 请求主 url 拿不到正文，例如有的是 js 动态渲染页面，
如果你当前安装了 agent-browser skill，使用 agent-browser skill 来打开 url， 禁止每次使用完后主动关闭有头浏览器，你不需要重启和关闭它。

## 返回格式

stdout 输出 JSON，退出码 0 表示成功。

search 返回 `results` 数组，每条含 `title`/`url`/`abstract`/`date`/`site`/`is_advertisement`。`url` 是真实网页地址（取自搜狗结果节点的 data-url，已绕开 JS 跳转），可直接传给 `extract`。`date` 是搜狗展示的发布日期（YYYY-MM-DD），不是每条都有，缺失时如实说明，不编造发布时间。`site` 是真实 URL 的域名（取不到时退回搜狗展示的站点名）。`is_advertisement=true` 表示广告，应跳过。先读 `abstract` 和 `site` 判断相关性，只对确认需要的非广告链接调 `extract`。

extract 返回 `title`/`content`/`date`/`author`/`sitename`/`length`/`truncated`。`truncated=true` 表示正文已截断，需要更多内容时调大 `--max-chars` 重试。

## 出错应对

`search` 一次可返回多条结果（默认 10 条，最多 50 条），先读 `abstract` 判断相关性，只对真正需要的那几条调 `extract`。
**某一条 `extract` 失败很正常，不要死磕单条 url** —— 换 search 结果里下一条相关 url 继续。只有所有相关链接都失败时，才向用户说明并退回用 `abstract` 摘要回答。

需要区分的错误类型：

- **真实无结果**（`total=0`）：换更具体或更通用的关键词重试；中文内容换 `baidu-search`、技术文档换 `bing-search` 再试。
- **HTTP 4xx/5xx**（如"HTTP 403 访问失败: https://真实url"）：404/410 说明页面已失效，直接换下一条；403 如果这条 url 确实关键，可换 `--client requests` 重试一次，否则也换下一条。
- **提取失败**（"提取失败: https://真实url（页面无正文）"）：页面是 JS 动态渲染或强反爬站，换下一条相关 url，或用 agent-browser skill 打开。
- **反爬拦截**（stderr 含"触发搜狗反爬拦截"）：这是全局拦截，换 url 也没用 —— 立即停止所有搜索/抓取，告知用户"搜索频率过高，稍后再试"。连续调用间隔 2 秒以上可预防。
- **依赖缺失**（ImportError）：告知用户安装对应包（`requests`/`beautifulsoup4`/`trafilatura`/`curl_cffi`）。

其他注意：

- 搜狗单页最多 10 条，脚本按 `page` 自动翻页，`--num` 上限 50；页数越多越容易触发反爬，日常用 10~20 条即可。
- 搜索结果里的日期是搜狗索引展示值，可能不准（例如把栏目更新日期当成文章发布时间），关键时间信息要用 `extract` 后的 `date` 或正文核对。
- 微信公众号文章用搜狗命中率高于百度/必应，但正文抓取仍可能被拦截，失败时用 agent-browser skill 打开。

## 关于 references 文件夹
把特定反扒或者 http 请求拿不到内容的网站的 url，用户需要把相关提示词写到 references 文件夹下的对应文件中。 因为有些网站反扒，有些网站是需要 ajax 请求具体的接口拿到正文内容，所以很多网站直接 http 协议去请求主 url 拿不到真正的详细正文内容。
