# sogou-search skill 的目的

和 `baidu-search`、`bing-search` 一样，这个 skill 不依赖第三方联网搜索 mcp、不购买搜索引擎 API key，
用 skill 脚本直接抓搜狗搜索结果页，实现免费联网搜索和 url 详情内容提取。

## 为什么再补一个搜狗

- **公众号/微信文章覆盖好**：搜狗的网页结果里会直接混入公众号文章（cite 显示"公众号"），
  这是百度和必应都覆盖较差的中文内容来源。
- **中文口语化查询召回不同**：同一个问题，搜狗和百度的排序、收录站点差异明显，
  作为第三个免费来源可以交叉验证，避免单一引擎的收录偏差。
- **零配置**：`www.sogou.com/web` 直连返回标准 HTML，不需要 cookie、不需要 API key。

## 实测到的结构（写脚本时验证过）

- 结果容器是 `div.vrwrap`，标题在 `h3` 的 `a` 节点，摘要主要在 `div.fz-mid`，
  引用信息在 `a.citeLinkClass`，其 span 依次是站点名、展示 URL、日期。
- 标题的 `href` 是 `/link?url=...` 的 JS 跳转页，HTTP 请求只能拿到一段
  `window.location.replace("真实URL")` 的脚本，不能靠 302 跟随。好在该结果块的
  `div.r-sech` 带 `data-url` 属性，直接就是真实 URL，脚本优先取它。
- 每页固定 10 条，`num` 参数不生效；`page` 参数可以稳定翻页（实测到第 20 页仍有结果）。
  脚本按 `--num` 自动翻页，上限 50 条。
- 翻页间隔设为 1 秒，连续调用建议间隔 2 秒以上；触发反爬时页面会跳到 `antispider`
  验证页或出现"请输入验证码"，脚本会直接报错而不是返回脏数据。

## 实现要点

- 默认 `curl_cffi` 模拟 Chrome 指纹请求（个别环境不兼容可 `--client requests`）。
- search 自动翻页、去重，`--num` 上限 50；整页结果都重复时提前停止。
- `extract` 用 trafilatura 提取正文为 markdown，与另外两个搜索 skill 相同方案；
  传入 `/link?url=` 链接时会先解析 JS 跳转拿真实地址。
- 对特定反扒网站的抓取策略，按需在 `references/` 文件夹补充提示词文档（渐进式加载，不撑大主 skill）。
