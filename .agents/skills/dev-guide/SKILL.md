---
name: dev-guide
description: >-
  lc-agent 框架 和 lc-agent-bfzs 演示项目的开发指南。
  编写、修改、运行这两个项目代码时必须遵循此 Skill。
---

# 禁止行为
不要在代码里面写 `from __future__ import annotations` 

# lc-agent 开发指南

## 1. 项目关系

| 项目 | 路径 | 角色 | PyPI 包名 |
|------|------|------|-----------|
| **lc-agent** | `D:\codes\lc-agent` | 框架（被导入使用） | `lc-agent-app` |
| **lc-agent-bfzs** | `D:\codes\lc-agent-bfzs` | 基于框架的演示应用 | `lc-agent-bfzs` |

- lc-agent 提供：Web UI、Agent 引擎、MCP 管理、Skills 加载、工具注册、持久化、WebSocket 流式输出
- bfzs 只写业务逻辑：自定义工具、自定义 Agent Graph、Skills、配置

## 2. 环境

```
Python 解释器: D:\ProgramData\Miniconda3\envs\py312\python.exe
Node.js:       系统 PATH 中的 node/npm
Frontend:      D:\codes\lc-agent\frontend (Vue 3 + Vite)
bfzs 端口:    8001
lc-agent 默认: 8000
```

安装方式:
```powershell
# 框架需要可编辑安装
cd D:\codes\lc-agent && pip install -e ".[dev,desktop]"

# bfzs 是应用项目，不需要 pip install，直接 python 运行
# 入口: D:\codes\lc-agent-bfzs\bfzs\main.py
```

## 3. 目录结构

### lc-agent 框架

```
lc_agent/
├── __init__.py          # 公开 API: LcAgentApp, set_config_path, get_config, tool, ToolRegistry
├── app.py               # LcAgentApp 主编排器
├── main.py              # CLI 入口 (lc-agent 命令)
├── desktop.py           # pywebview 桌面客户端（独立启动）
├── config/
│   ├── loader.py        # JSONC 配置加载 + {env:VAR} 替换
│   ├── runtime.py       # 全局配置单例: set_config_path / get_config / get_app_name / get_database_url
│   ├── utils.py         # get_config_value 点路径读取 + 默认值常量
│   └── schema.py        # Pydantic 配置 schema
├── core/
│   ├── engine.py        # AgentEngine — create_agent + 预设 + 流式
│   ├── chat_model.py    # ChatOpenAIReasoning (提取 reasoning_content)
│   ├── models.py        # AgentPreset, ModelInfo 数据模型
│   └── http_trace*.py   # HTTP 请求追踪
├── tools/
│   ├── registry.py      # ToolRegistry 单例 + @tool 装饰器
│   └── builtin.py       # 内置工具（如有）
├── mcp/
│   ├── manager.py       # McpManager — 连接/管理 MCP 服务器
│   └── tool_adapter.py  # MCP schema → LangChain StructuredTool
├── skills/
│   ├── filtered_loader.py  # Skills 运行时开关（enable/disable）
│   └── scanner.py       # Skills 目录扫描
├── server/
│   ├── app.py           # FastAPI 工厂 + 静态文件挂载
│   ├── websocket.py     # ChatWebSocketHandler
│   ├── dependencies.py  # FastAPI DI
│   └── routes/          # REST API: health, models, tools, agents, sessions, skills, mcp
├── db/
│   ├── engine.py        # async SQLite + Alembic 自动迁移
│   ├── models.py        # SQLModel 表定义
│   ├── repository.py    # 数据访问层
│   └── migrations/      # Alembic 版本
└── web/dist/            # 前端构建产物（npm run build 输出）

frontend/                # Vue 3 前端源码
├── src/
│   ├── App.vue
│   ├── views/ChatView.vue         # 主聊天界面
│   ├── stores/                    # Pinia: chat, sessions, agents, tools
│   ├── api/                       # http.ts (REST), websocket.ts (WS)
│   ├── components/
│   │   ├── chat/                  # ToolCallCard, TokenUsage, HttpTrace, ChatBubble...
│   │   ├── layout/                # AppHeader, LeftSidebar, RightPanel
│   │   ├── panels/                # ToolGroupPanel, ModelSelector, TodoList
│   │   └── dialogs/               # AgentEditorDialog
│   └── router/index.ts
├── package.json
└── vite.config.ts                 # 代理 /api → :8000, /ws → ws://:8000 (开发bfzs需改8001)
```

### lc-agent-bfzs 演示应用

```
D:\codes\lc-agent-bfzs/
├── config.jsonc           # LLM、DB、MCP、Skills 配置
├── pyproject.toml         # 依赖: lc-agent
├── bfzs/
│   ├── main.py            # 入口: 加载配置→导入工具→创建App→注册Agent→run
│   ├── tools/
│   │   ├── file_tools.py  # [file_mgmt] 文件管理
│   │   └── data_tools.py  # [data_analysis] 数据分析
│   └── agents/
│       └── research_agent.py  # 自定义 LangGraph 研究助手
├── myskills/              # 自定义 SKILL.md 文件
├── bfzs_data.db           # SQLite 数据 (运行时生成)
└── bfzs_checkpoints.db    # LangGraph checkpoint (运行时生成)
```

## 4. 开发模式和常用操作

### 4.1 新增工具 (在 bfzs 项目)

```python
# bfzs/tools/my_new_tools.py
from lc_agent import tool

@tool(group="my_group", group_description="我的工具组显示名")
def my_function(param1: str, param2: int = 10) -> str:
    """工具的描述 — 会展示给 LLM 看，要写清楚用途和参数含义。

    Args:
        param1: 参数1说明
        param2: 参数2说明
    """
    # 业务逻辑
    return "结果字符串"
```

然后在 `bfzs/main.py` 中添加 import:
```python
import bfzs.tools.my_new_tools  # noqa: F401
```

**规则:**
- `group` 必须是 ASCII `^[a-zA-Z0-9_-]+$`
- `group_description` 写中文显示名
- 函数 docstring 是 LLM 看到的工具描述，务必清晰
- 工具名最终为 `{group}__{func_name}`

### 4.2 新增自定义 Agent (在 bfzs 项目)

```python
# bfzs/agents/my_agent.py
from typing import Annotated, TypedDict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class MyState(TypedDict):
    messages: Annotated[list, add_messages]
    # ... 其他状态字段

def build_my_agent(config: dict):
    """构建自定义 Agent Graph"""
    # 从 config 获取 LLM 配置
    provider_conf = list(config.get("provider", {}).values())[0]
    model_id = config.get("agent", {}).get("default_model", "")
    
    from lc_agent.core.chat_model import ChatOpenAIReasoning
    llm = ChatOpenAIReasoning(
        model=model_id,
        base_url=provider_conf.get("base_url", ""),
        api_key=provider_conf.get("api_key", ""),
        temperature=0.3,
        stream_usage=True,
    )

    async def node_a(state: MyState) -> dict:
        # ...
        return {"messages": [AIMessage(content="...")]}

    graph = StateGraph(MyState)
    graph.add_node("node_a", node_a)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", END)
    return graph.compile()
```

在 `bfzs/main.py` 注册:
```python
from lc_agent import get_config
from bfzs.agents.my_agent import build_my_agent
my_graph = build_my_agent(get_config())
app.add_agent(name="my_agent", graph=my_graph, description="描述")
```

### 4.3 修改框架核心 (在 lc-agent 项目)

常见修改点:
| 目标 | 文件 |
|------|------|
| 新增 REST API | `lc_agent/server/routes/` 新建文件定义 `router = APIRouter()`，然后在 `server/app.py` 中 import 并 `include_router` |
| 修改 WebSocket 协议 | `lc_agent/server/websocket.py` |
| 修改 Agent 构建逻辑 | `lc_agent/core/engine.py` |
| 新增数据库表 | `lc_agent/db/models.py` (启动时自动 Alembic 迁移) |
| 修改配置解析 | `lc_agent/config/loader.py` + `runtime.py` + `schema.py` |
| 修改 MCP 集成 | `lc_agent/mcp/manager.py` |

### 4.4 修改前端

```powershell
# 开发模式 (热更新)
# 注意: vite.config.ts 默认代理到 :8000，开发 bfzs 时需改为 :8001 或让 bfzs 监听 8000
cd D:\codes\lc-agent\frontend
npm run dev

# 构建 (输出到 lc_agent/web/dist/)
npm run build
```

前端要点:
- 路由: `src/router/index.ts` — hash 模式
- 状态: Pinia stores (`src/stores/`)
- API 调用: `src/api/http.ts` (REST), `src/api/websocket.ts` (WS)
- UI 库: Element Plus + vue-element-plus-x (AI chat 组件)
- 聊天气泡: `BubbleList` 来自 vue-element-plus-x

### 4.5 新增前端组件

```
frontend/src/components/
├── chat/        # 聊天相关 (消息气泡内的元素)
├── layout/      # 布局 (Header, Sidebar)
├── panels/      # 面板 (工具列表, 模型选择)
└── dialogs/     # 对话框
```

## 5. 运行项目

### 启动 bfzs (常规方式)

```powershell
cd D:\codes\lc-agent-bfzs
D:\ProgramData\Miniconda3\envs\py312\python.exe -u -m bfzs.main --port 8001
```

### 使用 restart-bfzs skill (推荐)

当修改了前端或后端代码后，使用 `restart-bfzs` skill 来重建前端并重启服务。

### 仅编译前端 (不重启 Python)

```powershell
cd D:\codes\lc-agent\frontend && npm run build
```

### 运行测试

```powershell
cd D:\codes\lc-agent
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/ -v
```

## 6. 关键设计模式

### 6.1 工具注册 — 导入即注册

```python
# ToolRegistry 是单例，@tool 装饰器在模块导入时自动注册
# bfzs 只需 import 模块，工具就进入全局注册表
import bfzs.tools.file_tools  # 导入 = 注册
```

### 6.2 配置驱动

所有 LLM、MCP、Skills 配置都在 `config.jsonc`，支持:
- JSONC 注释
- `{env:VAR}` 环境变量替换
- `.env` 文件加载

**全局配置单例：** 应用入口调用一次 `set_config_path()` 注册配置路径（写入 `LC_AGENT_CONFIG_PATH` 环境变量并失效缓存），之后框架内任何地方用 `get_config()` 无参获取同一份配置（同一 dict 引用，运行时修改立即生效）；`get_app_name()` / `get_database_url()` 是高频字段的快捷 getter。找不到任何配置文件时 `load_config` 直接 raise RuntimeError（CLI 入口会打印错误并退出），不再回退到内置默认空壳配置。

**重要：** 修改或新增配置项时，必须同时更新以下两个文件：
1. `D:\codes\lc-agent\config.example.jsonc` — 框架示例配置，用户复制的唯一参考
2. `D:\codes\lc-agent-bfzs\config.jsonc` — 演示项目的实际配置

改了一个漏了另一个会导致不一致。字段重命名、删除、新增都要两边同步。

**模型字段命名规范：** 如果该模型可以在网页 UI 中动态切换/覆盖，配置中应命名为 `default_model`（表示"默认值，可被用户在运行时覆盖"）。
例如 `agent.default_model`、`agent.summarization.default_model` 都可以在右侧面板修改，所以叫 `default_model`。

### 6.3 三值权限过滤

Agent Preset 的 `allowed_tool_groups` / `allowed_mcp_servers` / `allowed_skills`:
- `None` = 全部允许
- `[]` = 全部禁止
- `["a", "b"]` = 只允许指定的

### 6.4 Agent 的三种创建方式

| 方式 | 来源 | 存储 | 构建逻辑 | Middleware |
|------|------|------|----------|-----------|
| **内置预设** | 框架代码 | 无需存储 | `engine.build_agent()` | 框架自动添加 |
| **用户网页创建** | Web UI 编辑 | SQLite `agent_presets` 表 | `engine.build_agent()` | 框架自动添加 |
| **用户代码创建** | Python 代码 | 无（内存） | 用户自己构建 graph | **用户完全控制** |

#### 内置预设（硬编码在框架中）

| ID | display_name | 行为 |
|----|--------------|------|
| `chat` | 普通对话 | 纯聊天，无工具 |
| `empty` | 空模板 | 默认不启用工具 |
| `power` | 全功能 | 默认启用所有工具 |

#### 用户网页创建的预设

用户在 Web UI 中创建/编辑的 Agent Preset，存入 SQLite 数据库。
启动时从 DB 加载，走 `build_agent()` 创建，享有框架自动添加的 middleware。

#### 用户代码创建的 Agent

通过 `app.add_agent(name, graph, description)` 注册自定义 LangGraph：
```python
app.add_agent(name="my_agent", graph=my_compiled_graph, description="描述")
```
- graph 可以来自 `create_agent`、`create_deep_agent`、或手动 `StateGraph().compile()`
- 框架**不会**往用户 graph 里添加任何 middleware
- 用户需要自行管理上下文裁剪、工具、权限等

### 6.5 Middleware 作用范围

框架的 `build_agent()` 会自动为内置/网页创建的 preset 添加 middleware（TodoListMiddleware、SummarizationMiddleware 等）。
**但 `app.add_agent(name, graph)` 注册的用户自定义 graph 不受影响** — 框架不会往用户的 graph 里插入任何 middleware。

用户如果想给自己的 agent 加上下文裁剪，需要自行在构建 graph 时配置 middleware（如 deepagents 的 SummarizationMiddleware 或 langchain 的 SummarizationMiddleware）。

### 6.6 流式输出 WebSocket 协议

客户端发送:
```json
{"type": "message", "content": "用户消息", "preset_id": "power", "model": "ds-deepseek-v4-flash"}
{"type": "cancel"}
{"type": "interrupt_response", "approved": true, "preset_id": "power"}
```

服务端流式返回:
```json
{"type": "connected", "thread_id": "..."}
{"type": "token", "content": "..."}
{"type": "thinking", "content": "..."}
{"type": "tool_call", "name": "...", "run_id": "...", "args": {...}}
{"type": "tool_result", "name": "...", "result": "..."}
{"type": "content", "content": "\n<!--HTTP:0-->\n"}
{"type": "llm_usage", "input_tokens": 0, "output_tokens": 0, ...}
{"type": "interrupt", "message": "Tool requires approval", "data": {...}}
{"type": "title_update", "thread_id": "...", "title": "..."}
{"type": "done", "usage": [...], "http_traces": [...]}
{"type": "cancelled"}
{"type": "error", "message": "..."}
```

## 7. LangChain/LangGraph 代码规范

**重要：** 写 LangChain 相关代码时：
1. 禁止使用 AI 预训练的过时语法，要使用2026年最新的语法。
2. 必须用 `docs-langchain` 和 `reference-langchain` MCP 查询最新用法
3. 如有必要，用 `nbrag` MCP 搜索 `langchain_ai_codes_and_docs` 知识库
4. 可以直接读 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 下的源码

### 当前版本关键 API

```python
# Agent 创建 (langchain >= 1.0)
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware

# LangGraph (>= 0.4)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Chat Model
from lc_agent.core.chat_model import ChatOpenAIReasoning

# Skills
from langchain_agentskills import SkillsToolkit
from langchain_agentskills.loaders import DirectorySkillLoader, CompositeSkillLoader
```

## 8. 数据库

| 用途 | bfzs 路径 | 引擎 |
|------|-----------|------|
| 应用数据 (sessions, presets, messages) | `D:\codes\lc-agent-bfzs\bfzs_data.db` | async SQLite via SQLModel |
| LangGraph checkpoint | `D:\codes\lc-agent-bfzs\bfzs_checkpoints.db` | AsyncSqliteSaver |

- 无需手动迁移，启动时 Alembic 自动处理
- 项目处于早期开发阶段，可以破坏性修改 schema，无需兼容旧数据
- 如 schema 改动大，可以删除 .db 文件重新启动。**但必须先询问用户确认！** 数据库中存有用户配置的 Agent preset，删库意味着丢失所有配置，重建很麻烦

### 8.2 数据库旧表加字段时候的注意事项

给已有表新增字段时，**必须写正式 Alembic revision**，同时改 SQLModel 表定义，两者缺一不可：

1. `lc_agent/db/models.py` — 修改表模型加字段（Python 侧）
2. `lc_agent/db/migrations/versions/` — 新建 revision 文件，`down_revision` 指向当前 head
3. NOT NULL 新列必须带 `server_default`；模型侧空串默认值写 `server_default=text("''")`（纯 `""` 会被兜底补列逻辑拼出非法 DDL）
4. 验证：跑覆盖该表的测试即可（fixture 在全新库上执行完整迁移链）

`_add_missing_columns` 只是启动时的幂等兜底，不能替代正式 revision。

## 9. 常见陷阱

1. **别在框架里写业务逻辑** — 工具、Agent、Skills 都应该在 bfzs 项目中
2. **前端修改后要 build** — `npm run build` 输出到 `lc_agent/web/dist/`，否则后端静态文件还是旧的
3. **Python 解释器** — 必须用 `D:\ProgramData\Miniconda3\envs\py312\python.exe`
4. **bfzs 工作目录** — 启动 bfzs 时 cwd 必须是 `D:\codes\lc-agent-bfzs`（因为 config.jsonc 中的相对路径基于此）
5. **MCP 服务器** — 类型分 `local`(subprocess)、`sse`、`http`(streamable HTTP)
6. **LiteLLM** — bfzs 通过 LiteLLM 代理访问各家 LLM，默认 `http://localhost:4000/v1`
7. **新增功能前先查生态** — 见下方"架构原则"
8. **禁止在 Python 文件顶部写 `from __future__ import annotations`** — 此语句会把当前模块所有函数注解变为惰性字符串，LangChain 的 `@tool` / `@lc_tool` 装饰器在构建 Pydantic schema 时调用 `get_type_hints()`，会在全局作用域解析注解字符串，导致函数内局部变量（如动态生成的 `Field(description=...)` 引用）报 `NameError`。Python 3.12 无需此语句，项目内已有该语句的文件可以直接删除。

## 10. 架构原则：优先复用 LangChain 生态

**新增功能时，必须优先检查 langchain/langgraph/deepagents 生态是否已有现成实现，而不是手动从零造轮子。**

已有的成功案例：
| 功能 | 来源（非自研） | 包 |
|------|---------------|-----|
| Agent 创建 | `create_agent` | `langchain` |
| TodoList | `TodoListMiddleware` | `langchain.agents.middleware` |
| 上下文摘要 | `SummarizationMiddleware` | `langchain.agents.middleware` |
| Skills 系统 | `SkillsToolkit` | `langchain_agentskills` |
| Checkpoint | `AsyncSqliteSaver` | `langgraph` |

**查找顺序：**
1. `langchain.agents.middleware` — 有没有现成 middleware？
2. `langgraph` — 有没有内置能力（如 interrupt、checkpoint）？
3. `deepagents` — 有没有增强实现（如 SummarizationMiddleware + backend offload）？
4. `langchain_core` / `langchain_community` — 有没有工具类可用？
5. 以上都没有 → 才自己实现

**检查方法：**
- 用 `docs-langchain` / `reference-langchain` MCP 搜索
- 用 `nbrag` MCP 搜索 `langchain_ai_codes_and_docs` 知识库
- 直接读 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 下的源码

## 11. 快速参考: 公开 API

```python
from lc_agent import LcAgentApp, set_config_path, get_config, tool, ToolRegistry

# 框架入口（推荐：注册一次，全局无参取配置）
set_config_path("./config.jsonc")
app = LcAgentApp(host="127.0.0.1", port=8001)
app.add_agent(name, graph, description)
app.run()

# 任何地方无参获取配置（路由、工具、自定义 Agent 内部）
from lc_agent import get_app_name, get_database_url
from lc_agent.config import get_config_value
config = get_config()
app_name = get_app_name()
db_url = get_database_url()
value = get_config_value(config, "agent.default_model", "")  # 点路径读取

# 兼容写法：显式加载并传 dict（会同步注册为全局）
from lc_agent import load_config
config = load_config(config_path="./config.jsonc")
app = LcAgentApp(config, host="127.0.0.1", port=8001)

# 工具注册
@tool(group="ascii_group_name", group_description="中文显示名")
def func(arg: str) -> str:
    """docstring 是 LLM 看到的描述"""
    return "result"
```
