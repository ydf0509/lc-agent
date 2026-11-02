# 360-search skill 的目的

和 `baidu-search`、`sogou-search`、`bing-search` 一样，这个 skill 是为了不依赖第三方联网搜索 mcp、
不购买搜索引擎 API key，自己通过 skill 脚本实现免费联网搜索（360 搜索）和 url 详情内容提取。

## 为什么选 360 搜索

2026-10 做本 skill 前的实测评估结论：

- **360 可免费稳定抓取**：`www.so.com/s` 返回标准 HTML，`li.res-list` 节点解析稳定，约 0.9s/次。
  结果节点的 `data-mdurl` 属性直接带真实 URL，不需要解析 `so.com/link` 跳转
  （跳转链接带签名校验，跨会话直接访问会返回 HTTP 400）。
- **翻页可用**：`pn=1/2/3` 返回不同结果；结果页底部有页码链接（`a[href*="pn="]`）。
- **限流敏感（重要）**：360 对高频访问的 IP 有两种惩罚形态——桌面站静默返回"无结果页"
  （`qcaptcha.so.com/noresult.html`），或跳转滑块验证码页（`qcaptcha.so.com/?ret=...`）。
  限制按 IP 生效，HTTP 通道短时间内无法恢复；在浏览器里手动过验证码只能解封该浏览器会话
  （cookie 绑定），不能解封脚本。因此脚本被拦时会输出明确提示，引导 agent 改用
  agent-browser 打开网页完成验证并在浏览器内读取/翻页/阅读（详见 SKILL.md 对应章节）。
- **需要过滤两类非自然结果**：短视频/影视等垂直模块（带 `data-mohe-type` 属性）和
  360 AI 摘要卡片（没有真实 URL），脚本已自动跳过，因此单页可用结果通常 3~7 条；
  结果条数少于 `--num` 属正常（exit 0），不是失败。
- 同期评估过的其它引擎大多不可用：Google（JS gate + IP 封）、DuckDuckGo html（202 反爬）、
  Mojeek（Captcha）、Brave 网页版（429）、Ecosia（403）、公共 SearXNG（连接超时）。

## 与其它搜索 skill 的分工

- 中文生活/国内信息 → `baidu-search`（首选）
- 微信公众号文章 → `sogou-search`
- 中文第三通道 / 交叉验证 → `360-search`
- 英文、国际、技术文档 → `bing-search`
- 重要问题多边交叉验证

## 实现要点

- 默认 `curl_cffi` 模拟 Chrome 指纹请求（个别环境不兼容可 `--client requests`）。
- `pn` 翻页 + URL 去重，`--num` 1~50（默认 30），最多翻 10 页；某页没有新结果即停止。
- 翻页间隔 0.5s；翻页途中被限流时返回已抓取的部分结果（不整单失败）。
- 被验证码/软限流拦截时，错误信息直接给出 `https://www.so.com/s?q=<关键词>` 和 agent-browser 处理指引。
- 浏览器过验证码的实测要点（已写入 SKILL.md）：`mouse move` 只接受整数坐标（小数报
  `Missing arguments`，且不能误判为语法错误）；拖动需 5~6 段、间隔 100~300ms；
  页面出现"网络或服务器异常"且 `img src=undefined` 时说明 IP 被加重限流，应停止而非继续重试。
- 滑块求解已固化为 `scripts/solve_slider.py`（识别缺口用模板匹配 + 自动分段拖动 + 失败重试），
  LLM 直接调用脚本即可，不要再临时写识别/拖动代码。实测新会话 12 秒通过验证。
- 浏览器内翻页**必须在页面内用 JS 点击页码**（`a.click()`，带 `psid` 的页码链接）。
  实测直接 `open "...&pn=2"` 会被静默打回第 1 页（final URL 里 pn 消失），
  `agent-browser click` 选择器点击也不跳转；只有 `a.click()` 有效。
  相邻页有重复结果，需按 URL 去重。
- 浏览器搜索已固化为 `scripts/browser_search.py`：自动打开搜索页、提取结果、点击翻页、
  跨页去重，输出与 `so360_search_cli.py search` 同构的 JSON。
  实测 5~6 页去重后 30 条，耗时约 1~1.5 分钟（页数越多越久）。
  退出码：0 成功；4 = 页面是验证码（先跑 solve_slider.py）；2 = 其他错误。
- HTTP 通道被限流后实测 20 分钟以上仍未恢复；浏览器会话可继续使用，
  但两者解封状态不共享（cookie/存储里都没有可用 token，5 种请求头组合实测均无效）。
- 摘要日期解析支持 ISO / 中文（2026年1月8日）/ 英文（Dec 29, 2025）/ 相对时间（1 天前 / 3 days ago）。
- extract 用 trafilatura 提取正文为 markdown，与其它搜索 skill 相同方案。
- 对特定反扒网站的抓取策略，按需在 `references/` 文件夹补充提示词文档（渐进式加载，不撑大主 skill）。
- 注意：爬虫型 skill 存在站点改版失效的风险，失效时改用 `baidu-search` / `sogou-search`。
