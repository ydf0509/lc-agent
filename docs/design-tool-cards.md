# 内置工具个性化卡片 — 设计方案

> 状态：P0 已实施（待用户验收），P1/P2 待排期
> 日期：2026-09-10
> 相关代码：`frontend/src/components/chat/tools/`（新增 8 文件）、`frontend/src/views/ChatView.vue:173-202`、`frontend/src/stores/chat.ts:121-137`、`lc_agent/tools/system_tools/`、`lc_agent/middlewares/ask_user.py`

## 1. 为什么做

现状：所有工具共用一个 `ToolCallCard`，头部都是“工具调用 + 英文 tool 名 + 状态 tag”，只能靠看小字区分。三个具体毛病：

1. **编辑和新建长得一样** —— `edit_block` 有 diff 数据也没用好，`write_file` 是新建还是重写一眼看不出。
2. **跑命令没有终端感** —— 命令和输出都按普通文本排，没有 `$` 提示行、没有退出码/耗时置顶，流式输出时更难读。
3. **读取类太占地方** —— `read_file` / `search_files` / `list_directory` 动不动几百行，把对话流冲得很长，其实用户只想先看一行摘要。

已经证明“按工具分发”是对的路：`write_todos`→`TodoProgressCard`、`subagent`→`SubAgentCard`、`ask_user`→`InterruptDialog`、文件变更→抽屉。本方案就是把这条路补完，覆盖高频内置工具。

## 2. 设计原则（6 条）

1. **标题说人话**：头部是“动词 + 对象”（改了哪个文件、跑了什么命令），原始英文 tool 名只放次要位置或 tooltip，不做主标题。
2. **高频做厚、低频做薄**：编辑 / 写入 / 命令三种精致化；读取 / 搜索 / 列表反向优化——默认压成一行，点开再看。
3. **刷新后还能看到当时的 diff**（2026-09-10 补）：`file_edit_diff` / `file_write_preview` 事件在 `accumulate_display_state` 里挂到同一 tool_call 上（`fileDiff` / `filePreview`），随 `tool_calls` JSON 一起入库；历史接口原样返回，前端 `normalizeHistoryMessage` 保留字段后直接渲染。子 Agent 内部工具的 diff 事件跳过（ns 第一段是父 task，会挂错位置；内层调用走子会话自己的历史）。
4. **状态沿用现有语言**：running 蓝、done 绿、error 红，左侧框线 + running 呼吸灯 + done 扫光保持不变，不另起一套颜色。
5. **默认折叠省空间**：done 默认收起，running / error 默认展开。用户点头部任意位置切换。**例外**（2026-09-10）：编辑/写入文件卡（`edit_block` / `write_file`）不自动折叠——`useToolCard` 传 `keepExpanded: true`，完成后也保持展开，只有用户手动点才收（改了什么要一眼看到，尤其刷新后）。
6. **展开区三段栅格**（2026-09-10 补）：所有卡的展开区统一是「工具 → 目标 → 内容」三段，左列 32px 灰色小字标签、右侧内容。工具段显示原始工具名（等宽 + 复制），人话名已经在头部，不重复。标签按卡分别定名，不强行统一成「入参 / 结果」——那套词套到 diff 和命令输出上不准。
7. **后端零改动**：纯前端按 tool 名分发，解析现有返回字符串；`fileDiff` / `filePreview` / `streamingOutput` / `pid` 等现成结构化字段直接用，不新增 SSE 事件。

## 3. 总览：工具 → 卡片

| 后端工具 | 前端卡片 | 默认（done 时） | 一句话说明 |
|---|---|---|---|
| `edit_block` | FileEditCard（P0） | 展开 diff | 红绿 diff 行 + 行号，点击文件名看全文 |
| `write_file` | FileWriteCard（P0） | 追加/重写展开前 20 行，新建只显示一行 | 蓝色“新”字图标，与编辑一眼区分 |
| `run_command`、`start_background_process` | TerminalCard（P0） | 展开 | 黑底终端，`$ 命令` 置顶，尾巴带耗时/退出码/PID |
| `read_process_output`、`kill_process`、`list_all_processes`、`list_agent_started_processes` | TerminalCard 复用（P2） | 折叠 | 同终端样式，头部换成对应动作 |
| `read_file`、`read_multiple_files` | ReadCard（P1） | 折叠成一行 | `读 a.py · 120 行`，点开看内容，图片显示缩略图 |
| `list_directory` | DirectoryCard（P1） | 折叠成一行 | `看目录 src · 34 项`，点开是文件树 |
| `search_files` | SearchCard（P1） | 折叠成一行 | `搜 "timeout" · 8 处`，点开按文件分组、关键字高亮 |
| `get_file_info`、`get_system_info`、`get_current_time` | InfoBadge（P2） | 一行，不可展开 | 灰色小徽章，不占纵向空间 |
| `create_directory`、`move_file`、`delete_file` | FileOpCard（P2） | 一行，不可展开 | 单行动词卡，删除红色、移动黄色警示 |
| `write_todos`、subagent 系列、`ask_user` | 保持现状 | — | 已有专属 UI，本方案不动 |
| MCP / skill / 未知工具 | GenericToolCard（兜底） | 折叠 | 现在的 `ToolCallCard` 瘦身后直接当兜底 |

## 4. 路由架构（只改前端）

`ChatView.vue` 现在是三分支（todos / subagent / 通用卡），在第三支加一层分发：

```vue
<!-- ChatView.vue #content 段，第 3 支替换为 -->
<ToolCardRouter v-else :tool-call="item.toolCalls[seg.toolIndex!]"
  :collapsed="item.toolCalls[seg.toolIndex!]?.status === 'done'" />
```

```vue
<!-- ToolCardRouter.vue：纯 switch，不含样式 -->
<FileEditCard  v-if="name === 'edit_block'" ... />
<FileWriteCard v-else-if="name === 'write_file'" ... />
<TerminalCard  v-else-if="isTerminal(name)" ... />
<ReadCard      v-else-if="isRead(name)" ... />
<DirectoryCard v-else-if="name === 'list_directory'" ... />
<SearchCard    v-else-if="name === 'search_files'" ... />
<InfoBadge     v-else-if="isInfo(name)" ... />
<FileOpCard    v-else-if="isFileOp(name)" ... />
<GenericToolCard v-else ... />
```

公共逻辑抽 `useToolCard.ts`：折叠 toggle、运行计时、复制、全屏 modal、搜索高亮。各卡只写头部 + 主体。新增文件放 `frontend/src/components/chat/tools/` 目录，不动现有组件。

## 5. P0-1 FileEditCard（`edit_block`）

数据来源：`toolCall.fileDiff`（`{file, start_line, context_before, removed, added, context_after}`，见 `file_write_tools.py:_emit_edit_diff`）+ 返回字符串尾的 `A lines → B lines`。

- **头部**：绿色“改”图标 + `改 src/app.py` + `+12 −3` + 耗时。error 时整卡红框 + 错误原因。
- **主体**：diff 行（已实现的红绿底 + 行号保留），>30 行折叠 + “展开全部 (N 行)”按钮。
- **操作**：点文件名 → `CodeBlockModal` 看全文（已实现，保留）；右下“在抽屉里看”→ 打开 `FileChangesDrawer` 看该文件最终状态（卡内是本次改动，抽屉是最终状态，两者共存）。
- **边界**：`expected_replacements != 1` 时后端不发 diff 事件，此时退化为两行文本卡（显示返回的错误 reason）；`old_string not found` 直接红卡显示错误头两行。

```
┌ 改 src/app.py  +12 −3 · 0.8s · 已完成 ─────┐
│ 42   ctx = load()                          │
│ 43 − timeout = 30        (红底)             │
│ 43 + timeout = 60        (绿底)             │
│ 文件名可点 → 看全文 · 在抽屉里看            │
└────────────────────────────────────────────┘
```

## 6. P0-2 FileWriteCard（`write_file`）

数据来源：`toolCall.filePreview`（`{file, mode, preview_lines, total_lines, start_line}`）+ 返回字符串开头（`Written` / `Appended`）。

- **头部**：蓝色“新”图标。标题按 mode 说人话：`新建 docs/report.md · 20 行` / `重写 app.py · 120 行` / `追加到 log.txt · +30 行`。注意：后端 `rewrite` 时新建和重写都返回 `Written`，V1 不强行区分，新建/重写统一显示“写入”，只把 `append` 区分出来；想精确区分等 P2 后端把返回改成 `Created` / `Rewrote` 再换标题（前端只改一行解析）。
- **主体**：只显示新增行（绿底 `+`，已有实现保留），不显示 diff 红行——这就是和编辑卡最直观的区别。>20 行截断 + “还有 N 行没显示（点开看全文）”。
- **running 时**：显示骨架行 + 转圈，不闪。

```
┌ 新 写入 docs/report.md · 20 行 · 已完成 ───┐
│ + # 周报                    (绿底，只贴新增) │
│ + - 进展 ...                                │
└────────────────────────────────────────────┘
```

## 7. P0-3 TerminalCard（`run_command` / `start_background_process`）

数据来源：`streamingOutput`（流式块事件 `command_output` 拼的）→ `result`；`pid` + `bgProcessRunning`（事件 `command_process_info`）；返回串尾的 `[exit_code=N, duration=Nms]` 或 `[Command timed out ...]` 用正则解析，不用改后端。

- **头部**：黑卡顶部 `$ npm run dev --port 3000`（单行省略，hover 显示全命令 + 一键复制按钮）。右侧状态灯：跑动中蓝色呼吸点 + 计时，结束显示 `2.3s · 退出码 0`（非 0 则红字），后台进程显示 `PID 1234 + ■ 停止`（已有 kill 逻辑保留）。
- **主体**：永远黑底（浅色模式也不反白，像 Codex/Cursor 的终端），等宽字体，ANSI 颜色保留（已有 `ansi_up` 保留）。stderr 行加暗红底 + `[stderr]` 前缀；timeout / 非零退出在末尾加一条红色状态行，不混在输出里。
- **截断**：>400px 高度出内部滚动 + 右下全屏按钮（已有 modal 保留）；流式时自动跟随到底部，用户手动上滚后停止跟随（加个“回到底部”小按钮）。
- **进程复用**：`read_process_output` 头部换成 `看后台输出 PID 1234 · 运行 12s`；`kill_process` 成功显示一行灰字 `已停止 PID 1234`，失败红字；两个 list 进程工具输出是 TSV 表，渲染成等宽小表，不用黑卡以外的样式。

```
┌ ● 运行 npm run dev ── 2.3s ── PID 1234 ■停止 ┐
│ $ npm run dev --port 3000          [复制]    │
│ ready in 1.2s · listening on :3000          │
│ [退出码 0 · 2.3s]                            │
└──────────────────────────────────────────────┘
```

## 8. P1 读取类：默认压成一行

- **ReadCard**（`read_file` / `read_multiple_files`）：头部 `读 a.py · 120 行` / `读 3 个文件`，折叠时只占一行。解析返回头 `[Lines X-Y of Z total]` 拿总数。点开展示代码块（按扩展名高亮，复用 `CodeBlockModal` 的语言映射）。图片返回（`[Image: name, size]` + base64）渲染缩略图 + 点击放大，不贴 base64 文本。
- **DirectoryCard**（`list_directory`）：头部 `看目录 src · 34 项`（数 `[DIR]`/`[FILE]` 行）。点开是缩进文件树：目录 📁 蓝字、文件按扩展名小图标，大小灰字。`depth` 参数大时只渲染前 200 行 + 提示。
- **SearchCard**（`search_files`）：头部 `搜 "timeout" · 8 处 · content`（`No matches found.` 显示灰字 `搜 "xxx" · 无结果`，不展开）。点开按文件分组，`文件:行号` 可点（点后调 `/tools/file/read` 看上下文），命中词黄底高亮，`files` 模式（按文件名找）只列文件名清单。

## 9. P2 小卡：FileOpCard + InfoBadge

- **FileOpCard**（`create_directory` / `move_file` / `delete_file`）：单行，不可展开。`📁 新建目录 a/b` / `⤷ a.py → b.py` / `删除 old.log`。删除红字红框、移动黄字，成功加 `✓` + 耗时。失败才可点开展示错误。
- **InfoBadge**（`get_file_info` / `get_system_info` / `get_current_time`）：行内灰徽章，例如 `🕒 2026-09-10 12:00 (Asia/Shanghai)` / `💻 Windows x64` / `a.py · 12 KB · 120 行`（解析 `size:` / `line_count:` 两行）。hover 显示完整返回，click 复制。

## 10. 通用规范（所有卡共用）

- 颜色：状态色只用 Element Plus 变量（primary/success/danger/warning）；diff 红绿沿用现有 `#f85149` / `#3fb950`；终端黑 `#0d1117` 全主题统一。
- 字体：标题 13px 系统字体，命令/路径/diff/输出一律 JetBrains Mono 等宽 12px。
- 头部永远包含：图标 + 人话标题 + 状态（跑动计时 / 完成耗时 / 错误红字）；原始 tool 名藏进 tooltip。
- **展开区三段栅格**（2026-09-10 定）：左列 `ToolField.vue` 统一 32px 宽、11px 灰色标签（深色卡 tone="dark" 走 `#7d8590`），右侧内容。四张卡的分段：

  | 卡 | 第一段 | 第二段 | 第三段 |
  |---|---|---|---|
  | 通用 | 工具 | 入参 | 结果 / 错误 |
  | 编辑 | 工具 | 文件 | 改动 |
  | 写入 | 工具 | 文件 | 内容 |
  | 终端 | 工具 | 命令 | 输出 / 错误 |

  工具段显示原始工具名（等宽 12px + 复制按钮）；人话名在头部，展开区不重复。命令段自带 `$` 提示 + 复制按钮（终端卡内独立样式）。错误段在折叠态也直接露出，不被折叠藏起来。
- **入参渲染规则**（2026-09-10 定）：单行且 ≤160 字符 → 紧跟参数名内联；多行或更长 → 独立浅底块（`max-height: 132px`）＋「看全文」按钮。`key` 是 11px 灰色小字，`value` 是 12px 等宽正文色——主次和旧版相反（旧版 key 用主题蓝，比 value 还抢眼）。**不再硬截断**：超 2000 字符只截显示、不截数据，点「看全文」走 `CodeBlockModal` 看完整内容。对象/数组按 2 空格缩进 JSON 展开。
- **弹层目标**：结果和某个入参共用一个 `CodeBlockModal`，用带类型的 `ModalTarget`（`{kind:'result'} | {kind:'arg', key}`）区分，不用字符串哨兵——否则某个入参正好叫 `result` 会串台。
- **复制按钮多槽位**：一张卡里工具名、命令各有一个复制按钮，`useToolCard` 用 `copyStates` 按 key 分别存状态（`copyLabel(key)` / `copyText(text, key)`），不共用单槽状态。
- 返回内容徽章（2026-09-10 补回）：done 后头部显示 `📦 1.2K chars | ~340 tokens`（旧 `ToolCallCard` 原有功能，拆卡时丢了，现抽到 `useToolCard` 公共返回：`resultSizeText` + `tokenText`）。token 用 `js-tiktoken` 懒加载 `cl100k_base` 估算，结果 > 500K 字符不估；编辑/写入/终端/通用四类卡都显示。
- 移动端 520px 下：头部换行、标题占满一行（沿用现有 media query 写法），终端卡横向可滚、全屏 modal 占满。
- 动效：只保留现有 running 呼吸灯 + done 扫光；`prefers-reduced-motion` 下全关（已有代码保留）。

## 11. 实施顺序与验收

- **P0**：`ToolCardRouter` + `FileEditCard` + `FileWriteCard` + `TerminalCard` + `GenericToolCard`（现状 `ToolCallCard` 改名瘦身）。验收：`TestSegments.vue` 加 6 组样例（编辑/新建/追加/短命令/长流式/失败命令）逐个预览通过。
- **P1**：`ReadCard` + `DirectoryCard` + `SearchCard`。验收：1000 行读取、34 项目录、8 处搜索结果三组样例，默认折叠后对话流高度减少一半以上。
- **P2**：`FileOpCard` + `InfoBadge` + 进程卡复用 + 后端返回文案微调（`Created`/`Rewrote` 区分）。验收：全工具走一遍无兜底泄漏（未知工具仍显示通用卡）。

## 12. P0 实施记录（2026-09-10）

已落地，文件都在 `frontend/src/components/chat/tools/`：

- `toolCardRouter.ts` — 按 tool 名分发（`edit_block`/`write_file`/`command__*` 全覆盖，P1/P2 的 read/directory/search/info/fileOp 已预留 kind，暂时走 generic）
- `useToolCard.ts` — 公共逻辑（折叠、运行计时、复制）
- `ToolFileCard.vue` + `ToolFileEditCard.vue` / `ToolFileWriteCard.vue` — 编辑（绿“改”+红绿 diff）/ 写入（蓝“新”+只贴新增行），复用 `fileDiff`/`filePreview`，点文件名看全文 + “在抽屉里看”跳 `FileChangesDrawer`
- `ToolTerminalCard.vue` — 黑底终端，`$ 命令` 置顶+复制，尾部 `[退出码 N · 耗时]`（正则解析 `run_command` 返回串），stderr 暗红块，PID+停止按钮+后台轮询从旧卡原样搬过来
- `ToolGenericCard.vue` — 兜底：人话标题（读/看/搜/删等中文动词+对象摘要）+ 参数 + 结果预览，旧 `ToolCallCard.vue` 不再被引用（文件保留未删）
- `ToolCardRouter.vue` — ChatView/ChatBubble 统一入口，`write_todos`/subagent 分支不动
- 契约测试 `frontend/scripts/check-tool-cards-contract.mjs`（`npm run test:tool-cards`），宽度/历史/编辑三份旧契约同步通过
- 预览页：`/test-segments` 改成 7 组 P0 样例（编辑/新建/追加/短命令/流式中/失败命令/通用兜底）
- 构建产物已同步到 `lc_agent/web/dist`（构建时如遇 safe-delete 锁或 rolldown 1224 文件锁，等几秒用 `--emptyOutDir=false` 重试即可）

## 13. 展开区栅格实施记录（2026-09-10 第二轮）

新增 `ToolField.vue`（左列标签 + 右内容 + 可选复制按钮，`tone="dark"` 给终端卡），三张卡接入：

- `ToolGenericCard.vue` — 工具 / 入参 / 结果（错误时第三段换「错误」）。入参去掉 200 字符硬截断，改内联/块二选一 + 「看全文」。
- `ToolFileCard.vue` — 工具 / 文件 / 改动|内容。文件名从旧的黑底标题条挪进「文件」段，改成浅底等宽可点；「看全文 / 在抽屉里看」挪到「改动 / 内容」段底部。头部 tooltip 改用 `fullTitle`（`改 a.py（src/…/a.py）`），顺手删掉之前攒下的 `void fullTitle` 死代码。
- `ToolTerminalCard.vue` — 工具 / 命令 / 输出（全部 `tone="dark"`）。命令段保留 `$` + 复制按钮（卡内独立 `tt-copy`，跟工具名复制按钮各存各的状态）。删掉没用上的 `escapeHtml`，给 `v-html` 里的 `[stderr]` 标签补了 `:deep(.stderr-tag)` 上色（scoped 样式进不去 `v-html`）。
- `useToolCard.ts` — 单槽 `copyState` 换成多槽 `copyStates` + `copyLabel(key)` / `copyText(text, key)`。
- 契约测试补 10 条断言（ToolField 引入、四张卡的工具名行、各卡标签文字、`tone="dark"`、多槽复制、入参不再硬截断、`ModalTarget`、样例折叠开关）；`/test-segments` 扩到 10 组，样例支持自带 `collapsed` 开关。

**本轮修掉的坑**：

- 弹层原本用字符串哨兵 `'result'` 区分「结果」和「某个入参」，入参正好叫 `result` 会串台 → 改带类型的 `ModalTarget`。
- `/test-segments` 第 10 组标着「折叠态露出错误」但模板写死 `:collapsed="false"`，根本测不出折叠 → 样例自带宽窄开关。
- `restart.ps1` 三处环境坑：`netstat.exe` 在沙箱里起不来却被 `$ErrorActionPreference="Stop"` 当致命错误（改 try/catch 容错，`Get-NetTCPConnection` 是主路径）；`npx vite build` 走 cmd.exe 包装脚本起不来（改成直接用 node 跑 `node_modules/vite/bin/vite.js`）；`Get-Command node` 在非交互会话里取不到 node（改成候选列表探测，含 WorkBuddy 托管版本目录）。

**明确不做**：卡内直接改文件/重跑命令（只读展示，改文件走抽屉+对话）；卡片主题自定义；后端新增结构化字段（一期只靠解析现有字符串）。
