---
name: 360-search
description: >-
  360 搜索联网检索。search 按关键词搜索网页返回标题/链接/摘要/日期；extract 阅读指定网页提取正文。
  中文综合检索的补充来源：百度结果不理想、或需要第三家中文引擎交叉验证时使用。
  HTTP 通道被限流/验证码拦截时，按文档引导改用 agent-browser 浏览器通道（脚本自动过滑块验证码、点击翻页）。
  用户要搜索、查资料、找中文文章时用 search；要读某篇文章、看某个链接内容时用 extract。
version: 1.0.0
---

# 360-search

360 搜索 + 网页正文提取，两个命令按需选用（免费，无需 API key）：

- `search`：按关键词联网检索，返回标题/链接/摘要/日期。用户要"搜索""查一下""找文章"时使用。
- `extract`：抓取指定网页并提取正文，返回标题/正文/日期/作者。用户要"读一下这篇文章""看看这个链接"时使用。`search` 返回的 `url` 可直接传给 `extract`。

与其它搜索 skill 的分工：中文生活/国内信息首选 `baidu-search`；微信公众号文章用 `sogou-search`；英文/国际/技术文档用 `bing-search`；本 skill 作为中文第三条检索通道，用于交叉验证或前两者结果不理想时。

## 调用

通过 `skill__execute_script` 执行 `scripts/` 下的脚本。cwd 就是 skill 根目录，命令里写相对路径即可。

**脚本清单**：

| 脚本 | 用途 |
|------|------|
| `scripts/so360_search_cli.py` | HTTP 通道：`search` 搜索 + `extract` 正文提取 |
| `scripts/solve_slider.py` | 浏览器通道：自动过 360 滑块验证码 |
| `scripts/browser_search.py` | 浏览器通道：浏览器内搜索、点击翻页、去重（HTTP 被限流时用） |

**环境与依赖**：Python 3.10+，依赖 `curl_cffi`、`requests`、`beautifulsoup4`、`trafilatura`、`pillow`（solve_slider 用）。
多 Python 环境的机器上，把命令里的 `python` 换成实际解释器路径（如 `D:\ProgramData\Miniconda3\envs\py312\python.exe`），
跑错环境会报 `ModuleNotFoundError`（处理见"出错应对"）。

### search
**使用 search 联网搜索发现关键词相关的网页**

```shell
python scripts/so360_search_cli.py search "关键词" --num 30
# search 后面的关键词要使用引号包裹起来，这可以避免命令行参数个数识别错误
```

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词（位置参数） |
| `--num N` | 返回条数，1~50，默认 30（脚本按 `pn` 自动翻页凑够，需要更多直接传大值） |
| `--client` | `curl_cffi`（默认，模拟 Chrome 指纹）或 `requests`。curl_cffi 不兼容时换 requests |

search 返回结果中的 `url` 已经是真实网页地址（取自结果节点的 `data-mdurl`），可直接传给 extract。如果某个 result 对你有用，你必须使用它的 url 来调用 extract。禁止完全只通过 search 的摘要就回答用户问题。

### extract
**使用 extract 提取指定 url 网页的正文内容**

```shell
python scripts/so360_search_cli.py extract "https://example.com/article"

```

| 参数 | 说明 |
|------|------|
| `url` | 网页 URL（位置参数），可直接传 search 返回的 url |
| `--max-chars N` | 正文最大字符数，默认 20000，传 0 不截断 |
| `--client` | 同 search |

#### ！！注意：
很多网站直接 extract 的 http 请求主 url 拿不到正文，例如有的是 js 动态渲染页面，
如果你当前安装了 agent-browser skill，使用 agent-browser skill 来打开 url，禁止使用完后主动关闭有头浏览器，你不需要重启和关闭它。

## 返回格式

stdout 输出 JSON，退出码 0 表示成功。

search 返回 `results` 数组，每条含 `title`/`url`/`abstract`/`date`/`site`/`is_advertisement`。`url` 是真实网页地址，可直接传给 `extract`。`abstract` 是 360 服务端给出的 SERP 摘要原文（通常 100~130 字符，末尾可能自带 `...`/`…`，这是搜索引擎的截取展示，不是脚本截断），只用于判断相关性，要读完整内容必须调 `extract`。`date` 是从摘要开头解析的发布日期（YYYY-MM-DD），360 不保证每条都有，缺失时如实说明，不编造发布时间；
且该日期取自 SERP 摘要文本，可能是文中提及的时间而非发布时间，**仅作参考，不要当成权威发布日期**。`is_advertisement=true` 表示广告，应跳过。先读 `abstract` 和 `site` 判断相关性，只对确认需要的非广告链接调 `extract`。

extract 返回 `title`/`content`/`date`/`author`/`sitename`/`length`/`truncated`。`truncated=true` 表示正文已截断，需要更多内容时调大 `--max-chars` 重试。

## 出错应对

`search` 单次最多返回 50 条，先读 `abstract` 判断相关性，只对真正需要的那几条调 `extract`。
**某一条 `extract` 失败很正常，不要死磕单条 url** —— 换 search 结果里下一条相关 url 继续。只有所有相关链接都失败时，才向用户说明并退回用 `abstract` 摘要回答。

需要区分的错误类型：

- **真实无结果**（`total=0` 且未报错）：360 确实没有该查询的结果。注意 360 很少返回真正的空结果——即使是无意义查询，它也会给出模糊匹配的网页（实测乱码串也能返回 6 条弱相关结果），所以要按 `title`/`abstract` 判断相关性，不能只看条数。换更具体或更通用的关键词重试；中文内容换 `baidu-search` / `sogou-search` 再试。
- **软限流**（stderr 含"360 触发软限流"）：360 对高频访问的 IP 静默返回"无结果页"，脚本用对照查询自动确认。该限制按 IP 生效，HTTP 通道短时间内无法恢复 —— **不要反复重试同一个命令**，按下面“HTTP 被验证码拦截时”一节用 agent-browser 处理，或改用 `baidu-search` / `sogou-search`。
- **验证码**（stderr 含"触发 360 验证码"）：同上，按下一节用 agent-browser 处理。
- **验证码页不给拼图**（页面显示"网络或服务器异常"、`img.v-wrap-img-front` 的 `src` 为 `undefined`）：IP 已被加重限流，立即停止 360，改用 `baidu-search` / `sogou-search`，至少 10 分钟后再试（见 2.1.4 节）。
- **翻页途中被拦**（stderr 含"翻页途中触发限制"）：已抓到的部分结果仍会正常返回（JSON 完整），按实际 `total` 使用即可，不要因此重试。
- **结果条数少于 `--num`**：正常现象，不算失败。360 单页混有短视频等垂直模块和 AI 摘要卡片，脚本已过滤，可用的自然结果通常每页 3~7 条；翻到末页后总数也会少于请求值，脚本会把实际拿到的全部返回（exit 0）。
- **HTTP 4xx/5xx**（如"HTTP 403 访问失败: https://真实url"）：404/410 说明页面已失效，直接换下一条；403 如果这条 url 确实关键，可换 `--client requests` 重试一次，否则也换下一条。
- **提取失败**（"提取失败: https://真实url（页面无正文）"）：页面是 JS 动态渲染或强反爬站，换下一条相关 url，或用 agent-browser skill 打开。
- **HTTP 400 且 URL 是 so.com/link**：跳转链接带签名校验，只能用 search 返回的 `data-mdurl` 真实地址，不要手工拼 so.com/link。
- **反爬拦截**：见上方"软限流"和"验证码"两类，按下一节用 agent-browser 处理。
- **依赖缺失**（ImportError）：告知用户安装对应包（`requests`/`beautifulsoup4`/`trafilatura`/`curl_cffi`）。

其他注意：

- 360 对 CSDN、新浪、知乎、ZOL 等站点收录较全，适合找中文技术/资讯内容。
  但注意：技术类查询的结果里 CSDN 系占比很高（实测一次英文查询 30 条里 19 条是 CSDN），
  而 CSDN 自身反爬强、extract/浏览器读取常被拦——**结果多 ≠ 可读**，选链接时留意站点。
- 广告结果已用 `is_advertisement=true` 标记，优先采用 `is_advertisement=false` 的非广告来源。
- 360 对高频请求敏感：`--num` 越大翻页越多，越容易触发限流。触发时脚本返回已抓取的部分结果或提示用 agent-browser，不会整单失败。
- 结果是爬虫抓取，360 页面结构变化时可能失效；失效时优先用 `baidu-search` / `sogou-search`。

## HTTP 被验证码拦截时：用 agent-browser 打开网页（重要）

HTTP 请求被限流/验证码后（stderr 提示"触发 360 验证码"或"触发软限流"），**不要反复重试命令行**，改用 agent-browser 走浏览器通道。浏览器通过验证后 cookie 会让后续页面继续可用；HTTP 脚本没有这个 cookie，所以后续搜索、翻页、读文章都继续在浏览器里做。

**固定使用同一个 session 名**（如 `--session so360`）：解封状态按浏览器会话保存，每次新建会话都要重新过验证码。

**不要自己起新的 agent-browser 会话去试**，直接复用已通过验证的那个会话。

### 1. 打开搜索页并过滑块（推荐一步完成）

`--url` 会自动打开页面（内部已处理假挂起）、判断是否需要验证码、需要时自动过滑块：

```shell
python scripts/solve_slider.py --session so360 --url "https://www.so.com/s?q=<URL编码后的关键词>"
```

- `--headed`：有头浏览器（可见窗口），过滑块实测更稳；无头模式更容易被判定为机器。
- 输出 `reason: passed` 或 `no_captcha` 就直接进行第 3 步（`browser_search.py`）。

只有脚本失败需要排错时，才手工走下面的打开流程（排错细节见 2.1）：

```
agent-browser --session so360 --headed open "https://www.so.com/s?q=<URL编码后的关键词>"
agent-browser --session so360 wait --load networkidle
agent-browser --session so360 screenshot ".tmp/agent-browser/captcha.png"   # 截图路径按项目调整
```

**首次启动会话会出现"假挂起"（Windows 实测）**：每个会话的第一条 agent-browser 命令要启动
daemon + Chrome，CLI 几秒内就完成了，但后台浏览器进程占住 shell 管道，
命令会一直不返回直到超时被杀。应对：

- **首选：给第一条命令设小超时（15 秒左右），超时属正常，直接继续下一步**。实测 15s 超时杀掉后，
  浏览器仍存活，下一条命令 0.3s 返回、页面也已加载完成；
- 执行工具没有超时参数时，用后台方式运行第一条命令（实测 10 秒内正常退出）；
- 同一会话的后续命令都在 1 秒内返回（实测 0.1~0.9 秒），**不要因为"卡住"就新建会话重试**。

注意：首条命令被重定向到验证码页时，输出是 `✓ 访问异常页面`——这是**正常现象**（"访问异常"
指的就是验证码页），不是失败，不要因此新建会话或重试。是否需要过滑块以 `solve_slider.py`
的返回为准（`no_captcha` = 不需要）。

### 2. 运行求解脚本（第 1 步已成功时跳过）

页面已打开（或第 1 步只做了 open、或需要重试）时，单独运行求解脚本。
识别缺口、算位移、分段拖动、失败重试全部自动完成：

```shell
python scripts/solve_slider.py --session so360
```

参数：

| 参数 | 说明 |
|------|------|
| `--session` | agent-browser 会话名，必须和打开页面时用的同一个（默认 `so360`） |
| `--url` | 可选：先打开这个搜索页再求解（会处理首条命令的假挂起） |
| `--dry-run` | 只算拖动距离，不实际拖动（调试用） |
| `--max-attempts` | 最多尝试次数（默认 3） |
| `--threshold` | RGB 兜底匹配的相关系数阈值（默认 0.6；边缘匹配优先，不受此值影响） |

返回 JSON，按 `reason` 处理：

| 结果 | 含义与动作 |
|------|-----------|
| `success: true`, `reason: passed` | 已验证通过，继续读取结果 |
| `success: true`, `reason: no_captcha` | 本来就不需要验证码，直接读结果 |
| `reason: no_puzzle` / `no_puzzle_image`（退出码 3） | **页面已没有拼图（360 加重限流），立即停止 360，改用 baidu-search / sogou-search** |
| `reason: max_attempts_reached` | 重试到上限仍失败，换引擎 |
| `reason: dry_run` | 只返回了 `drag_px` 和 `confidence`/`method` |

脚本内部要点（了解即可）：
- **缺口定位优先用边缘匹配**（拼图轮廓 vs 背景梯度），对"亮色拼图块 + 暗色缺口"这类配色同样有效；
  边缘匹配不可靠时才退回 RGB 模板匹配。`confidence` 在 edge 方法下是"峰值/均值"比值（≥1.5 采信）。
- 滑块与拼图是 1:1 线性映射；`mouse move` 只接受整数坐标；拖动分 8 段、间隔 120ms。
- 拖动失败后会点验证码的刷新按钮换一张新拼图再重试（不刷新的话同一张图会白白重试）。
- 首条 agent-browser 命令的假挂起会被超时兜住。

### 2.1 手工排错（脚本失败时才看）

#### 2.1.1 读滑块和拼图的位置（直接取整数坐标）

`getBoundingClientRect()` 返回的是浮点数，而 `agent-browser mouse move` **只接受整数坐标**，
传小数会报 `Missing arguments for: mouse move`（看起来像命令语法错误，实际是坐标不合法）。
所以直接用 `Math.round` 一次算好所有要用的整数坐标，后续命令全部用这些整数：

```
agent-browser --session so360 eval "JSON.stringify((()=>{const b=document.querySelector('.v-target-btn').getBoundingClientRect();const f=document.querySelector('.v-wrap-img-front').getBoundingClientRect();return {cx:Math.round(b.x+24),cy:Math.round(b.y+24),frontX:Math.round(f.x),frontW:Math.round(f.width)}})())"
```

- `span.v-target-btn`：滑块按钮（48×48），`cx`/`cy` 是滑块中心点（已取整）
- `img.v-wrap-img-front`：拼图块条带（94×232），初始 `frontX` 等于背景图左边界
- `canvas.v-wrap-img-bg`：带缺口的背景图（375×232）

#### 2.1.2 确定拖动距离

拖动距离 = 缺口在背景图中的 x 坐标 − 拼图块初始 x。两种方法：

- **边缘匹配（推荐，可靠）**：取拼图块轮廓点，在背景图的梯度图上滑动，梯度响应最高处就是缺口。
  对颜色不敏感（实测"亮块+亮缺口"和"亮块+暗缺口"都准），用"峰值/均值 ≥ 1.5"判断可信度。
- **RGB 模板匹配（兜底）**：把拼图块按 x 滑动做归一化相关，取相关系数最高的 dx；
  **拼图块与缺口明暗反差大时会失效**（实测相关系数只有 0.16），此时必须用边缘匹配。
- 输出必须是整数像素。
- **肉眼法（兜底）**：截图后放大缺口区域，读缺口左边缘相对背景图左边缘的像素差。
  缺口是盾牌右上方一块明显不同的拼图形亮块。

导出两张图：

```
agent-browser --session so360 eval "document.querySelector('.v-wrap-img-bg').toDataURL('image/png')"
agent-browser --session so360 eval "document.querySelector('.v-wrap-img-front').src"
```

注意：拼图 png 的原始尺寸（如 146×360）和页面显示尺寸（94×232）不同，匹配前要按显示尺寸缩放。

#### 2.1.3 按住滑块拖动（关键：整数坐标 + 分段移动）

实测 360 的滑块与拼图是 **1:1 线性映射**：滑块 `left=60px` 时拼图 `left` 也是 `60px`，
所以拖动距离 = 需要的拼图位移。

**每一步的坐标都必须是整数**。用上一步拿到的 `cx`/`cy` 和目标距离 `D`（整数），
按 6 段拖动（示例：起点 64，目标 205，即 D=141）：

```
agent-browser --session so360 mouse move 64 460        # 滑块中心（cx, cy）
agent-browser --session so360 mouse down
agent-browser --session so360 mouse move 96 460        # 每段 +30 左右，共 5~6 段
agent-browser --session so360 mouse move 128 460
agent-browser --session so360 mouse move 160 460
agent-browser --session so360 mouse move 185 460
agent-browser --session so360 mouse move 200 460
agent-browser --session so360 mouse move 205 460       # 终点 = cx + D
agent-browser --session so360 mouse up
agent-browser --session so360 wait --load networkidle
agent-browser --session so360 get url
```

要点（都是实测踩过的坑）：
- **坐标必须是整数**。小数坐标会报 `Missing arguments`，move 不会执行；如果此时继续 `mouse up`，
  就变成原地空提交，等于白白浪费一次机会。
- **每次 move 后检查命令是否真的成功**（输出 `✓ Done`，exit code 0）。有一步报错就
  `mouse up` 后重新打开页面换新拼图，不要在"没拖动的状态"下松手。
- **必须分段移动**（5~6 次，每次间隔 100~300ms），一次瞬移容易被判定为机器。
- 松手后等 3 秒左右；`get url` 从 `qcaptcha.so.com` 变回 `https://www.so.com/s?...` 即验证通过。
- 失败会自动换一张新拼图：重新截图 → 重新算缺口 → 重试。

#### 2.1.4 验证码后端不给拼图时（立即停止）

如果页面变成"网络或服务器异常"、`img.v-wrap-img-front` 的 `src` 是 `undefined`、
取图接口里的 `fp` 为空——**已经没有拼图可拖，再算坐标、再重试都没有意义**。
这说明 360 已按 IP 加重限流，和拖动技术无关。此时：

1. 立即停止所有 360 操作，不要再刷新页面或重试拖动；
2. 改用 `baidu-search` / `sogou-search` 完成当前任务；
3. 限流按 IP 生效：实测 HTTP 通道 20 分钟以上仍未恢复，不要原地等待，先换引擎把任务做完。

### 3. 用脚本执行浏览器搜索（推荐，不要手工写 eval）

验证码通过后，直接用脚本搜索。它内部会打开搜索页、提取结果、按页面真实链接翻页、
跨页去重，输出 JSON 与 `so360_search_cli.py search` **完全同构**（query/mkt/total/results）：

```
python scripts/browser_search.py --session so360 --keyword "关键词" --num 30
python scripts/browser_search.py --session so360 --keyword "关键词" --num 30 --debug   # 打印每页 url/条数
python scripts/browser_search.py --session so360 --keyword "关键词" --dry-run          # 只看页面状态
```

| 参数 | 说明 |
|------|------|
| `--session` | 必须与过验证码的会话同名（默认 so360），否则要重新过滑块 |
| `--num` | 目标条数 1~50，默认 30；实际可能更少（原因见下方"### 4. 翻页"和"结果条数少于 --num"条目） |
| `--max-pages` | 最多翻页数，默认 8 |
| `--debug` | 在 stderr 输出每页的 final URL 和新增条数。注意 stderr 里的 `total=` 是**累计去重数**，stdout JSON 里的 `total` 是 `min(--num, 累计)`，两者不同是正常的 |

退出码：`0` 成功；`4` 页面是验证码（先跑 `solve_slider.py`）；`2` 其他错误。
（注意与 `solve_slider.py` 的退出码区分：solve_slider 的 `3` = 无拼图要停止，browser_search 的 `4` = 是验证码页、可继续。）

**如果脚本出错需要手工排查**，注意 agent-browser 的 `eval` **只接受单行 JS**，
多行会静默返回 `null`（`solve_slider.ab_eval` 已自动压平换行，手工调用时要自己压平）。
手工提取结果的 eval 片段（单行）：

```
agent-browser --session so360 eval "JSON.stringify((()=>{const out=[];for(const li of document.querySelectorAll('li.res-list')){if(li.querySelector('[data-mohe-type]')||li.matches('[data-mohe-type]'))continue;const a=li.querySelector('h3 a');if(!a)continue;const u=a.getAttribute('data-mdurl')||'';if(!u.startsWith('http'))continue;const h=new URL(u).hostname;if(/(^|\.)(so\.com|360kan\.com|hao\.360\.com)$/.test(h))continue;const p=li.querySelector('p.res-desc,.res-list-summary');out.push({title:a.innerText.trim(),url:u,abstract:p?p.innerText.trim():''})}return {count:out.length,results:out}})())"
```

必须过滤两类节点：垂直模块（带 `data-mohe-type`）和 360 自有域名（`tv.360kan.com` 等），
否则会混进"短视频大全"这类卡片。每页真实网页结果通常只有 3~7 条，属正常（其余是广告/垂直模块/AI 卡片）。

### 4. 翻页：必须在页面内点击页码（脚本已自动处理）

实测三种方式，只有一种有效：

| 方式 | 结果 |
|------|------|
| `open "...&pn=2"` 直接导航 | ❌ 被静默重定向回第 1 页（final URL 里 pn 消失） |
| `agent-browser click "a[href*='pn=2']"` | ❌ 点击返回 ✓ 但不跳转 |
| **页面内 JS 点击页码 `a.click()`** | ✅ URL 保留 `pn=2&psid=...`，拿到真正的下一页 |

正确做法：

```
agent-browser --session so360 eval "JSON.stringify((()=>{const a=[...document.querySelectorAll('a')].find(a=>a.innerText.trim()==='2'&&/pn=\d+/.test(a.href));if(!a)return 'NOT_FOUND';a.click();return 'OK:'+a.href})())"
```

点完后用 `agent-browser --session so360 wait --load networkidle` 等页面加载（必要时再 sleep 2 秒），
然后用 `get url` 确认仍带 `pn=N`；丢了说明被打回首页，停止翻页。
相邻页会有重复结果，按 URL 去重即可。

`browser_search.py` 已实现该逻辑：实测 5 页（4+7+7+7+7）去重后正好 30 条，耗时约 1~1.5 分钟
（页数越多越久，不要按固定秒数设超时）。页面没有下一页链接时会自动停止。

### 5. 阅读文章

按页面类型选方法：

- **静态页**：直接用命令行 `extract`（它直连目标站，不受 360 限流影响）。
- **JS 渲染页**：`agent-browser read <url>` 是 HTTP 抓取，只能拿到导航文字，不要用它。应打开页面后读渲染 DOM：

```
agent-browser --session so360 tab new "<文章URL>"
agent-browser --session so360 wait --load networkidle
agent-browser --session so360 eval "JSON.stringify((()=>{const el=document.querySelector('article,.article-content,.post-content,#content')||document.body;const t=el.innerText||'';return {len:t.length,text:t.slice(0,12000)}})())"
```

- **目标站自身有反爬**：CSDN 返回"安全验证"页、知乎直接 403、cfi.net.cn 返回 295 字节空页、
  易车（news.yiche.com）extract 拿不到正文 —— 换下一条结果，不要死磕（这与 360 限流无关，是目标站自己的策略）。
  实测网易号文章（www.163.com/dy/article/...）可以直接 extract 成功。

浏览器方式也失败时，退回 `baidu-search` / `sogou-search`，不要死磕 360。

## 关于 references 文件夹

把特定反爬、或 http 直接请求主 url 拿不到正文的网站的处理经验，写到 `references/` 文件夹下的对应文件中
（文件不存在时先创建 `references/<站点名>.md`，如 `references/csdn.md`）。
原因：有些网站反爬，有些需要 ajax 请求具体接口才能拿到正文，直接 http 请求主 url 拿不到真正的正文内容。
下次遇到同类站点时，先查 references 里有没有对应文档，有就按文档处理。
