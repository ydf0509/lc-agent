---
name: baidu-search
description: >-
  百度联网检索。search 按关键词搜索网页返回摘要/链接；extract 阅读指定网页提取正文。
  用户要搜索、查资料时用 search；要读某篇文章、看某个链接内容时用 extract或者用浏览器打开。
version: 1.1.0
---

# baidu-search

百度搜索 + 网页正文提取，两个命令按需选用：

- `search`：按关键词联网检索，返回标题/链接/摘要/时间。用户要"搜索""查一下""找文章"时使用。
- `extract`：抓取指定网页并提取正文，返回标题/正文/日期/作者。用户要"读一下这篇文章""看看这个链接"时使用。`search` 返回的 `url` 可直接传给 `extract`。

## 调用

通过 `skill__execute_script` 执行 `scripts/baidu_search_cli.py`。cwd 就是 skill 根目录，命令里写相对路径即可。

### search
**使用 search 联网搜索发现关键词相关的网页**

```json
{
  "skill_name": "baidu-search",
  "command": "python scripts/baidu_search_cli.py search 关键词 --num 30"
}
```

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词（位置参数） |
| `--num N` | 返回条数，1~50，默认 30 |
| `--client` | `curl_cffi`（默认，模拟 Chrome 指纹）或 `requests`。curl_cffi 不兼容时换 requests |

search 返回结果中的 results 的 url 就是需要调用 extract 提取url正文。如果某个result对你有用，你必须使用它的 url 来调用 extract。禁止完全只通过 search 的摘要就回答用户问题。

### extract
**使用extract提取指定url网页的正文内容**

```json
{
  "skill_name": "baidu-search",
  "command": "python scripts/baidu_search_cli.py extract https://example.com/article"
}
```

| 参数 | 说明 |
|------|------|
| `url` | 网页 URL（位置参数），可直接传 search 返回的result中的百度跳转链接url |
| `--max-chars N` | 正文最大字符数，默认 20000，传 0 不截断 |
| `--client` | 同 search |

#### ！！注意：
很多网站直接extract的http请求主url拿不到正文，例如有的是js动态渲染页面，
如果你当前有playwright的mcp工具或者使用agent-browser skill，你使用浏览器来打开url， 禁止每次使用完后你主动关闭浏览器，你不需要重启和关闭浏览器。

## 返回格式

stdout 输出 JSON，退出码 0 表示成功。

search 返回 `results` 数组，每条含 `title`/`url`/`abstract`/`date`/`site`/`is_advertisement`。`url` 是百度跳转链接（302 到目标页），需要真实 URL 或正文时对它调 `extract`。`site` 是来源站点（自然结果多数是真实域名如 `www.langchain.com`，少数是站点备案名如"腾讯云计算"；广告结果是广告主公司名）。`is_advertisement=true` 表示广告，应跳过。先读 `abstract` 和 `site` 判断相关性，只对确认需要的非广告链接调 `extract`。

extract 返回 `title`/`content`/`date`/`author`/`sitename`/`length`/`truncated`。`truncated=true` 表示正文已截断，需要更多内容时调大 `--max-chars` 重试。


## 出错应对

`search` 一次返回多条结果（默认 30 条），每条都带 `abstract`/`url`/`site`。先读 `abstract` 判断相关性，只对真正需要的那几条调 `extract`。
**某一条 `extract` 失败很正常，不要死磕单条 url** —— 先看 `site` 是否匹配 `references/` 里的站点策略（如知乎），命中就 `skill__read_content` 加载对应文档按其步骤抓；没命中就换 search 结果里下一条相关 url 继续。只有所有相关链接都失败时，才向用户说明并退回用 `abstract` 摘要回答。


需要区分的错误类型：

- **HTTP 4xx/5xx**（如"HTTP 403 访问失败: https://真实url"）：404/410 说明页面已失效，直接换下一条；403 如果这条 url 确实关键，可换 `--client requests` 重试一次，否则也换下一条。
- **提取失败**（"提取失败: https://真实url（页面无正文）"）：页面是 JS 动态渲染或强反爬站，换下一条相关 url。
- **知乎等强反爬站**：`site` 命中知乎时不要 `extract`（100% 返回 403），直接 `skill__read_content` 读 `references/zhihu-browser-access.md`，按其中的 playwright 步骤抓。
- **反爬拦截**（stderr 含"百度安全验证"）：这是全局拦截，换 url 也没用 —— 立即停止所有搜索/抓取，告知用户"搜索频率过高，稍后再试"。连续调用间隔 5 秒以上可预防。
- **依赖缺失**（ImportError）：告知用户安装对应包（`requests`/`beautifulsoup4`/`trafilatura`/`curl_cffi`）。

其他注意：

- `date` 字段百度不保证提供，缺失时如实说明，不编造发布时间。
- 广告结果已用 `is_advertisement=true` 标记（url 含 `baidu.php?url=`），优先采用 `is_advertisement=false` 的非广告来源。



## 关于 references 文件夹
把特定反扒或者http请求拿不到内容的网站的url，用户需要把相关提示词写到 references 文件夹下的对应文件中。 因为有些网站反扒，有些网站是需要ajax请求具体的接口拿到正文内容，所以很多网站直接 http协议去请求主url拿不到真正的详细正文内容。