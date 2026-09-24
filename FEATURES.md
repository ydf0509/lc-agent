# lc-agent 框架功能清单

> 本文档基于 `lc_agent/` 源码整理，目标是列举 lc-agent 已经具备哪些功能，避免重复造轮子或建议已存在的功能。
>
> 整理日期：2026-09-16
> 框架 PyPI 包名：`lc-agent-app`
> 框架直接启动入口：`lc_agent.main:main`（`python -m lc_agent`），仅用于框架独立运行场景，**不用于 lc-agent-bfzs 项目**

---

## ⚠️ 重要：项目定位与关系

**lc-agent 本身是功能完整的 AI Agent 平台**（含 Web UI、Agent 引擎、MCP 管理、认证、持久化等），并非仅是底层库。lc-agent-bfzs 是在此基础上的**薄层演示扩展**，代码极少（1 个自定义工具文件 + 1 个自定义 Agent + `config.jsonc` 配置），主要价值是展示接入方式并配置了丰富的第三方 MCP。

| 项目 | 路径 | 角色 |
|------|------|------|
| **lc-agent**（本文档） | `D:\codes\lc-agent` | 功能完整的 AI Agent 平台，提供 Web UI / 引擎 / MCP / 认证 / 持久化全套能力 |
| **lc-agent-bfzs**（薄层演示扩展） | `D:\codes\lc-agent-bfzs` | 代码极少的演示项目，仅添加少量自定义工具、一个自定义 Agent 和 config.jsonc；AI 日常部署运行的目标环境 |

### bfzs 关键信息（AI 必须了解）

| 项目 | 路径 |
|------|------|
| 入口文件 | `D:\codes\lc-agent-bfzs\bfzs\main.py` |
| 配置文件 | `D:\codes\lc-agent-bfzs\config.jsonc` |
| 应用数据库 | `D:\codes\lc-agent-bfzs\bfzs_data.db` |
| Checkpoint 数据库 | `D:\codes\lc-agent-bfzs\bfzs_checkpoints.db` |
| Skills 目录 | `D:\codes\lc-agent-bfzs\myskills\`（演示用）+ `D:\codes\lc-agent-bfzs\skills_query_feature\`（功能查询类），均为演示，与 bfzs 项目目标无关 |
| 服务端口 | `8001` |

**bfzs 启动方式（唯一正确方式）**：使用 `restart-bfzs` skill，执行：
```powershell
powershell -ExecutionPolicy Bypass -File "D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\restart.ps1"
```
该脚本在 `D:\codes\lc-agent-bfzs` 目录下，以 `D:\ProgramData\miniconda3\envs\py312\python.exe` 运行 `python -m bfzs.main --port 8001`，并负责构建前端、停止旧进程。

**bfzs 的 MCP 扩展能力**：bfzs 通过 `D:\codes\lc-agent-bfzs\config.jsonc` 中的 `mcpServers` 字段配置任意第三方 MCP 服务器。当前 bfzs 已配置的 MCP 示例：联网搜索（web-search/anysearch）、LSP 代码工具（serena）、库文档检索（context7）、LangChain 文档（docs-langchain/reference-langchain）、RAG 知识库（nbrag）。新增 MCP 只需在 bfzs 的 `config.jsonc` 里加条目，重启服务即可生效。

---

## ⭐ 框架核心功能一览

> 以下是 lc-agent 作为 AI Agent 平台的完整功能列表，按产品能力分类。
> **lc-agent 是完全自托管的 AI Agent 平台**，所有数据（对话、记忆、配置、文件）100% 留在本地；LLM 推理需要外部 API（OpenAI 兼容），也可接自托管 LLM 实现全链路私有化。

### 聊天与交互
- **多会话管理**：多个独立会话并行，支持 pin/删除/标题自动生成
- **顶部会话标签栏**：跨 Agent 全局单栏，持久化 open/active，支持右键菜单（关闭/关闭其他/关闭右侧/关闭全部/置顶/重命名/删除）、中键关闭，streaming/未读状态提示，子会话按标签隔离
- **会话深链与草稿**：支持 `/c/:sessionId` 深链恢复，本地先建草稿会话、首次发送才落库，滚动位置与输入草稿按会话记忆
- **实时流式输出**：SSE 推流，对话内容逐字渲染；支持停止生成，发送计时显示
- **思考过程展示**：reasoning 模型的思考内容以折叠块展示，超长自动折叠，流式时自动展开
- **多模态输入**：支持图片和文本文件上传（图片自动压缩），拖拽/粘贴/附件，`/` 唤起 Skill 选择器，Ctrl+Enter 发送，4 种输入框动画
- **Markdown 渲染**：代码块语法高亮（highlight.js），代码可复制/展开；Markdown 版式 10 种 + 配色 10 种
- **消息操作**：支持编辑最后一条用户消息后重新生成；时间分隔线；复制最近 N 轮（可选含思考/工具）、单条复制回答/思考/工具
- **Ask User 交互**：Agent 在任务中途可向用户发起多选/文字提问，支持单选/多选/自定义 Other/必填校验/跳过，等待回答后继续
- **会话持久化与恢复**：LangGraph Checkpoint 完整快照，切换会话不丢上下文
- **查看子会话**：子代理运行会产生一个独立子会话，用户可点击进入查看它完整的对话历史，面包屑导航返回
- **布局**：三栏可拖拽宽度并记忆，支持 PC 与移动端（移动端变抽屉），动态标题 + favicon
- **主题切换**：暗色 / 亮色

### 文件与终端操作（内置工具）
- **文件读写**：读取、写入、搜索、移动文件；精确字符串替换时前端渲染 **diff 预览**，整文件覆写时展示内容预览。前端支持excel word ppt pdf查看，通过lc_agent/skills/office支持excel word ppt pdf的编辑。
- **命令执行**：运行 shell 命令，输出实时以"打字机"效果流式显示（ANSI 颜色支持）
- **后台进程管理**：启动后台进程、查看输出、终止进程
- **安全边界**：可配置 `allowed_directories` 限制文件读写范围；命令工具支持 `blocked_commands` 黑名单；写入可配置扩展名黑名单

### Agent 智能能力
- **Todo 任务分解**：AI 将复杂任务拆解为有序 todo 并追踪进度，支持多步骤工程任务
- **子代理委派（Subagent）**：Agent 可将子任务委派给专用子 Agent，模型可在同一轮发起多个子任务
- **长期记忆**：跨会话持久化记忆，Agent 通过工具主动存取；可配置语义检索（OpenAI 兼容 Embedding API）
- **上下文摘要**：自动压缩超长对话，保留关键信息继续推理
- **项目模式**：开启 `project_mode` 并配置 `project_root` 后，自动注入 AGENTS.md 规则 + git 状态 + OS 信息；同时激活文件工具目录边界（支持 `extra_dirs` 扩展）、加载项目级 MCP（`.agents/mcp.json`）和项目级 Skills（`.agents/skills/`）

### 配置与扩展
- **多 LLM 供应商**：任意 OpenAI 兼容接口（OpenAI、Anthropic、DeepSeek、Gemini 等），config.jsonc 一键切换
- **运行时 LLM 参数调整**：前端面板可实时调整 temperature、reasoning_effort 等参数，无需修改预设
- **多 Agent 预设**：通过 UI 创建/管理多套 Agent 配置（系统提示、工具集、MCP、Skills 权限），存储于数据库
- **MCP 集成**：通过 config.jsonc 接入任意第三方 MCP 服务器（无需改代码），支持 local/SSE/HTTP 三种传输
- **Skills 系统**：目录式 Skill，AI 可动态加载执行自定义脚本工作流；运行时支持开关单个 Skill / 工具组 / MCP 服务器
- **JSONC 配置驱动**：providers、database、memory、auth、skills、MCP 全部配置化
- **代码注册 Agent**：开发者可将自定义 LangGraph Agent 注册到框架，无需改框架代码
- **提示词模板库**：可创建可复用提示词片段，绑定到 Agent 预设
- **内置 OpenAPI 文档**：`/api/docs` 自动生成，便于二次开发与集成

### 管理与安全
- **用户认证**：JWT + bcrypt，角色分 admin/user，支持多用户（需配置 `auth.secret` 启用，不配置则匿名 admin 模式）
- **工具权限 + HITL 拦截**：管理员可配置工具白名单，非白名单工具调用需用户实时审批（管理员可在审批时永久加白名单）
- **用户→Agent 访问控制**：管理员可控制每个用户能访问哪些 Agent 预设
- **Token 用量记录**：每条消息记录 input/output token 用量（对话界面内，当前轮次明细）
- **Token 费用统计**：独立用量页面（管理页 + 个人页），每次 LLM 调用落库，按用户/agent/模型/天聚合金额，单价可配（同模型只保留最新一条单价），可导出 CSV，可点开会话看每次调用明细；个人页支持日期范围、按天/月、按 Agent/模型分组、含子 Agent、缓存命中/写入列，无单价显示 `—`，支持 top 会话排行
- **HTTP 请求追踪**：完整展示 LLM HTTP 请求/响应，便于调试
- **数据清理**：按保留天数预览 sessions/messages/threads，支持跳过置顶/活跃会话，二次确认删除，双库 VACUUM 压缩
- **自动数据库迁移**：Alembic 启动时自动迁移，升级框架无需手动操作

### 自动化任务
- **定时任务**：按照用户指定的 agent 定时自动运行任务，支持单次/间隔/每天/每周 4 种周期，带时区
- **任务管理**：手动立即执行、暂停/恢复、失败重跑、执行历史可跳转回看会话，单次任务跑完自动停用，防重复执行
- **群通知**：可通知到钉钉/企业微信/飞书，支持多目标管理、测试发送、推送成功/失败状态追踪

### ai coding 强化
- **专门的项目模式**：自动将绑定的项目文件夹作为agent的工作目录，自动读取项目下的AGNTES.md 和 .agents/skills 文件夹的skill。 专门的集中展示文件变动内容，专门划分git变化和当前会话agent修改文件导致的变动内容。
- **文件变更审查**：双源对照（本会话 Agent 修改 vs Git Diff），Unified/Side-by-side 切换，按轮次筛选，按子 Agent 分组；Git 基准可切会话开始/HEAD/暂存区/指定提交；顶栏变更数徽标，每轮末尾变更卡片，点击跳转定位
- **项目文件管理**：左栏 Chats/文件双视图（仅项目模式显示文件）；文件树支持文件名+内容双搜、新建/重命名/删除、复制绝对/相对路径、分支显示
- **多标签编辑器**：标签 pin/恢复关闭/未保存圆点，面包屑，搜索计数，Markdown 预览，Word/Excel/PPT/PDF 只读预览，图片全屏放大，二进制/超大文件降级，保存冲突提示，可复制 `路径#L行号` 引用

---

## 0. 启动与入口

- 框架通过 `python -m lc_agent` 直接启动（支持 `--config`/`--host`/`--port` 参数）
- 演示项目 bfzs 通过 `restart-bfzs` skill 脚本启动（见上方 bfzs 关键信息）
- 桌面模式：支持 pywebview 嵌入

**启动时自动完成**：DB 初始化与迁移 → Auth 初始化（配置了 `auth.secret` 时自动创建 admin） → Checkpoint 初始化 → 长期记忆 Store 初始化（需 `memory.enabled`） → Agent 预设加载 → 自动化调度器恢复（重启后恢复定时任务） → MCP 后台并行连接

---

## 1. 核心引擎

### 1.1 Agent 预设与管理
- **三种内置预设**：`chat`（纯对话，禁用工具组 + MCP + Skills）、`empty`（启用全部工具组 + MCP，禁用 Skills）、`power`（全部启用）；切换预设时联动批量重置运行时开关
- **三种 Agent 来源**：框架内置预设、用户在 UI 创建的预设（存数据库）、开发者代码注册的自定义 Agent（LangGraph StateGraph / deepagents 等）
- **展示名与内部名分离**：展示名可随意改，内部名唯一，用于委派与对外调用定位
- **委派开关**：`可被委派`（内部 task 委派白名单）与 `可对外作 MCP` 两个独立开关，配有默认委派介绍
- **通用子代理开关**：可开启继承父 Agent 配置的通用子代理
- **额外 Skill 目录与强校验**：支持额外 Skill 目录；开启项目模式必须配已存在的项目根目录
- **MCP 热更新**：MCP 连接状态变化时自动重建受影响的 Agent，无需重启服务

### 1.2 对话与流式
- **流式输出**：SSE 实时推送，支持文本 + 图片 + 文件内容多种内容块
- **非流式接口**：一次性返回（适合程序化调用）
- **自动标题生成**：用首条用户消息生成 ≤10 字会话标题
- **上下文摘要**：自动压缩超长对话（可配触发阈值和压缩策略），可指定独立摘要模型

### 1.3 子代理（Subagent）
- 顶层 Agent 通过 `task` 工具将子任务委派给专用子 Agent
- 支持同一轮并行发起多个子代理调用
- 深度限制（默认 2 层）+ 循环引用检测
- 可选通用子代理 `general-purpose`，继承父 Agent 配置

### 1.4 LLM 能力
- 支持任意 OpenAI 兼容 LLM 接口
- reasoning 模型（deepseek-reasoner、kimi-k2-thinking、GLM-5-Z1 等）思考内容捕获与前端折叠展示
- LLM 参数透传：temperature、reasoning_effort、top_p、max_tokens 等

### 1.5 认证
- JWT + bcrypt 多用户认证，角色分 admin / user
- 启动时自动创建初始 admin 用户
- 未配置 `auth.secret` 时认证关闭，以匿名 admin 身份运行（开发/单机场景）

### 1.6 长期记忆
- 跨会话记忆持久化（SQLite），按用户隔离
- Agent 通过内置记忆工具主动存取（增删改查 + 列举 + 搜索，共 6 个工具）
- 可配置语义检索（OpenAI 兼容 Embedding API）

### 1.7 权限与 HITL
- 工具白名单：管理员配置后，白名单内工具跳过审批
- HITL 拦截：非白名单工具调用弹出审批，所有用户可批准 / 拒绝；**管理员**可在审批时永久加白名单

### 1.8 HTTP 追踪
- 拦截 OpenAI 兼容路径的 LLM HTTP 请求/响应，持久化并在前端展示
- 敏感信息（API Key、token、密码等）自动脱敏
- 子代理独立追踪，互不干扰

### 1.9 代码注册 API
- 开发者可将任意 LangGraph StateGraph / deepagents Agent 注册到框架，作为内置 Agent 使用
- 框架提供带 HTTP 追踪的 LLM 工厂函数，代码注册的 Agent 也能获得追踪能力

---

## 2. 工具系统

### 2.1 工具组与权限过滤
- 工具按组（group）管理：`__builtin__`（系统信息，始终注入）、`file_read`、`file_write`、`command`、`utility`（时区查询等）
- Agent 预设可精确控制哪些工具组可用（三值语义：全部 / 全部禁用 / 指定组）
- 前端支持运行时开关工具组，无需重启

### 2.2 内置工具能力

#### 文件读取（`file_read` 组）
- 读取文件（支持行范围分页、图片 base64）
- 批量读取多个文件（单文件失败不影响整体）
- 递归列出目录结构
- 获取文件元数据（大小、修改时间、行数等）
- 基于 ripgrep 的文件名 / 内容搜索（正则匹配，AI 可动态控制结果数量）

#### 文件写入（`file_write` 组）
- 写文件（覆写 / 追加），自动创建父目录
- 创建目录
- 精确字符串替换：替换时前端实时渲染 **diff 预览**
- 整文件覆写时展示**内容预览**
- 移动 / 重命名文件或目录
- 删除单个文件（受 `allowed_directories` + 扩展名黑名单约束；目录删除走 `command` 组）

#### 命令执行（`command` 组）
- 一次性执行 shell 命令（Windows 默认 PowerShell，Linux/macOS 用 `$SHELL`）
- **实时流式输出**：命令运行中途 stdout 以"打字机"效果逐行推送到前端（ANSI 颜色支持）
- 启动后台进程：超时后返回 PID + 已收集输出，进程继续后台运行，前端展示 PID 和停止按钮
- 后台进程管理：读取输出、列出进程、终止进程
- 列出系统全部进程

> **流式打字机效果和 diff 预览是框架原生 Python 工具专属能力**。第三方 MCP 命令工具在 LangGraph 中是黑盒原子操作，无法中途推流，也无法渲染 diff。这是框架内置工具相比 MCP 工具的核心优势。

#### 安全边界
- `allowed_directories`：限制文件工具的读写目录范围
- `blocked_commands`：命令黑名单
- 写入扩展名黑名单（防止误写二进制文件）
- 相对路径自动解析到配置的项目根目录

---

## 3. 中间件（能力注入机制）

框架通过中间件向 Agent 注入额外工具和系统提示词。内置中间件能力：

- **Ask User**：Agent 在任务中途向用户发起多选 / 文字提问，等待回答后继续；支持单次多问题
- **当前时间注入**：每次对话自动注入当前日期和时区
- **自定义中间件 API**：开发者可将"工具包 + 系统提示词"封装为一个中间件，统一注入指定 Agent

---

## 4. MCP 集成

> **bfzs MCP 配置位置**：所有 MCP 在 `D:\codes\lc-agent-bfzs\config.jsonc` 的 `mcpServers` 字段配置，编辑后重启即生效，无需改框架代码。

### 连接与管理
- 三种连接类型：本地进程（stdio）、SSE 长连接、HTTP Streamable；有 `url` 时自动推断为 HTTP，SSE 需显式指定
- 持久化长连接，调用失败自动重连
- 启动时并行连接所有已配置 MCP
- 运行时刷新（单个 / 全部）、启停，无需重启服务
- MCP 状态变化时自动通知引擎重建受影响 Agent

### 项目级 MCP
- 项目模式下自动加载 `.agents/mcp.json`，同名 MCP 覆盖全局配置

### Agent 预设过滤
- Agent 预设可按 MCP 服务器名称过滤可用工具（三值语义）

### 作为 MCP Server 对外暴露（lcagent_as_mcp）
- 固定 2 个工具，不随 agent 数增长：`list_lca_agents`（agent 目录）+ `invoke_lca_agent`（按名委派，prompt 必须自包含）
- Agent 面板独立开关 `can_be_mcp`（与内部委派的 `can_be_subagent` 解耦，委派描述共用），勾选即显式授权其全部工具能力
- 外部 Agent（Claude Code / Cursor 等）连 `/mcp` 即发现调用，新增 agent 重连可见；调不存在的名字时报错里自带最新目录

---

## 5. Skills 系统

Skills 是 AI 可动态加载的指令工作流：每个 Skill 是一个目录下的 `SKILL.md` 文件，包含 AI 需要遵循的详细指令和工具用法。

### 核心能力
- **AI 按需加载**：Agent 判断 Skill 描述匹配当前任务时，自动加载完整指令
- **可执行脚本**：Skill 内可包含脚本，AI 通过 `skill__execute_script` 传入完整 shell 命令执行（工作目录为 Skill 目录）
- **资源读取**：AI 可读取 Skill 目录内的附属资源文件
- **运行时开关**：前端支持运行时单独启停每个 Skill，无需重启

### 工具
`skill__load_skill`、`skill__read_content`、`skill__execute_script` 注册给 Agent；`skill__list_skills` 不注册，Skill 清单由系统提示注入。

### 多层 Skills
- 全局 Skills：由 config.jsonc `skills` 字段指定的目录
- 项目级 Skills：项目模式下自动加载 `.agents/skills/`，同名 Skill 覆盖全局

### Agent 预设过滤
- Agent 预设可精确控制哪些 Skills 可用（三值语义）

### 框架内置 Skills
- **百度搜索**：关键词搜索 + 网页正文提取
- **codegraph**：结构性代码问题优先走结构检索而非 grep/read
- **create-skill**：Skill 脚手架与规范校验
- **extra-dirs-file-edit**：白名单外目录的文件读写
- **karpathy-guidelines**：防 LLM 编码坑的极简规范
- **vision-bridge**：无视觉模型时经外部视觉模型识图

---

## 6. 服务端（REST API + SSE）

基于 FastAPI 构建，内置 OpenAPI 文档（`/api/docs`）。

### 6.1 API 能力概览

| 能力域 | 功能 |
|--------|------|
| 会话管理 | 会话 CRUD、pin 置顶、标题更新、消息列表、HTTP 追踪查询 |
| 流式聊天 | SSE 流式对话、停止生成（cancel）、thread 状态查询（interrupt 检测） |
| Agent 预设 | 创建 / 编辑 / 删除 / 激活预设，查询可用子代理列表 |
| 工具管理 | 工具列表、工具组运行时开关、后台进程管理（列出 / 输出 / 终止） |
| MCP 管理 | 状态查询、运行时刷新（单个 / 全部）、启停 |
| Skills 管理 | 列表、运行时启停、资源读取 |
| 权限管理 | 工具白名单 CRUD（允许 / 移除 / 批量设置） |
| 认证 | 登录、当前用户、修改密码 |
| 管理员 | 用户 CRUD、密码重置、用户→Agent 访问控制 |
| 用量统计 | 多维聚合（用户/agent/模型/时间）、单价管理、CSV 导出、个人用量 |
| 自动化任务 | 任务 CRUD、暂停/恢复/立即执行/失败重跑、执行历史、通知目标管理与测试发送 |
| 文件变更 | 本会话文件变更聚合、按轮次 diff、Git Diff 多基准查询 |
| 项目文件 | 项目文件树/搜索/内容检索、文件读写（带保存冲突检测） |
| 提示词模板 | 模板 CRUD、Agent↔提示词绑定 |
| 摘要配置 | 运行时读取 / 更新摘要配置 |

### 6.2 流式聊天机制
- LangGraph SSE（Server-Sent Events）推流
- 支持多种内容块（文本、图片、文件内容）实时推送
- 子代理追踪事件（启动 / 完成 / 进度）
- 取消生成：前端发送 cancel 请求，流式 handler 轮询后发送 cancelled 事件
- 消息与 HTTP 追踪自动持久化

---

## 7. 数据库（持久化）

SQLite + SQLAlchemy 异步引擎，通过 Alembic 管理迁移。Checkpoint 默认 SQLite，检查点路径配为 PG 地址时切换为 PG 存储。

### 持久化内容

| 数据类型 | 说明 |
|---------|------|
| 会话与消息 | 会话元数据（标题 / pin / 子会话关联）+ 聊天消息（含 HTTP traces、token 用量）；多用户下会话按用户隔离（admin 看全部，user 仅看自己） |
| 自动化任务 | 任务配置（周期/时区/通知目标）+ 执行历史（含会话关联与推送状态） |
| 文件变更 | 每轮文件变更记录（含 diff 片段与行号） |
| Token 用量 | `llm_usage`（每次调用明细，含模型/用户/agent/角色）+ `model_pricing`（单价，带生效时间） |
| Agent 预设 | 完整预设配置（系统提示、工具权限、MCP、Skills、项目模式等） |
| 用户与权限 | 用户账号（admin / user 角色）+ 用户→Agent 访问控制 |
| 提示词模板 | 可复用提示词片段，支持绑定到 Agent 预设 |
| LangGraph Checkpoint | 对话历史完整状态快照，支持会话恢复和重试 |

---

## 8. 配置系统 (config/)

> **bfzs 实际配置文件**：`D:\codes\lc-agent-bfzs\config.jsonc`（包含真实的 LLM provider、mcpServers、skills、database 路径等）。框架自身的 `config.example.jsonc` 仅为参考模板。修改 bfzs 行为时，始终编辑 bfzs 目录下的 `config.jsonc`。

### 8.1 配置加载
[loader.py](file:///d:/codes/lc-agent/lc_agent/config/loader.py)

- JSONC 格式（支持 `//` 和 `/* */` 注释）
- 环境变量替换：`{env:ENV_VAR_NAME}` 语法
- `.env` 文件加载
- 相对路径解析（基于 `_project_root`）

### 8.2 可配置能力
[schema.py](file:///d:/codes/lc-agent/lc_agent/config/schema.py)

- **多 LLM 供应商**：任意 OpenAI 兼容接口，可同时注册多个供应商和模型，运行时切换
- **Agent 行为**：默认系统提示、流式输出、递归深度、子代理深度上限、自动摘要等
- **数据持久化**：SQLite 数据库 URL + LangGraph 检查点路径，可独立配置
- **长期记忆**：开关 + 存储路径 + 语义搜索配置
- **认证**：JWT secret + token 过期天数；未配置则以匿名 admin 运行
- **Skills 目录**：支持多目录扫描，可叠加框架内置与项目自定义 Skills
- **MCP 服务器**：字典式批量注册，支持 local（stdio）/ sse / http 三种连接类型，有 `url` 时自动推断，`sse` 需显式指定
- **对外 MCP**：`lcagent_as_mcp` 的启用开关与挂载路径
- **UI 定制**：应用名称等前端展示配置

### 8.3 MCP 服务器配置能力
- 三种连接类型：本地进程（stdio）、SSE 长连接、HTTP streamable
- 每个 MCP 支持独立 `enabled` 开关，无需删除配置即可停用
- 环境变量透传（`env` 字段），安全隔离凭证
- 可配置连接超时，适配不同网络环境

---

## 9. 内置提示词

框架内置一套工具使用规范提示词，在特定场景自动注入 Agent 系统消息：

- **工具组规范**：文件读写、命令执行的使用规范（含 Windows PowerShell 注意事项）；项目模式下按 Agent 已启用工具组自动注入对应规范
- **子代理工作规范**：task 工具使用规则（无状态单次往返、并行调用、何时使用 / 不使用）
- **Todo 任务分解**：引导 AI 将复杂任务拆解为有序 todo 列表并追踪完成状态，含滥用防护机制

开发者也可在 Agent 预设的系统提示中直接引用内置常量（如 `AGENT_GUIDELINES_PROMPT`）。

---

## 10. 前端 UI

基于 Vue 3 + Element Plus X 构建。

### 聊天界面
- 流式聊天：EPX BubbleList 实时渲染，支持文本 + 图片 + 文件内容
- 工具调用卡片：按改文件/写文件/终端/通用分卡展示，支持 diff 预览/内容预览/打字机输出
- 子代理卡片：子代理执行进度和结果，可点击进入该子代理的会话查看完整对话
- Todo 进度卡片：AI 任务分解和完成进度
- HITL 审批弹窗：工具调用审批（批准 / 拒绝；管理员可永久允许）
- AskUser 表单：单选/多选/自定义 Other/必填校验/跳过
- HTTP 追踪面板：完整 LLM 请求/响应展示（含脱敏）
- Token 用量面板：每条消息的 input / output token 统计（对话界面内）
- 用量统计页面：独立于对话界面，管理页（多维聚合 + 单价管理 + CSV 导出 + top 会话）与个人用量页（日期范围 + 按天/月 + 分组 + 缓存列）
- 错误富提示：失败原因 + 处理建议 + 技术详情

### 输入与操作
- 图片上传、文件附件（图片自动压缩），支持拖拽/粘贴
- `/` 唤起 Skill 选择器
- 消息编辑后重新生成
- 停止生成按钮，发送计时显示
- 输入框动画 4 种，Markdown 版式 10 种 + 配色 10 种
- Markdown 渲染 + 代码语法高亮
- 代码块全屏弹窗 + 一键复制
- 复制对话轮次为 Markdown：支持复制最近 N 轮（可选含思考/工具），单条复制回答/思考/工具
- 时间分隔线，思考块超长折叠

### 会话与布局
- 顶部会话标签栏：跨 Agent 全局单栏，右键/中键关闭，streaming/未读状态提示
- 多会话侧边栏：会话列表、pin 置顶、删除、标题编辑、按 Agent 分组折叠、分组分页、标题搜索
- 三栏可拖拽宽度并记忆，会话深链 `/c/:sessionId`，本地草稿会话，滚动与草稿按会话记忆
- 动态标题 + favicon
- 响应式布局（PC + 移动端抽屉）

### 项目文件与变更
- Chats/文件双视图（仅项目模式显示文件）
- 文件树：文件名/内容双搜，新建/重命名/删除，复制绝对/相对路径，分支显示
- 多标签编辑器：pin/恢复关闭/未保存圆点，面包屑，搜索计数，Markdown 预览，Word/Excel/PPT/PDF 只读预览，图片全屏放大，二进制/超大文件降级，保存冲突提示，复制 `路径#L行号` 引用
- 文件变更审查：本会话修改 vs Git Diff 双源，Unified/Side-by-side，按轮次筛选，按子 Agent 分组；Git 基准可切会话开始/HEAD/暂存区/指定提交；顶栏变更徽标 + 每轮变更卡片

### 右侧面板
- 5 个 Tab：模型/能力/变更/编辑器/任务，带 badge，可跨组件跳转
- 模型/预设切换、MCP 启停、Skills 启停、工具组启停、LLM 参数滑块（temperature 等）、模型覆盖标签 + 一键清除、摘要配置
- 工具/MCP/Skill 统一详情弹层

### 自动化与管理功能
- 自动化抽屉：任务列表 + 执行历史，新建/编辑/复制/删除，暂停/恢复/立即执行/失败重跑，周期单次/间隔/每天/每周，群通知多目标 + 测试发送 + 推送状态
- 后台进程管理面板：列出 Agent 启动的进程、查看输出、终止
- 数据清理：按保留天数预览，跳过置顶/活跃，二次确认，双库压缩
- Agent 预设管理器：新建 / 编辑 / 管理 / 提示词绑定 / 子代理配置 / 委派开关
- 工具白名单面板（HITL 权限管理）
- 登录 / 登出 + 管理员页（用户 CRUD、Agent 访问控制）
- 修改密码
- 主题切换（暗色 / 亮色）

---

## 11. 核心设计模式

### 11.1 三值语义（统一权限过滤）
工具组 / MCP 服务器 / Skills 的权限过滤使用统一的三值语义：
- `null`（None）：全部允许
- `[]`（空列表）：全部禁用（`__builtin__` 工具组始终例外）
- `["a", "b"]`：仅允许指定项

### 11.2 内置工具 vs MCP 工具
框架原生 Python 工具（`file_write` / `command` 组）可在函数执行中途推送自定义事件，实现：
- `edit_block` 的 diff 预览渲染
- 命令输出的流式打字机效果
- 后台进程的 PID / 停止按钮

MCP 工具在 LangGraph 中是原子操作（只有 start / end），不具备中途推流能力。**这是框架内置工具相比第三方 MCP 工具的核心优势。**

### 11.3 中间件自动注入顺序
框架在构建 Agent 时按以下顺序自动注入中间件（部分为条件注入）：

提示词绑定 → 项目上下文系列（项目模式下）→ 记忆（memory 启用时）→ Skills（有可见 Skill 时）→ 子代理提示词（有子代理注册表时）→ Todo（顶层）→ 摘要（默认开启）→ Ask User（顶层）→ 当前时间（始终）→ HITL（顶层）

---

## 12. 不内置的能力（需通过 MCP / Skills 扩展）

为避免恶意重复造轮子，以下能力**不在框架内置**，通过 MCP 或 Skills 集成：

### 12.1 ⭐ nbrag 知识库（作者亲手打造的 MCP）

[nbrag](https://github.com/ydf0509/nbrag) 是 lc-agent 作者**本人亲手开发**的 RAG 知识库 MCP 服务器，是 lc-agent 生态的首选知识检索方案。

- **定位**：作者亲手打造，与 lc-agent 同属一个生态
- **能力**：代码/文档向量化与混合检索（Vector + BM25 + grep），已将 LangChain/LangGraph/DeepAgents 官方源码与教程向量化到知识库 `langchain_ai_codes_and_docs`
- **部署**：支持 local（stdio）和 http 两种模式
- **配置示例**：
  ```jsonc
  "nbrag": { "type": "http", "url": "http://localhost:9101/mcp" }
  ```
- **与 lc-agent 长期记忆的关系**：memory 的语义搜索直接调用 OpenAI 兼容 embedding API（`BAAI/bge-m3`），与 nbrag MCP 调用路径独立，不依赖 nbrag 服务；仅是配置中复用了同一 API Key（`NBRAG_API_KEY`）

> nbrag 的具体工具列表、参数说明、使用规范由 nbrag 自身的工具描述和提示词负责，不在 lc-agent 文档范畴内。

### 12.2 强大的第三方 MCP 扩展能力

lc-agent 支持在 `config.jsonc` 的 `mcpServers` 字段接入任意第三方 MCP 服务器，无需修改框架代码，重启即可生效。例如 bfzs 演示项目就接入了以下 MCP，展示了框架扩展能力的广度：

- **联网搜索**：如 web-search（Open Web Search）、anysearch 等
- **LSP 代码工具**：如 serena（基于 LSP 的符号检索 / 导航 / 跨文件重构 / 代码编辑，支持 40+ 语言）
- **文档检索**：如 context7（实时拉取三方库文档）、docs-langchain、reference-langchain
- **RAG 知识库**：如 nbrag（自建知识库，已向量化 LangChain 生态源码与文档）

### 12.3关于联网能力
作者自己开发的逆向破解免费使用 百度搜索的skill，可以免费白嫖百度搜索引擎，用户勾选启用baidu-search 就可以使用联网功能；
用户也可以使用知名的 anysearch skill或者mcp来搜索。
禁止建议用户耗资几千亿美元开发搜索引擎技术。


## 13. 配置示例

- **框架示例配置**（用户参考模板）：[config.example.jsonc](file:///d:/codes/lc-agent/config.example.jsonc)，演示了 provider、agent、database、memory、skills、mcpServers 的配置方式（不含 auth，auth 走 schema 默认值）。
- **bfzs 演示项目实际配置**：`D:\codes\lc-agent-bfzs\config.jsonc`，包含 bfzs 实际使用的 LLM provider、所有已接入的第三方 MCP、Skills 路径、数据库路径等。**修改 bfzs 行为（如新增 MCP、切换模型）应编辑此文件**，而非框架示例文件。

---

