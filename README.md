# lc-agent

基于 LangChain / LangGraph 的 AI Agent 框架，内置 Web UI。

**lc-agent 既是框架又是产品。** 用户可以在自己项目中 `import lc_agent` 开发自定义 Agent 应用；也可以零代码，直接在页面创建配置智能体。

> [lc-agent-bfzs](https://github.com/ydf0509/lc-agent-bfzs) 是基于 lc-agent 框架开发的演示项目。

## 定位

| 使用方式 | 类比 | 说明 |
|----------|------|------|
| 纯聊天 | DeepSeek / 豆包网页 | 配好 API Key 即可对话 |
| 接入 MCP & Skills | Codex / Claude Code / OpenCode | 无需改框架代码，配置即 Agent |
| 作为框架开发 | LangServe / Dify SDK | `import lc_agent` 注册自定义工具和 Agent |
| 可观测性 | LangSmith / LangFuse | 内置 HTTP 追踪、Token 统计、工具调用可视化 |

## 截图预览

**桌面端 — 对话 + MCP/Skills 面板**

![桌面端对话界面](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc01.png)

**可观测性 — HTTP 追踪 + Token 统计 + 工具调用**

![HTTP追踪与Token面板](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc02.png)



**工具调用详情 — 参数、返回值、思考过程**

![工具调用卡片](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc03.png)

**移动端适配**

![移动端界面](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/phone01.png)

**使用lc-agent框架的真实用户的案例截图**

ai agent 自动分解任务，并实时更新进度，并最终完成任务。

![用户真实案例](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/user_case.png)

## 安装

请注意安装包名字是`lc-agent-app`，不是`lc-agent`，因为`lc-agent`这个名字在pypi过不了审核。 

```bash
# 从 PyPI 安装
pip install lc-agent-app

# 或从源码开发安装，先从github ，git clone下来，然后打开项目根目录，执行以下命令
pip install -e .
```

## 截图


## 核心特性

### Agent 引擎
- 基于 `langchain.agents.create_agent` 构建 Agent（支持所有 LangChain 兼容 LLM）
- 三套内置预设：**Chat**（纯聊天）、**Empty**（全部工具默认关）、**Power**（全部工具默认开）
- 运行时热切换模型 / 工具 / MCP / Skills，无需重启
- 每次对话可临时覆盖模型（前端直接切换）
- 代码注册自定义 `CompiledStateGraph` Agent

### 任务进度追踪
- Agent 自动将复杂任务拆解为多个子步骤，实时追踪每步进度
- 基于 LangChain 官方 `TodoListMiddleware`，Agent 自主规划、自主更新
- 三态可视化：`pending` → `in_progress` → `completed`，带进度条
- 前端独立渲染任务卡片，不与工具调用混排，界面清晰不刷屏

### 可观测性（类 LangFuse）
- **HTTP 追踪**：自动捕获每轮 LLM 请求/响应全文，敏感信息自动脱敏
- **Token 面板**：每轮 input / output / cache_read / reasoning tokens 详细展示 + 累计汇总
- **工具调用卡片**：参数、返回值、耗时、运行状态一目了然
- **追踪持久化**：HTTP traces 存入数据库，历史会话可回放完整调试信息

### 工具 & Skills & MCP
- `@tool` 装饰器注册工具，支持分组 + 分组描述
- SKILL.md 技能扫描（遵循 agentskills.io 规范，支持 `metadata.group` 分组）
- MCP 服务器管理：支持 **stdio / SSE / Streamable HTTP** 三种传输方式
- MCP 自动重连（工具调用超时/异常时自动重连一次）
- MCP JSON Schema → LangChain StructuredTool 自动适配
- 三值权限控制：`null` = 全部允许，`[]` = 全部禁止，`["x","y"]` = 白名单
- 危险工具标记 + Human-in-the-loop 审批（LangGraph interrupt）

### 对话体验
- WebSocket 流式输出（thinking / 工具调用 / 回答实时交替渲染）
- 流式生成随时中断（真正取消，不是假停止）
- 消息编辑 & 重发（编辑历史消息，自动截断后续并重新生成）
- 自动生成会话标题（≤30字）
- 会话固定/分组/搜索/深度链接（`#/c/:sessionId`）

### Reasoning 思考过程
- 自定义 `ChatOpenAIReasoning` 类自动提取 `reasoning_content`
- 支持 DeepSeek / GLM / 任何返回 reasoning 字段的供应商
- 无需为每个供应商 import 不同 Chat Model 类

### Web UI
- **Vue 3 + TypeScript + Element Plus X**（AI 专用组件：BubbleList、XSender、Thinking）
- 明暗主题切换
- 完整移动端适配（抽屉式侧栏、触控手势、表格横滚+首列固定）
- Markdown 渲染 + 语法高亮 + 代码一键复制
- 丰富的复制工具（全部 / 仅思考 / 仅工具 / 仅回答 / 最近 N 轮）
- Agent 编辑器（页面创建/编辑预设，细粒度权限配置）
- Agent 来源标识（内置 / 代码 / 自建）

### 数据持久化
- 双存储模型：SQLModel（会话/预设/UI消息）+ LangGraph AsyncSqliteSaver（checkpoint）
- Alembic 自动迁移（启动时自动升级 schema）
- 会话历史完整保存（含思考、工具调用、HTTP追踪）

## 快速开始

### 作为独立聊天工具（无 tools）

```bash
cp config.example.jsonc config.jsonc
# 编辑 config.jsonc 配置 LLM provider
lc-agent
# 访问 http://127.0.0.1:8000
```

### 作为框架使用（在用户项目中）

```python
from lc_agent import LcAgentApp, load_config, tool

# 1. 注册自定义工具
@tool(group="my_tools", group_description="我的工具")
def my_tool(query: str) -> str:
    """工具描述"""
    return f"result: {query}"

# 2. 加载配置并启动
config = load_config(config_path="./config.jsonc")
app = LcAgentApp(config, host="127.0.0.1", port=8001)

# 3. 可选：注册自定义 CompiledGraph Agent
from my_agents import build_my_agent
app.add_agent("my_agent", build_my_agent(config), description="自定义Agent")

app.run() # 启动web服务，如果app.run(desktop=True) ，则同时启动一个桌面客户端，无需打开浏览器。
```

## CLI 参数

```bash
lc-agent [OPTIONS]

  -c, --config PATH      配置文件路径（默认搜索顺序见下方）
  -p, --port INT         监听端口（默认 8000）
  --host TEXT            绑定地址（默认 127.0.0.1）
  --dotenv PATH          指定 .env 文件路径
```

## 配置

使用 `config.jsonc`（支持注释 + `{env:VAR}` 环境变量替换 + `.env` 自动加载）：

**配置搜索顺序**：命令行 `-c` 指定 → `./config.jsonc` → `~/.lc_agent/config.jsonc` → 内置默认值

```jsonc
{
  "provider": {
    "litellm": {
      "api_key": "{env:LLM_API_KEY}",
      "base_url": "http://localhost:4000/v1",
      "models": [{"id": "deepseek-v4", "context_limit": 64000}]
    }
  },
  "agent": {
    "system_prompt": "你是一个有用的AI助手",
    "default_model": "deepseek-v4"
  },
  "database": {
    "url": "sqlite+aiosqlite:///./data.db",
    "checkpoint_path": "./checkpoints.db"
  },
  "skills": {"directory": "./myskills"},
  "mcp_servers": {}
}
```

## 工具注册

```python
from lc_agent import tool

@tool(group="file_ops", group_description="文件操作")
def read_file(path: str) -> str:
    """读取文件"""
    return open(path).read()
```

- `group`: ASCII 标识符（`^[a-zA-Z0-9_-]+$`），作为工具名前缀
- `group_description`: 人类可读的分组展示名（支持中文）
- 工具名格式: `{group}__{func_name}`

## Skills

放在配置的 `skills.directory` 下，遵循 agentskills.io 规范：

```
myskills/
└── my-skill/
    └── SKILL.md
```

SKILL.md 格式：

```yaml
---
name: my-skill
description: 技能描述
metadata:
  group: "技能组名"
---
# 技能内容（会注入到 Agent 系统提示词）
...
```

## API 概览

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 版本 + 配置状态 |
| `GET /api/models` | 可用模型列表 |
| `GET/POST /api/tools` | 工具列表 / 分组开关 |
| `GET/POST/PUT/DELETE /api/agents` | Agent 预设 CRUD + 激活 |
| `GET/POST/PUT/DELETE /api/sessions` | 会话 CRUD + 消息历史 |
| `GET/POST /api/skills` | Skills 列表 / 开关 |
| `GET/POST /api/mcp` | MCP 服务器状态 / 开关 |
| `WS /ws/chat[/{thread_id}]` | 流式对话 WebSocket |
| `GET /api/docs` | OpenAPI 文档 |

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | LangChain `create_agent` + `init_chat_model`（多提供商统一接入） |
| LLM 客户端 | `ChatOpenAIReasoning` — 自动提取 reasoning_content |
| 后端 | FastAPI + SQLModel + Alembic + asyncio |
| 前端 | Vue 3 + TypeScript + Element Plus X + Vite |
| 数据库 | SQLite（aiosqlite）+ LangGraph Checkpoint |
| 通信 | WebSocket（流式）+ REST API |

## 与 OpenWebUI 的区别

lc-agent 的下限是 OpenWebUI（内置 Chat 预设，配好 API Key 即可聊天），上限是 LangSmith + Dify（框架级开发调试）。

| 对比维度 | OpenWebUI | lc-agent |
|----------|-----------|----------|
| 纯聊天 | 支持 | 支持（内置 Chat 预设） |
| 多用户/团队/权限 | 支持 | 单用户（开发调试场景） |
| 内置 RAG 拖拽上传 | 支持 | 通过 nbrag MCP 实现（更强但需配置） |
| 多模态（TTS/语音/图片生成） | 支持 | 不做（非 Agent 开发核心需求） |
| HTTP 追踪（request/response 全文） | 无 | 内置，自动脱敏 |
| Token 逐轮统计（含 cache/reasoning） | 无 | 内置面板 |
| 工具调用可视化（入参/耗时/返回值） | 简单 | 详细卡片 + 全屏查看 + 搜索 |
| `import` 框架级使用 | 不支持 | 核心能力 |
| MCP 原生支持 | 不支持 | stdio/SSE/HTTP 三传输 |
| 代码注册自定义 Agent | 不支持 | `app.add_agent()` |
| 运行时热切换模型/工具/MCP | 部分 | 全部支持，无需重启 |
| LangChain 生态原生 | 不相关 | 原生集成 |

**总结**：不写代码只想聊天 → 两者都行；要开发/调试/部署 LangChain Agent → lc-agent。

## 快问快答



### lc-agent 能做什么？

- 当做 OpenWebUI / PrivateGPT 使用：配 API Key 聊天
- 当做 Codex / Claude Code 使用：配置 MCP 和 Skills 获得工具调用能力
- 当做 LangChain Agent 管理界面：热切换模型/工具/MCP，比改代码重启强得多

！！！注意： lc-agent 他不是最终的终极agent能力，它是一个框架，不是针对特定场景下的agent，自身不带一堆tools，用户可以导入框架，手写增加tools函数，也可以配置mcp skills。
lc-agent 她不是专门的coding agent，也不是专门的办公 aegnt，连最基本的文件读写能力都不提供，因为她是框架，要保持框架的纯净性。

### 比一般 LLM 网页聊天有什么优势？

可观测性。把工具调用入参/响应时间/返回内容可视化，每轮 tokens 消耗/缓存命中详细记录。效果接近 LangSmith / LangFuse，但零配置开箱即用。

### 有 RAG 知识库功能吗？

通过 [nbrag](https://github.com/ydf0509/nbrag) MCP 实现 Agentic RAG。lc-agent 不重复造轮子，nbrag 远超 Dify 和 OpenWebUI 内置的知识库检索能力。

### 内置的chat聊天agent能联网吗？

ai大模型自身不自带联网查询功能，你去买deepseek的api_key，也不会有自动联网功能。
要想联网，解决方式是配置一个现成的 `web search` 的mcp，这种mcp有几百个，有些是免费的。或者你牛逼自己python写爬取百度的函数，加上@tool装饰器 或者用skiils或者手写自定义mcp server就好了。


### 关于登录和多用户隔离？

lc-agent 目前不需要登录，没有支持多用户隔离，不是不愿意加上，是因为理念冲突，lc-agent没有限制agent不和用户本地机器有交互。lc-agent希望是万能的，不针对任何特定场景。**如果加上了多用户登录和隔离，而不提供云端容器，会让用户产生误解懵逼。**



主要原因是 lc-agent 没规定agent的行为是完全不碰用户本地机器，不读写用户自身电脑的文件，不执行用户电脑的脚本和命令，那agent作用大打折扣，此时你干脆去用豆包 deepseek gpt的官网网页就好了，网页版免费聊天还不要钱，不需要买apikey。

就像claudecode opencode codex 那样，每个用户需要亲自安装这个软件，会话只有用户自己知道，所以不需要登录和多用户隔离。
这个很容易懂吧？豆包 deepseek官网网页只是能聊天和搜新闻，她能读你本机项目的代码吗？能改你本机项目的代码吗？这写是caludecode和codex和cursor的事情。
如果你的agent偏向只搜互联网 只聊天 或者检索rag知识库，而绝不和用户自身电脑有交互关系，那你可以改造lc-aegnt加上登录和多用户隔离功能。

lc-agent 通过浏览器 使用agent能力，大部分时候不充当一个传统的bs架构，浏览器只是充当了 tui gui的渲染可视化作用，fastapi的web服务必须部署在需要被操作的机器上。
nb-agent 通过 tui 使用agent的能力 [https://github.com/ydf0509/nb_agent](https://github.com/ydf0509/nb_agent)。

#### 既然如此（不做多用户隔离），为什么要做成bs架构？
另外一个项目是 nb-agent是tui，也是本人项目。不通过浏览器提供agent操作，天然不会让用户有误解懵逼。
但是tui的天花板很低，tui通过终端字符渲染实现界面，难以实现复杂的ui交互，2025年tui吃香，2026年gui更吃香。
现在ai coding的tui太多了，只做tui类似小米的mimocode没有诚意，像codex zcode 这种gui才有诚意，所以codex客户端现在很吃香。
lc-agent 的浏览器相当于充当tui gui的作用 ，web开发比gui客户端的开发更灵活更轻，视觉渲染和交互天花板比tui和gui都更高，所以选择bs架构，不是cs架构。


当然还有一种方式通过浏览器，也可以提供高级agent能力，在container 里跑 agent，agent 有写权限但不是操作本机，那种玩法太高端了，类似traework qoder workbuddy的云端电脑能力。
不过没啥卵用那种云端容器，因为你如果不愿意付费，那么云端容器就不属于你自己所有，里面的文件随时被回收，因为这种玩法厂商成本太高了。你自己买台阿里云 腾讯云 linux云服务器，部署lc-agent，自己可以在浏览器输入linux服务器上部署的lc-agent的ip和端口，你在网页上让ai在linux服务器上操作各种文件的读写和命令的执行，里面ai生成的文件永远不会被回收，因为你付费买了阿里云服务器，你只要没欠费，阿里云就不敢删你的文件。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

### 前端开发

```bash
cd frontend
npm install
npm run dev      # 开发模式（热更新，代理到 :8000）
npm run build    # 构建到 lc_agent/web/dist/
```



## License

MIT
