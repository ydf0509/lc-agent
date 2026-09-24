---
name: dev-guide
description: >-
  lc-agent 框架 和 lc-agent-bfzs 演示项目的开发指南。
  编写、修改、运行这两个项目代码时必须遵循此 Skill。
---

# 注意：
严格禁止ai自动修改此文件添加临时不重要的一次性细节。
未获用户明确要求，AI 不得修改本文件及 .agents/skills/ 下的任何 skill。


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
│   ├── filtered_loader.py  # LcAgentSkillLoader — 全局目录 + 项目 overlay + 运行时开关
│   └── skill_middleware.py # SkillsMiddleware 子类 + skills 系统提示词
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

## config.jsonc 中 model_id 和 raw_model_id区别

- `model_id` 是 给供应商+原始模型名字起的唯一别名名字，前端使用这个。
- `raw_model_id` 是 实际请求模型供应商http接口的模型ID，实际请求服务时候用的raw_model_id。

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
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class MyState(TypedDict):
    messages: Annotated[list, add_messages]
    # ... 其他状态字段

def build_my_agent():
    """构建自定义 Agent Graph：直接写代码，不读配置。"""
    from langchain_openai import ChatOpenAI  # 按需换自己的模型类
    llm = ChatOpenAI(model="...", api_key="...")  # 写死或读环境变量

    async def node_a(state: MyState) -> dict:
        resp = await llm.ainvoke(state["messages"])
        return {"messages": [AIMessage(content=resp.content)]}

    graph = StateGraph(MyState)
    graph.add_node("node_a", node_a)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", END)
    return graph.compile()
```

在 `bfzs/main.py` 注册:
```python
from bfzs.agents.my_agent import build_my_agent
app.add_agent(name="my_agent", graph=build_my_agent(), description="描述")
```

想复用 `config.jsonc` 里配好的模型时，用 `resolve_model(model_id)` 一行拿连接参数
（`raw_model_id` / `base_url` / `api_key` / `provider`），不用自己翻配置：
```python
from lc_agent import resolve_model
info = resolve_model("my-model-id")  # config 省略时自动用全局配置
llm = ChatOpenAI(model=info.raw_model_id, base_url=info.base_url, api_key=info.api_key)
```
（框架内部约定：`model_id` 只是前端别名，请求一律发 `raw_model_id`。）

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

- "测试通过"必须看到 `N passed` 汇总行才算数，exit 0 不算（曾有仓库根遗留 `pytest.py` 劫持 `python -m pytest`，只打印 5 行依赖检查就 exit 0）
- 仓库根严禁放与常用工具同名的 .py（pytest.py / conftest.py 等，会因 cwd 优先被当模块加载）
- 若 pytest 输出异常为空，先确认没有同名劫持文件；结果可 `--junitxml` 或落盘再读



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
from nb_langchain_agentskills import SkillsMiddleware
from lc_agent.skills.filtered_loader import LcAgentSkillLoader
```

## 8. 数据库

| 用途 | bfzs 路径 | 引擎 |
|------|-----------|------|
| 应用数据 (sessions, presets, messages) | `D:\codes\lc-agent-bfzs\bfzs_data.db` | async SQLite via SQLModel |
| LangGraph checkpoint | `D:\codes\lc-agent-bfzs\bfzs_checkpoints.db` | AsyncSqliteSaver |

- 无需手动迁移，启动时 Alembic 自动处理
- 项目可以破坏性修改 schema，无需兼容旧数据
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
| Skills 系统 | `SkillsMiddleware` | `nb_langchain_agentskills` |
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

## lc-agent 要支持的数据库
lc-agent分为langchain的checkpoint数据库和业务数据库。
checkpoint数据库要能支持sqlite postgre
业务数据库使用的sqlmodel，所以支持所有sqlachemy支持的数据库

## 前端开发规则
1. UI设计要美观华丽，各种UI设计的布局和颜色要符合业界通常的最佳实践设计。不能为了贪快，只实现功能不顾布局合理性和美感。
2. 按钮必须有彩色背景，禁止灰底/透明底。