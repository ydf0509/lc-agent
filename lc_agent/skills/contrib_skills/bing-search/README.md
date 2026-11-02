# bing-search skill 的目的

和 `baidu-search` 一样，这个 skill 是为了不依赖第三方联网搜索 mcp、不购买搜索引擎 API key，
自己通过 skill 脚本实现免费联网搜索（必应）和 url 详情内容提取。

## 为什么选必应（Bing）

2025 年做本 skill 前的实测评估结论：

- **必应可免费稳定抓取**：`www.bing.com/search` 直连返回标准 HTML，`li.b_algo` 节点解析稳定，
  连续快速请求无频率限制（建议间隔 2 秒）。国内版（mkt=zh-CN）直接给真实 URL；
  国际版（mkt=en-US）给 `bing.com/ck/a` 跳转链接，其 `u=a1<base64url>` 参数可直接 base64
  解码还原真实 URL（本脚本已内置解码）。
- **必应单页固定上限 10 条，翻页不可用**（实测堵死）：`first` 参数（11/21、10/20 两种偏移写法）、
  官方"下一页"链接（带 FPIG token）、带 cookie 的同一 Session、`format=rss`、
  primp 浏览器指纹客户端——全都只能拿到第一页的同一批结果。因此本 skill 只做单页抓取，
  `--num` 上限 10；需要更多候选时由 agent 换多个不同关键词分别搜索。
- **不引入 ddgs 等第三方搜索库**：曾评估用 ddgs 的 Bing 索引镜像（duckduckgo html / yahoo）
  翻页补足 30 条，实测镜像反爬间歇性失效（DDG 202 挑战、Yahoo "temporary problems"），
  不可靠，最终决定只用原生必应，保持零第三方搜索依赖。
- **Google 免费爬取不可行**（三条路全部实测堵死）：
  1. 纯 HTTP（含 gbv/udm14/curl_cffi 指纹等所有变体）只返回 JS 渲染跳转壳页（Google 2025 年起对无 Cookie 请求强制 JS 渲染）；
  2. `ddgs` 库 google 后端返回 No results found；
  3. headless 浏览器（系统 Chrome）被 Google 重定向到 `/sorry/` 验证码页（出口 IP 级封锁）。
  Google 唯一可靠途径是官方 Custom Search JSON API（免费 100 次/天，但需注册 API key），不符合本 skill 零配置定位。
- 微软官方 Bing Search API 也已于 2025-08-11 退役，免费抓取网页是必应唯一的免费途径。

## 与 baidu-search 的分工

- 中文生活/国内信息 → `baidu-search`
- 英文、国际、技术文档 → `bing-search`
- 重要问题两边交叉验证

## 实现要点

- 默认 `curl_cffi` 模拟 Chrome 指纹请求（个别环境不兼容可 `--client requests`）。
- 单页抓取，`--num` 上限 10 条，不做翻页（原因见上）。
- search 自动按关键词语言选市场（中文→国内版，其他→国际版），国内版无结果自动回退国际版
  （必应国内版对部分查询会返回"没有与此相关的结果"，实测 `langchain 是什么` 即如此）。
- **结果质量依赖网络出口 IP**（2026-10 实测重要发现）：本机全局 TUN 代理把所有流量送出
  阿里云美国机房 IP（149.129.226.181），Bing 对数据中心 IP 降级服务——随机投喂其他查询的
  缓存页（WhatsApp/购物站/新闻）或导航类泛结果，**真实 Chrome 自然搜索同样如此**，非脚本
  问题。品牌词强的查询（fastapi/langchain + 具体需求）召回正常。缓解：TUN 配置给
  `bing.com` 加直连规则（国内可直连必应，直连后用真实宽带 IP 质量正常）；agent 侧已写
  入 SKILL.md 的识别与重试策略。
- 摘要日期解析支持 ISO / 中文（2026年1月8日）/ 英文（Dec 29, 2025）/ 相对时间（1 天前 / 3 days ago）。
- extract 用 trafilatura 提取正文为 markdown，与 baidu-search 相同方案；传入 `bing.com/ck/a`
  链接会先解码再抓取。
- 对特定反扒网站的抓取策略，按需在 `references/` 文件夹补充提示词文档（渐进式加载，不撑大主 skill）。
