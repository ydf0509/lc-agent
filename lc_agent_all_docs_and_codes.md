
# 🤖 AI 上下文阅读协议 (由 nb_ai_context 生成)

> **此文档生成时间**：2026-06-14 21:14:30
> **系统指令**：你正在解析一份由工具 **`nb_ai_context`** 自动生成的**结构化项目快照**。
> **文档性质**：这**不是**一份普通的面向人类的文档，而是专为 AI 大模型（LLM）设计的上下文数据流。它将项目文档、源代码和 AST 架构元数据进行了特殊的结构化合并，请开启"代码解析器"的心智模式。


## 🧠 AI 认知与解析准则

这份由 `nb_ai_context` 生成的文档是你的核心知识库。其中的内容是动态的——它可能包含完整的底层源码，也可能仅包含使用教程，或者是两者的混合。请严格遵循以下自适应阅读策略：

### 1. 信息的层级与冲突处理
*   **文档即意图**：将 `README`、教程文档和 Docstrings 视为项目设计的**最高意图**。如果生成器省略了对应源码，请完全信任文档逻辑，以此为基础推理。
*   **源码即事实**：遇到 `.py` 源码或 AST 元数据（类/函数签名）时，以此作为实现细节、类型约束和语法准确性的**最终事实标准**。
*   **冲突处理**：若文档与源码/AST 存在矛盾，请以源码为准，并在回答中向用户简要指出该差异。
*   **测试代码的忽略**：为优化 Token 长度，集成/单元测试及非核心 API 源码通常被隐藏。**绝对不要**因此推断或提醒用户“项目缺乏测试”或“代码未实现”。

### 2. 文件边界与架构感知
*   **上下文定界**：工具使用 `--- **start of file: <路径>** ---` 等标记严格界定文件。**在你的回复中，请使用标准 Markdown 代码块，切勿模仿使用此类系统定界符。**
*   **结构可视化**：利用“文件树 (File Tree)”章节建立项目的宏观架构认知。
*   **依赖关系**：利用“文件依赖分析”章节理清模块间的 import 数据流向。

### 3. 严格的代码生成与交互边界
*   **事实锚定 (Fact Anchoring)**：你生成的代码必须严格锚定在本文档范围内！API 调用必须基于**源码中的 AST 签名**或**文档中的演示示例**。
*   **严禁臆造 (Zero Fabrication)**：绝对禁止编造文档中未定义或未提及的类名、方法名或参数。
*   **越界拒绝**：如果用户询问的功能在当前提供的上下文中完全不存在，请明确告知“当前上下文中未包含该信息”，而不是试图凭空生成。

---
# markdown content namespace: lc_agent project summary 



- `lc-agent` 是基于 LangChain / LangGraph 的 AI Agent Web 应用框架。
- 提供 WebSocket 流式对话、工具调用、MCP 集成、Skill 系统、多 Agent Preset 管理等能力。
- 前端使用 Vue 3 + Element Plus + Vite，后端使用 FastAPI + LangGraph。
- 核心模块：
  - `lc_agent/app.py`: LcAgentApp — 应用编排入口，创建引擎、注册路由、启动服务
  - `lc_agent/core/engine.py`: AgentEngine — 核心引擎，管理 Agent 实例、Preset、工具组
  - `lc_agent/server/websocket.py`: ChatWebSocketHandler — WebSocket 流式事件转发
  - `lc_agent/mcp/manager.py`: McpManager — MCP 服务连接管理
  - `lc_agent/tools/registry.py`: ToolRegistry — 工具注册表
  - `lc_agent/skills/scanner.py`: SkillScanner — Skill 扫描与匹配
  - `lc_agent/db/`: SQLAlchemy 异步数据持久化
  - `frontend/src/`: Vue 3 前端界面
- 用户用法：`from lc_agent import LcAgentApp, load_config`


## 📋 lc_agent most core source files metadata (Entry Points)


以下是项目 lc_agent 最核心的入口文件的结构化元数据，帮助快速理解项目架构：



### the project lc_agent most core source code files as follows: 
- `lc_agent/__init__.py`
- `lc_agent/app.py`
- `lc_agent/core/engine.py`
- `lc_agent/server/websocket.py`
- `lc_agent/mcp/manager.py`
- `lc_agent/tools/registry.py`


### 📄 Python File Metadata: `lc_agent/__init__.py`

#### 📝 Module Docstring

`````
lc_agent — LangChain Agent framework with built-in Web UI.
`````

#### 📦 Imports

- `from lc_agent.app import LcAgentApp`
- `from lc_agent.config.loader import load_config`
- `from lc_agent.tools.registry import ToolRegistry`
- `from lc_agent.tools.registry import tool`


---




### 📄 Python File Metadata: `lc_agent/app.py`

#### 📦 Imports

- `from __future__ import annotations`
- `from contextlib import asynccontextmanager`
- `import uvicorn`
- `from fastapi import FastAPI`
- `from fastapi import WebSocket`
- `from fastapi import WebSocketDisconnect`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.db.engine import init_db`
- `from lc_agent.server.app import create_app`
- `from lc_agent.server.app import mount_static_files`
- `from lc_agent.server.websocket import ChatWebSocketHandler`
- `from lc_agent.skills.scanner import SkillScanner`
- `from lc_agent.mcp.manager import McpManager`
- `import asyncio`
- `import asyncio`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.models import AgentPresetDB`
- `from lc_agent.core.models import AgentPreset`
- `from sqlalchemy import select`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent import __version__`
- `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`
- `import aiosqlite`

#### 🏛️ Classes (1)

##### 📌 `class LcAgentApp`
*Line: 15*

**Docstring:**
`````
Main application orchestrator — creates engine, server, and runs.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict, host: str = '127.0.0.1', port: int = 8000)`
  - **Parameters:**
    - `self`
    - `config: dict`
    - `host: str = '127.0.0.1'`
    - `port: int = 8000`

**Public Methods (2):**
- `def add_agent(self, name: str, graph, description: str = '')`
  - **Docstring:**
  `````
  Register a pre-built CompiledStateGraph as a named agent.
  
  Args:
      name: Unique agent identifier
      graph: A compiled LangGraph (must have ainvoke and astream_events)
      description: Human-readable description
  `````
- `def run(self)`
  - *Start the server (blocking).*


---




### 📄 Python File Metadata: `lc_agent/core/engine.py`

#### 📦 Imports

- `from __future__ import annotations`
- `from typing import Any`
- `from typing import AsyncIterator`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent.core.models import ModelInfo`
- `from lc_agent.tools.registry import ToolRegistry`
- `from langchain.agents import create_agent`
- `from langchain.chat_models import init_chat_model`
- `from lc_agent.core.chat_model import ChatOpenAIReasoning`

#### 🏛️ Classes (1)

##### 📌 `class AgentEngine`
*Line: 10*

**Docstring:**
`````
Core agent engine wrapping langchain.agents.create_agent with middleware support.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict, checkpointer = None)`
  - **Parameters:**
    - `self`
    - `config: dict`
    - `checkpointer = None`

**Public Methods (11):**
- `def get_models(self) -> list[ModelInfo]`
  - *Return available models.*
- `def get_builtin_presets(self) -> list[AgentPreset]`
  - *Return the three built-in agent presets.*
- `def get_default_preset(self) -> AgentPreset`
  - *Return the default agent (Chat - safest).*
- `def build_agent(self, preset: AgentPreset | None = None)`
  - *Build a LangGraph ReAct agent from preset.*
- `async def chat(self, message: str, thread_id: str, preset_id: str = '__chat__') -> str`
  - *Send a message and get a response (non-streaming).*
- `async def chat_stream(self, message: str, thread_id: str, preset_id: str = '__chat__') -> AsyncIterator[dict]`
  - *Stream chat responses as events.*
- `async def generate_title(self, user_message: str, model_id: str = '') -> str`
  - *Generate a short conversation title from the user's first message.*
- `def get_presets(self) -> list[AgentPreset]`
  - *Return all agent presets (including default and custom).*
- `def add_preset(self, preset: AgentPreset) -> AgentPreset`
  - *Add a new agent preset.*
- `def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None`
  - *Update an existing preset.*
- `def delete_preset(self, preset_id: str) -> bool`
  - *Delete a preset. Cannot delete builtin.*

**Class Variables (1):**
- `BUILTIN_IDS = {'__chat__', '__empty__', '__power__'}`


---




### 📄 Python File Metadata: `lc_agent/server/websocket.py`

#### 📦 Imports

- `import asyncio`
- `import uuid`
- `from typing import Any`
- `from fastapi import WebSocket`
- `from lc_agent.core.engine import AgentEngine`
- `import time`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.repository import SessionRepository`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.repository import SessionRepository`
- `from langgraph.types import Command`

#### 🏛️ Classes (1)

##### 📌 `class ChatWebSocketHandler`
*Line: 11*

**Docstring:**
`````
Handles WebSocket connections for streaming chat.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, engine: AgentEngine)`
  - **Parameters:**
    - `self`
    - `engine: AgentEngine`

**Public Methods (3):**
- `async def connect(self, websocket: WebSocket, thread_id: str | None = None) -> str`
  - *Accept WebSocket connection.*
- `async def disconnect(self, thread_id: str)`
  - *Clean up on disconnect.*
- `async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict)`
  - *Process incoming message and stream response.*


---




### 📄 Python File Metadata: `lc_agent/mcp/manager.py`

#### 📦 Imports

- `from __future__ import annotations`
- `import asyncio`
- `import os`
- `from dataclasses import dataclass`
- `from dataclasses import field`
- `from typing import Any`
- `from mcp import ClientSession`
- `from mcp import StdioServerParameters`
- `from mcp.client.stdio import stdio_client`
- `from mcp import ClientSession`
- `from mcp.client.sse import sse_client`
- `from mcp import ClientSession`
- `from mcp.client.streamable_http import streamable_http_client`
- `from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas`
- `from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas`

#### 🏛️ Classes (2)

##### 📌 `class McpServerStatus`
*Line: 10*

**Class Variables (9):**
- `name: str`
- `type: str = 'local'`
- `command: str = ''`
- `url: str = ''`
- `enabled: bool = True`
- `status: str = 'disconnected'`
- `tools: list[str] = field(default_factory=list)`
- `tool_schemas: list[dict] = field(default_factory=list)`
- `error: str | None = None`

##### 📌 `class McpManager`
*Line: 22*

**Docstring:**
`````
Manages persistent MCP server connections and tool invocation.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict[str, dict])`
  - **Parameters:**
    - `self`
    - `config: dict[str, dict]`

**Public Methods (7):**
- `def get_server(self, name: str) -> McpServerStatus | None`
- `async def connect_all(self)`
  - *Connect to all configured MCP servers (persistent).*
- `async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str`
  - *Invoke a tool on a connected MCP server (serialized per server).*
- `def get_tools_for_server(self, server_name: str) -> list[str]`
  - *Get tool names for a given server.*
- `def get_langchain_tools(self) -> list`
  - *Get all connected MCP tools as LangChain StructuredTools.*
- `def get_filtered_langchain_tools(self, allowed_servers: list[str] | None) -> list`
  - *Get MCP tools filtered by allowed servers (three-value semantics).*
- `async def shutdown(self)`
  - *Clean up all persistent connections.*

**Properties (1):**
- `@property servers -> list[McpServerStatus]`


---




### 📄 Python File Metadata: `lc_agent/tools/registry.py`

#### 📦 Imports

- `from __future__ import annotations`
- `import functools`
- `import re`
- `from typing import Any`
- `from typing import Callable`
- `from typing import overload`
- `from langchain_core.tools import BaseTool`
- `from langchain_core.tools import StructuredTool`

#### 🏛️ Classes (1)

##### 📌 `class ToolRegistry`
*Line: 13*

**Docstring:**
`````
Central registry for all tools, supporting groups and filtering.
`````

**Public Methods (6):**
- `def get_all_tools(self) -> list[BaseTool]`
  - *Return all registered tools as LangChain BaseTool instances.*
- `def get_tools_by_groups(self, groups: list[str]) -> list[BaseTool]`
  - *Return tools belonging to specified groups.*
- `def get_filtered_tools(self, allowed_groups: list[str] | None) -> list[BaseTool]`
  - **Docstring:**
  `````
  Filter tools by allowed groups (three-value semantics).
  
  None = all allowed, [] = none allowed, ["a","b"] = only those groups.
  Also excludes runtime-disabled groups.
  `````
- `def get_group_names(self) -> list[str]`
  - *Return unique list of all registered group names.*
- `def get_group_info(self) -> list[dict[str, str]]`
  - *Return group id + description pairs.*
- `def register(self, func: Callable, group: str = '', group_description: str = '') -> BaseTool`
  - **Docstring:**
  `````
  Register a function as a tool.
  
  Args:
      func: The function to register as a tool.
      group: ASCII group identifier, used as prefix in tool name.
             Must match ^[a-zA-Z0-9_-]+$ if provided.
      group_description: Human-readable group description for UI display.
             If not provided, defaults to the group value.
  `````

**Class Variables (4):**
- `_instance: ToolRegistry | None = None`
- `_global_tools: dict[str, dict[str, Any]] = {}`
- `_group_descriptions: dict[str, str] = {}`
- `_disabled_groups: set[str] = set()`

#### 🔧 Public Functions (5)

- `def tool(func: Callable) -> Callable` `overload`
  - *Line: 109*

- `def tool() -> Callable[[Callable], Callable]` `overload`
  - *Line: 113*

- `def tool(func: Callable | None = None)`
  - *Line: 116*
  - **Docstring:**
  `````
  Decorator to register a function as an agent tool.
  
  Usage:
      @tool
      def my_func(...): ...
  
      @tool(group="file_mgmt", group_description="文件管理")
      def my_func(...): ...
  `````

- `def decorator(fn: Callable) -> Callable`
  - *Line: 128*

- `def wrapper(*args, **kwargs)` `functools.wraps(fn)`
  - *Line: 132*


---



## 🔗 lc_agent Some File Dependencies Analysis

以下是项目文件之间的依赖关系，帮助 AI 理解代码结构：

### 📊 Internal Dependencies Graph

`````
Core Files (imported by other files, sorted by import count):
  ◆ lc_agent/__init__.py (imported by 4 files)
  ◆ lc_agent/core/engine.py (imported by 2 files)
  ◆ lc_agent/tools/registry.py (imported by 2 files)
  ◆ lc_agent/app.py (imported by 1 files)
  ◆ lc_agent/server/websocket.py (imported by 1 files)
  ◆ lc_agent/mcp/manager.py (imported by 1 files)

`````

### 📋 Detailed Dependencies

#### `lc_agent/__init__.py`

**Imports from project:**
- `lc_agent/app.py`
- `lc_agent/tools/registry.py`

**Imported by:**
- `lc_agent/app.py`
- `lc_agent/core/engine.py`
- `lc_agent/mcp/manager.py`
- `lc_agent/server/websocket.py`

#### `lc_agent/app.py`

**Imports from project:**
- `lc_agent/__init__.py`
- `lc_agent/core/engine.py`
- `lc_agent/mcp/manager.py`
- `lc_agent/server/websocket.py`

**Imported by:**
- `lc_agent/__init__.py`

#### `lc_agent/core/engine.py`

**Imports from project:**
- `lc_agent/__init__.py`
- `lc_agent/tools/registry.py`

**Imported by:**
- `lc_agent/app.py`
- `lc_agent/server/websocket.py`

#### `lc_agent/mcp/manager.py`

**Imports from project:**
- `lc_agent/__init__.py`

**Imported by:**
- `lc_agent/app.py`

#### `lc_agent/server/websocket.py`

**Imports from project:**
- `lc_agent/__init__.py`
- `lc_agent/core/engine.py`

**Imported by:**
- `lc_agent/app.py`

#### `lc_agent/tools/registry.py`

**Imported by:**
- `lc_agent/__init__.py`
- `lc_agent/core/engine.py`

### 📦 Third-party Dependencies

项目使用的第三方库：

- `aiosqlite`
- `fastapi`
- `langchain`
- `langchain_core`
- `langgraph`
- `mcp`
- `sqlalchemy`
- `uvicorn`
- ......以及更多的第三方库......


---
# markdown content namespace: lc_agent Project Root Dir Some Files 


## lc_agent File Tree (relative dir: `.`)


`````

├── README.md
└── pyproject.toml

`````

---


## lc_agent (relative dir: `.`)  Included Files (total: 2 files)


- `README.md`

- `pyproject.toml`


---


--- **start of file: README.md** (project: lc_agent) --- 

`````markdown
# lc-agent

基于 LangChain / LangGraph 的 AI Agent 框架，内置 Web UI。

## 定位

lc-agent 是一个**可导入的框架**，用户在自己的项目中 `import lc_agent` 来开发自定义 Agent 应用，无需 clone 或修改框架代码。

## 功能

- 内置 FastAPI 服务器 + WebSocket 流式对话
- Vue 3 暗色主题 Web UI（Element Plus）
- LangGraph ReAct Agent 引擎
- 工具注册表（`@tool` 装饰器，支持分组 + 分组描述）
- SKILL.md 技能扫描（支持 `metadata.group` 分组）
- MCP 服务器管理 + 工具适配
- 会话持久化（SQLModel + SQLite）
- Human-in-the-loop 审批机制
- Agent 预设管理（代码注册 / 页面创建）

## 安装

```bash
# Python >= 3.12
pip install -e .
```

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

app.run()
```

## 配置

使用 `config.jsonc`（支持注释 + `{env:VAR}` 环境变量替换）：

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
└── my-skill/           # 文件夹名 = name 字段
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
# 技能内容
...
```

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

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | LangChain `create_agent` + `init_chat_model` (多提供商) |
| LLM 客户端 | `ChatOpenAIReasoning` — 自动提取 reasoning_content（兼容所有供应商） |
| 后端 | FastAPI + SQLModel + asyncio |
| 前端 | Vue 3 + TypeScript + Element Plus + Vite |
| 数据库 | SQLite (aiosqlite) |
| 通信 | WebSocket (流式) + REST API |

## Reasoning / 思考过程显示

框架使用自定义的 `ChatOpenAIReasoning` 类（继承 `ChatOpenAI`），自动从流式响应中提取 `reasoning_content` 字段，支持任何返回该字段的模型：

- DeepSeek 系列（通过 DeepSeek 官方 / 字节方舟 / 阿里百炼等）
- GLM 系列（复杂任务时自动触发思考）
- 任何其他返回 `reasoning_content` 或 `reasoning` 的供应商

无需为每个供应商 import 不同的 Chat Model 类。

## License

MIT

`````

--- **end of file: README.md** (project: lc_agent) --- 

---


--- **start of file: pyproject.toml** (project: lc_agent) --- 

`````text
[project]
name = "lc-agent"
version = "0.1.0"
description = "LangChain Agent framework with built-in Web UI"
requires-python = ">=3.12"
license = "MIT"
dependencies = [
    "langchain>=1.0",
    "langgraph>=0.4",
    "langchain-openai",
    "langchain-deepseek",
    "fastapi>=0.115",
    "uvicorn[standard]",
    "sqlmodel>=0.0.22",
    "aiosqlite>=0.20",
    "langgraph-checkpoint-sqlite>=3.0",
    "python-dotenv",
    "commentjson",
    "websockets",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "mcp>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx",
    "ruff",
]

[project.scripts]
lc-agent = "lc_agent.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 120

`````

--- **end of file: pyproject.toml** (project: lc_agent) --- 

---

# markdown content namespace: lc_agent Python 后端源码 


## lc_agent File Tree (relative dir: `lc_agent`)


`````

└── lc_agent
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── config
    │   ├── __init__.py
    │   ├── loader.py
    │   └── schema.py
    ├── core
    │   ├── __init__.py
    │   ├── chat_model.py
    │   ├── engine.py
    │   └── models.py
    ├── db
    │   ├── __init__.py
    │   ├── engine.py
    │   ├── models.py
    │   └── repository.py
    ├── main.py
    ├── mcp
    │   ├── __init__.py
    │   ├── manager.py
    │   └── tool_adapter.py
    ├── server
    │   ├── __init__.py
    │   ├── app.py
    │   ├── dependencies.py
    │   ├── routes
    │   │   ├── __init__.py
    │   │   ├── agents.py
    │   │   ├── health.py
    │   │   ├── mcp.py
    │   │   ├── models.py
    │   │   ├── sessions.py
    │   │   ├── skills.py
    │   │   └── tools.py
    │   └── websocket.py
    ├── skills
    │   ├── __init__.py
    │   └── scanner.py
    ├── tools
    │   ├── __init__.py
    │   ├── builtin.py
    │   └── registry.py
    └── utils
        └── loggers.py

`````

---


## lc_agent (relative dir: `lc_agent`)  Included Files (total: 36 files)


- `lc_agent/app.py`

- `lc_agent/main.py`

- `lc_agent/__init__.py`

- `lc_agent/__main__.py`

- `lc_agent/config/loader.py`

- `lc_agent/config/schema.py`

- `lc_agent/config/__init__.py`

- `lc_agent/core/chat_model.py`

- `lc_agent/core/engine.py`

- `lc_agent/core/models.py`

- `lc_agent/core/__init__.py`

- `lc_agent/db/engine.py`

- `lc_agent/db/models.py`

- `lc_agent/db/repository.py`

- `lc_agent/db/__init__.py`

- `lc_agent/mcp/manager.py`

- `lc_agent/mcp/tool_adapter.py`

- `lc_agent/mcp/__init__.py`

- `lc_agent/server/app.py`

- `lc_agent/server/dependencies.py`

- `lc_agent/server/websocket.py`

- `lc_agent/server/__init__.py`

- `lc_agent/skills/scanner.py`

- `lc_agent/skills/__init__.py`

- `lc_agent/tools/builtin.py`

- `lc_agent/tools/registry.py`

- `lc_agent/tools/__init__.py`

- `lc_agent/utils/loggers.py`

- `lc_agent/server/routes/agents.py`

- `lc_agent/server/routes/health.py`

- `lc_agent/server/routes/mcp.py`

- `lc_agent/server/routes/models.py`

- `lc_agent/server/routes/sessions.py`

- `lc_agent/server/routes/skills.py`

- `lc_agent/server/routes/tools.py`

- `lc_agent/server/routes/__init__.py`


---


--- **start of file: lc_agent/app.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/app.py`

#### 📦 Imports

- `from __future__ import annotations`
- `from contextlib import asynccontextmanager`
- `import uvicorn`
- `from fastapi import FastAPI`
- `from fastapi import WebSocket`
- `from fastapi import WebSocketDisconnect`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.db.engine import init_db`
- `from lc_agent.server.app import create_app`
- `from lc_agent.server.app import mount_static_files`
- `from lc_agent.server.websocket import ChatWebSocketHandler`
- `from lc_agent.skills.scanner import SkillScanner`
- `from lc_agent.mcp.manager import McpManager`
- `import asyncio`
- `import asyncio`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.models import AgentPresetDB`
- `from lc_agent.core.models import AgentPreset`
- `from sqlalchemy import select`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent import __version__`
- `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`
- `import aiosqlite`

#### 🏛️ Classes (1)

##### 📌 `class LcAgentApp`
*Line: 15*

**Docstring:**
`````
Main application orchestrator — creates engine, server, and runs.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict, host: str = '127.0.0.1', port: int = 8000)`
  - **Parameters:**
    - `self`
    - `config: dict`
    - `host: str = '127.0.0.1'`
    - `port: int = 8000`

**Public Methods (2):**
- `def add_agent(self, name: str, graph, description: str = '')`
  - **Docstring:**
  `````
  Register a pre-built CompiledStateGraph as a named agent.
  
  Args:
      name: Unique agent identifier
      graph: A compiled LangGraph (must have ainvoke and astream_events)
      description: Human-readable description
  `````
- `def run(self)`
  - *Start the server (blocking).*


---

`````python
# lc_agent/app.py
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from lc_agent.core.engine import AgentEngine
from lc_agent.db.engine import init_db
from lc_agent.server.app import create_app, mount_static_files
from lc_agent.server.websocket import ChatWebSocketHandler


class LcAgentApp:
    """Main application orchestrator — creates engine, server, and runs."""

    def __init__(self, config: dict, host: str = "127.0.0.1", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self._db_url = config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
        self._checkpoint_path = config.get("database", {}).get("checkpoint_path", "./lc_agent_checkpoints.db")
        self.engine = AgentEngine(config)
        from lc_agent.skills.scanner import SkillScanner
        skills_dir = config.get("skills", {}).get("directory", "./skills")
        self.skill_scanner = SkillScanner(skills_dir)
        self.skill_scanner.scan()
        from lc_agent.mcp.manager import McpManager
        mcp_config = config.get("mcp_servers", {})
        self.mcp_manager = McpManager(mcp_config)
        self.fastapi_app = create_app(config, lifespan=self._lifespan)
        self.fastapi_app.state.mcp_manager = self.mcp_manager
        self.fastapi_app.state.skill_scanner = self.skill_scanner
        self.engine._skill_scanner = self.skill_scanner
        self.engine._mcp_manager = self.mcp_manager
        self.fastapi_app.state.engine = self.engine
        self._ws_handler = ChatWebSocketHandler(self.engine)
        self._setup_websocket_route()
        mount_static_files(self.fastapi_app)

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """FastAPI lifespan: startup and shutdown logic."""
        import asyncio

        await init_db(self._db_url)
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            import aiosqlite
            conn = await aiosqlite.connect(self._checkpoint_path)
            saver = AsyncSqliteSaver(conn)
            await saver.setup()
            self.engine._checkpointer = saver
        except Exception as e:
            print(f"[Warning] Checkpoint saver setup failed, using None: {e}")

        await self._load_presets_from_db()

        async def _connect_mcp_background():
            try:
                await self.mcp_manager.connect_all()
                connected = [s for s in self.mcp_manager.servers if s.status == "connected"]
                if connected:
                    print(f"[MCP] Connected: {[s.name for s in connected]}")
                    self.engine._mcp_generation += 1
            except Exception as e:
                print(f"[MCP] Background connection error: {e}")

        asyncio.create_task(_connect_mcp_background())
        yield

    def _setup_websocket_route(self):
        import asyncio

        async def _ws_loop(websocket: WebSocket, tid: str):
            streaming_task: asyncio.Task | None = None
            try:
                while True:
                    if streaming_task and not streaming_task.done():
                        recv_coro = websocket.receive_json()
                        recv_task = asyncio.ensure_future(recv_coro)
                        done, _ = await asyncio.wait(
                            [recv_task, streaming_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if recv_task in done:
                            data = recv_task.result()
                            if data.get("type") == "cancel":
                                self._ws_handler._cancel_flags[tid] = True
                        if streaming_task in done:
                            streaming_task = None
                            if recv_task not in done:
                                recv_task.cancel()
                                try:
                                    await recv_task
                                except (asyncio.CancelledError, Exception):
                                    pass
                    else:
                        data = await websocket.receive_json()
                        msg_type = data.get("type", "message")
                        if msg_type == "cancel":
                            continue
                        streaming_task = asyncio.create_task(
                            self._ws_handler.handle_message(websocket, tid, data)
                        )
            except WebSocketDisconnect:
                if streaming_task and not streaming_task.done():
                    streaming_task.cancel()
                await self._ws_handler.disconnect(tid)
            except Exception as e:
                print(f"[WS] Loop error: {e}")
                if streaming_task and not streaming_task.done():
                    streaming_task.cancel()
                await self._ws_handler.disconnect(tid)

        @self.fastapi_app.websocket("/ws/chat/{thread_id}")
        async def websocket_chat(websocket: WebSocket, thread_id: str):
            tid = await self._ws_handler.connect(websocket, thread_id)
            await _ws_loop(websocket, tid)

        @self.fastapi_app.websocket("/ws/chat")
        async def websocket_chat_auto(websocket: WebSocket):
            tid = await self._ws_handler.connect(websocket)
            await _ws_loop(websocket, tid)

    async def _load_presets_from_db(self):
        """Load user-created presets from database on startup."""
        from lc_agent.db.engine import get_async_session
        from lc_agent.db.models import AgentPresetDB
        from lc_agent.core.models import AgentPreset
        from sqlalchemy import select

        session = get_async_session(self._db_url)
        try:
            stmt = select(AgentPresetDB)
            result = await session.execute(stmt)
            for row in result.scalars().all():
                preset = AgentPreset(
                    id=row.id,
                    name=row.name,
                    system_prompt=row.system_prompt,
                    default_model=row.default_model,
                    allowed_tool_groups=row.allowed_tool_groups,
                    allowed_mcp_servers=row.allowed_mcp_servers,
                    allowed_skills=row.allowed_skills,
                    dangerous_tools=row.dangerous_tools,
                )
                self.engine._presets[preset.id] = preset
            loaded = len(self.engine._presets)
            if loaded:
                print(f"[Agents] Loaded {loaded} user presets from database")
        except Exception as e:
            print(f"[Warning] Failed to load presets from DB: {e}")
        finally:
            await session.close()

    def add_agent(self, name: str, graph, description: str = ""):
        """Register a pre-built CompiledStateGraph as a named agent.

        Args:
            name: Unique agent identifier
            graph: A compiled LangGraph (must have ainvoke and astream_events)
            description: Human-readable description
        """
        if name in self.engine._agents:
            raise ValueError(f"Agent '{name}' already registered")

        from lc_agent.core.models import AgentPreset

        self.engine._agents[name] = graph
        self.engine._agent_mcp_gen[name] = self.engine._mcp_generation
        preset = AgentPreset(
            id=name,
            name=name,
            system_prompt=description or f"Custom agent: {name}",
            default_model="custom",
            source="code",
        )
        self.engine._custom_presets[name] = preset

    def run(self):
        """Start the server (blocking)."""
        from lc_agent import __version__

        print(f"\n  lc_agent v{__version__}")
        print(f"  Web UI: http://{self.host}:{self.port}")
        print(f"  API Docs: http://{self.host}:{self.port}/api/docs\n")
        uvicorn.run(self.fastapi_app, host=self.host, port=self.port)

`````

--- **end of file: lc_agent/app.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/main.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/main.py`

#### 📦 Imports

- `import argparse`
- `from lc_agent.config.loader import load_config`
- `from lc_agent.app import LcAgentApp`

#### 🔧 Public Functions (1)

- `def main()`
  - *Line: 5*


---

`````python
# lc_agent/main.py
import argparse


def main():
    parser = argparse.ArgumentParser(description="lc_agent - LangChain Agent with Web UI")
    parser.add_argument("--config", "-c", help="Path to config.jsonc")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--dotenv", help="Path to .env file")
    args = parser.parse_args()

    from lc_agent.config.loader import load_config

    config = load_config(config_path=args.config, dotenv_path=args.dotenv)

    from lc_agent.app import LcAgentApp

    app = LcAgentApp(config, host=args.host, port=args.port)
    app.run()


if __name__ == "__main__":
    main()

`````

--- **end of file: lc_agent/main.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/__init__.py`

#### 📝 Module Docstring

`````
lc_agent — LangChain Agent framework with built-in Web UI.
`````

#### 📦 Imports

- `from lc_agent.app import LcAgentApp`
- `from lc_agent.config.loader import load_config`
- `from lc_agent.tools.registry import ToolRegistry`
- `from lc_agent.tools.registry import tool`


---

`````python
# lc_agent/__init__.py
"""lc_agent — LangChain Agent framework with built-in Web UI."""

__version__ = "0.1.0"

from lc_agent.app import LcAgentApp
from lc_agent.config.loader import load_config
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = [
    "LcAgentApp",
    "load_config",
    "ToolRegistry",
    "tool",
    "__version__",
]

`````

--- **end of file: lc_agent/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/__main__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/__main__.py`

#### 📦 Imports

- `from lc_agent.main import main`


---

`````python
from lc_agent.main import main

if __name__ == "__main__":
    main()

`````

--- **end of file: lc_agent/__main__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/config/loader.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/config/loader.py`

#### 📦 Imports

- `import os`
- `import re`
- `from pathlib import Path`
- `from typing import Any`
- `import commentjson`
- `from dotenv import load_dotenv`

#### 🔧 Public Functions (4)

- `def substitute_env_vars(data: Any) -> Any`
  - *Line: 12*
  - *Recursively replace {env:VAR_NAME} patterns with environment variable values.*

- `def load_config_from_file(path: str) -> dict`
  - *Line: 36*
  - *Load a JSONC configuration file and apply env substitution.*

- `def load_config(config_path: str | None = None, dotenv_path: str | None = None) -> dict`
  - *Line: 48*
  - *Load configuration with priority: explicit path > ./config.jsonc > ~/.lc_agent/config.jsonc > defaults.*

- `def replacer(m)`
  - *Line: 22*


---

`````python
import os
import re
from pathlib import Path
from typing import Any

import commentjson
from dotenv import load_dotenv

ENV_PATTERN = re.compile(r"\{env:([^}]+)\}")


def substitute_env_vars(data: Any) -> Any:
    """Recursively replace {env:VAR_NAME} patterns with environment variable values."""
    if isinstance(data, str):
        match = ENV_PATTERN.fullmatch(data)
        if match:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        def replacer(m):
            var_name = m.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        return ENV_PATTERN.sub(replacer, data)
    elif isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    return data


def load_config_from_file(path: str) -> dict:
    """Load a JSONC configuration file and apply env substitution."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = commentjson.load(f)

    return substitute_env_vars(raw)


def load_config(
    config_path: str | None = None,
    dotenv_path: str | None = None,
) -> dict:
    """Load configuration with priority: explicit path > ./config.jsonc > ~/.lc_agent/config.jsonc > defaults."""
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.append(Path.cwd() / "config.jsonc")
    search_paths.append(Path.home() / ".lc_agent" / "config.jsonc")

    for p in search_paths:
        if p.exists():
            config = load_config_from_file(str(p))
            config["_config_path"] = str(p)
            config["_project_root"] = str(p.parent)
            return config

    return {
        "provider": {},
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ""},
        "_config_path": None,
        "_project_root": str(Path.cwd()),
    }

`````

--- **end of file: lc_agent/config/loader.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/config/schema.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/config/schema.py`

#### 📦 Imports

- `from pydantic import BaseModel`
- `from pydantic import Field`

#### 🏛️ Classes (6)

##### 📌 `class ModelConfig(BaseModel)`
*Line: 4*

**Class Variables (2):**
- `id: str`
- `context_limit: int = 8000`

##### 📌 `class ProviderConfig(BaseModel)`
*Line: 9*

**Class Variables (3):**
- `api_key: str = ''`
- `base_url: str = ''`
- `models: list[ModelConfig] = Field(default_factory=list)`

##### 📌 `class DatabaseConfig(BaseModel)`
*Line: 15*

**Class Variables (2):**
- `url: str = 'sqlite+aiosqlite:///./lc_agent_data.db'`
- `checkpoint_path: str = './lc_agent_checkpoints.db'`

##### 📌 `class SkillsConfig(BaseModel)`
*Line: 20*

**Class Variables (1):**
- `directory: str = './skills'`

##### 📌 `class McpServerConfig(BaseModel)`
*Line: 24*

**Class Variables (6):**
- `type: str = 'local'`
- `command: str | list[str] = ''`
- `args: list[str] = Field(default_factory=list)`
- `env: dict[str, str] = Field(default_factory=dict)`
- `url: str = ''`
- `enabled: bool = True`

##### 📌 `class AppConfig(BaseModel)`
*Line: 33*

**Docstring:**
`````
Application configuration schema.
`````

**Class Variables (8):**
- `provider: dict[str, ProviderConfig | dict] = Field(default_factory=dict)`
- `agent: dict = Field(default_factory=lambda: {'system_prompt': 'You are a helpful assistant.', 'default_model': '', 'streaming': True})`
- `mcp: dict = Field(default_factory=dict)`
- `database: DatabaseConfig = Field(default_factory=DatabaseConfig)`
- `session: dict = Field(default_factory=lambda: {'db_path': ''})`
- `ui: dict = Field(default_factory=dict)`
- `skills: SkillsConfig = Field(default_factory=SkillsConfig)`
- `mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)`


---

`````python
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    id: str
    context_limit: int = 8000


class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    models: list[ModelConfig] = Field(default_factory=list)


class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./lc_agent_data.db"
    checkpoint_path: str = "./lc_agent_checkpoints.db"


class SkillsConfig(BaseModel):
    directory: str = "./skills"


class McpServerConfig(BaseModel):
    type: str = "local"  # "local", "sse", "http"
    command: str | list[str] = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    enabled: bool = True


class AppConfig(BaseModel):
    """Application configuration schema."""

    provider: dict[str, ProviderConfig | dict] = Field(default_factory=dict)
    agent: dict = Field(default_factory=lambda: {
        "system_prompt": "You are a helpful assistant.",
        "default_model": "",
        "streaming": True,
    })
    mcp: dict = Field(default_factory=dict)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    session: dict = Field(default_factory=lambda: {"db_path": ""})
    ui: dict = Field(default_factory=dict)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)

`````

--- **end of file: lc_agent/config/schema.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/config/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/config/__init__.py`

#### 📦 Imports

- `from lc_agent.config.loader import load_config`
- `from lc_agent.config.loader import load_config_from_file`
- `from lc_agent.config.loader import substitute_env_vars`


---

`````python
from lc_agent.config.loader import load_config, load_config_from_file, substitute_env_vars

__all__ = ["load_config", "load_config_from_file", "substitute_env_vars"]

`````

--- **end of file: lc_agent/config/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/core/chat_model.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/core/chat_model.py`

#### 📝 Module Docstring

`````
ChatOpenAI subclass that extracts reasoning_content from streaming deltas.

ChatOpenAI only supports official OpenAI API fields. Many providers (DeepSeek,
GLM, etc.) return a non-standard `reasoning_content` field in the streaming
delta for chain-of-thought / thinking content. This subclass captures it into
`additional_kwargs["reasoning_content"]` so downstream handlers can display it.
`````

#### 📦 Imports

- `from __future__ import annotations`
- `from langchain_core.messages import AIMessageChunk`
- `from langchain_core.outputs import ChatGenerationChunk`
- `from langchain_openai import ChatOpenAI`

#### 🏛️ Classes (1)

##### 📌 `class ChatOpenAIReasoning(ChatOpenAI)`
*Line: 16*

**Docstring:**
`````
ChatOpenAI with reasoning_content extraction from streaming deltas.

Drop-in replacement for ChatOpenAI. Works with any provider that returns
`reasoning_content` or `reasoning` in the streaming delta dict (e.g.
DeepSeek, GLM with thinking mode, OpenRouter).
`````


---

`````python
"""ChatOpenAI subclass that extracts reasoning_content from streaming deltas.

ChatOpenAI only supports official OpenAI API fields. Many providers (DeepSeek,
GLM, etc.) return a non-standard `reasoning_content` field in the streaming
delta for chain-of-thought / thinking content. This subclass captures it into
`additional_kwargs["reasoning_content"]` so downstream handlers can display it.
"""

from __future__ import annotations

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI


class ChatOpenAIReasoning(ChatOpenAI):
    """ChatOpenAI with reasoning_content extraction from streaming deltas.

    Drop-in replacement for ChatOpenAI. Works with any provider that returns
    `reasoning_content` or `reasoning` in the streaming delta dict (e.g.
    DeepSeek, GLM with thinking mode, OpenRouter).
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info,
        )
        if generation_chunk is None:
            return None

        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if not choices:
            return generation_chunk

        delta = choices[0].get("delta") or {}
        if isinstance(generation_chunk.message, AIMessageChunk):
            reasoning = delta.get("reasoning_content")
            if reasoning is None:
                reasoning = delta.get("reasoning")
            if reasoning is not None:
                generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning

        return generation_chunk

`````

--- **end of file: lc_agent/core/chat_model.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/core/engine.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/core/engine.py`

#### 📦 Imports

- `from __future__ import annotations`
- `from typing import Any`
- `from typing import AsyncIterator`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent.core.models import ModelInfo`
- `from lc_agent.tools.registry import ToolRegistry`
- `from langchain.agents import create_agent`
- `from langchain.chat_models import init_chat_model`
- `from lc_agent.core.chat_model import ChatOpenAIReasoning`

#### 🏛️ Classes (1)

##### 📌 `class AgentEngine`
*Line: 10*

**Docstring:**
`````
Core agent engine wrapping langchain.agents.create_agent with middleware support.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict, checkpointer = None)`
  - **Parameters:**
    - `self`
    - `config: dict`
    - `checkpointer = None`

**Public Methods (11):**
- `def get_models(self) -> list[ModelInfo]`
  - *Return available models.*
- `def get_builtin_presets(self) -> list[AgentPreset]`
  - *Return the three built-in agent presets.*
- `def get_default_preset(self) -> AgentPreset`
  - *Return the default agent (Chat - safest).*
- `def build_agent(self, preset: AgentPreset | None = None)`
  - *Build a LangGraph ReAct agent from preset.*
- `async def chat(self, message: str, thread_id: str, preset_id: str = '__chat__') -> str`
  - *Send a message and get a response (non-streaming).*
- `async def chat_stream(self, message: str, thread_id: str, preset_id: str = '__chat__') -> AsyncIterator[dict]`
  - *Stream chat responses as events.*
- `async def generate_title(self, user_message: str, model_id: str = '') -> str`
  - *Generate a short conversation title from the user's first message.*
- `def get_presets(self) -> list[AgentPreset]`
  - *Return all agent presets (including default and custom).*
- `def add_preset(self, preset: AgentPreset) -> AgentPreset`
  - *Add a new agent preset.*
- `def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None`
  - *Update an existing preset.*
- `def delete_preset(self, preset_id: str) -> bool`
  - *Delete a preset. Cannot delete builtin.*

**Class Variables (1):**
- `BUILTIN_IDS = {'__chat__', '__empty__', '__power__'}`


---

`````python
# lc_agent/core/engine.py
from __future__ import annotations

from typing import Any, AsyncIterator

from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.tools.registry import ToolRegistry


class AgentEngine:
    """Core agent engine wrapping langchain.agents.create_agent with middleware support."""

    def __init__(self, config: dict, checkpointer=None):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = checkpointer
        self._agents: dict[str, Any] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)
        self._presets: dict[str, AgentPreset] = {}
        self._custom_presets: dict[str, AgentPreset] = {}
        self._agent_mcp_gen: dict[str, int] = {}
        self._mcp_generation: int = 0

    def _parse_models(self, config: dict) -> list[ModelInfo]:
        """Extract ModelInfo list from config."""
        models = []
        for provider_name, provider_conf in config.get("provider", {}).items():
            if isinstance(provider_conf, dict):
                for model_conf in provider_conf.get("models", []):
                    models.append(ModelInfo(
                        id=model_conf["id"],
                        provider=provider_name,
                        base_url=provider_conf.get("base_url", ""),
                        context_limit=model_conf.get("context_limit", 8000),
                        api_key=provider_conf.get("api_key", ""),
                    ))
        return models

    def get_models(self) -> list[ModelInfo]:
        """Return available models."""
        return self._models

    BUILTIN_IDS = {"__chat__", "__empty__", "__power__"}

    def get_builtin_presets(self) -> list[AgentPreset]:
        """Return the three built-in agent presets."""
        agent_conf = self.config.get("agent", {})
        default_model = agent_conf.get("default_model", "")
        return [
            AgentPreset(
                id="__chat__",
                name="Chat",
                system_prompt="You are a helpful assistant. Respond in the user's language.",
                default_model=default_model,
                allowed_tool_groups=[],
                allowed_mcp_servers=[],
                allowed_skills=[],
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="__empty__",
                name="Empty",
                system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
                default_model=default_model,
                allowed_tool_groups=None,
                allowed_mcp_servers=None,
                allowed_skills=None,
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="__power__",
                name="Power",
                system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
                default_model=default_model,
                allowed_tool_groups=None,
                allowed_mcp_servers=None,
                allowed_skills=None,
                source="builtin",
                default_enabled=True,
            ),
        ]

    def get_default_preset(self) -> AgentPreset:
        """Return the default agent (Chat - safest)."""
        return self.get_builtin_presets()[0]

    def build_agent(self, preset: AgentPreset | None = None):
        """Build a LangGraph ReAct agent from preset."""
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        system_prompt = preset.system_prompt
        if hasattr(self, '_skill_scanner') and self._skill_scanner:
            enabled_skills = self._skill_scanner.get_filtered(preset.allowed_skills)
            if enabled_skills:
                skills_text = "\n\n---\n\n".join(
                    f"## Skill: {s.name}\n\n{s.content}" for s in enabled_skills
                )
                system_prompt = f"{system_prompt}\n\n# Available Skills\n\n{skills_text}"

        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            mcp_tools = self._mcp_manager.get_filtered_langchain_tools(preset.allowed_mcp_servers)
            tools = tools + mcp_tools

        model_info = self._find_model(preset.default_model)
        llm = self._create_llm(model_info, preset.default_model)

        from langchain.agents import create_agent

        kwargs: dict[str, Any] = {}
        if self._checkpointer:
            kwargs["checkpointer"] = self._checkpointer

        if preset.dangerous_tools:
            kwargs["interrupt_before"] = ["tools"]

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            **kwargs,
        )

        self._agents[preset.id] = agent
        return agent

    def _create_llm(self, model_info: ModelInfo | None, model_id: str):
        """Create a chat model instance.

        Uses ChatOpenAIReasoning when base_url is set — extracts reasoning_content
        from any provider that returns it (DeepSeek, GLM, etc).
        Uses init_chat_model for standard providers (handles provider routing).
        """
        if model_info and model_info.base_url:
            from lc_agent.core.chat_model import ChatOpenAIReasoning
            return ChatOpenAIReasoning(
                model=model_info.id,
                base_url=model_info.base_url,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
            )

        from langchain.chat_models import init_chat_model

        if model_info:
            model_str = f"{model_info.provider}:{model_info.id}" if model_info.provider else model_info.id
            return init_chat_model(
                model_str,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
            )

        return init_chat_model(model_id, api_key="not-set", temperature=0.7, stream_usage=True)

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    def _resolve_preset(self, preset_id: str) -> AgentPreset:
        """Resolve a preset ID to an AgentPreset object."""
        if preset_id in self.BUILTIN_IDS:
            for bp in self.get_builtin_presets():
                if bp.id == preset_id:
                    return bp
        if preset_id in self._custom_presets:
            return self._custom_presets[preset_id]
        if preset_id in self._presets:
            return self._presets[preset_id]
        return self.get_default_preset()

    def _get_or_build_agent(self, preset_id: str):
        """Get cached agent or build a new one. Rebuilds if MCP state changed."""
        preset = self._resolve_preset(preset_id)
        mcp_gen = getattr(self, '_mcp_generation', 0)
        cached = self._agents.get(preset_id)
        cached_gen = self._agent_mcp_gen.get(preset_id, -1)
        if cached is None or cached_gen != mcp_gen:
            agent = self.build_agent(preset)
            self._agent_mcp_gen[preset_id] = mcp_gen
            return agent
        return cached

    async def chat(self, message: str, thread_id: str, preset_id: str = "__chat__") -> str:
        """Send a message and get a response (non-streaming)."""
        agent = self._get_or_build_agent(preset_id)

        config = {"configurable": {"thread_id": thread_id}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(self, message: str, thread_id: str, preset_id: str = "__chat__") -> AsyncIterator[dict]:
        """Stream chat responses as events."""
        agent = self._get_or_build_agent(preset_id)

        config = {"configurable": {"thread_id": thread_id}}
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        ):
            yield event

    async def generate_title(self, user_message: str, model_id: str = "") -> str:
        """Generate a short conversation title from the user's first message."""
        model_info = self._find_model(model_id) if model_id else None
        if model_info is None and self._models:
            model_info = self._models[0]
        if model_info is None:
            return user_message[:20]

        llm = self._create_llm(model_info, model_info.id)
        try:
            resp = await llm.ainvoke([
                {"role": "system", "content": "用10个字以内为这段对话生成一个简洁标题。只输出标题，不要标点符号和引号。"},
                {"role": "user", "content": user_message[:200]},
            ])
            title = resp.content.strip().strip('"\'""').strip()
            return title[:30] if title else user_message[:20]
        except Exception:
            return user_message[:20]

    def get_presets(self) -> list[AgentPreset]:
        """Return all agent presets (including default and custom)."""
        default = self.get_default_preset()
        return [default] + list(self._presets.values()) + list(self._custom_presets.values())

    def add_preset(self, preset: AgentPreset) -> AgentPreset:
        """Add a new agent preset."""
        self._presets[preset.id] = preset
        return preset

    def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None:
        """Update an existing preset."""
        if preset_id not in self._presets:
            return None
        existing = self._presets[preset_id]
        updated = existing.model_copy(update=data)
        self._presets[preset_id] = updated
        return updated

    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset. Cannot delete builtin."""
        if preset_id in self.BUILTIN_IDS:
            return False
        return self._presets.pop(preset_id, None) is not None

`````

--- **end of file: lc_agent/core/engine.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/core/models.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/core/models.py`

#### 📦 Imports

- `from pydantic import BaseModel`
- `from pydantic import Field`

#### 🏛️ Classes (2)

##### 📌 `class ModelInfo(BaseModel)`
*Line: 5*

**Docstring:**
`````
LLM model metadata.
`````

**Class Variables (5):**
- `id: str`
- `provider: str`
- `base_url: str`
- `context_limit: int = 8000`
- `api_key: str = ''`

##### 📌 `class AgentPreset(BaseModel)`
*Line: 15*

**Docstring:**
`````
Agent preset configuration (three-value semantics from nb_agent).

For allowed_* fields:
  None  = all allowed (default)
  []    = all disabled
  ["a"] = only specified items allowed

source: "builtin" | "code" | "user"
default_enabled: controls whether tools/MCP/skills default to ON or OFF in the UI
`````

**Class Variables (10):**
- `id: str`
- `name: str`
- `system_prompt: str`
- `default_model: str`
- `allowed_tool_groups: list[str] | None = None`
- `allowed_mcp_servers: list[str] | None = None`
- `allowed_skills: list[str] | None = None`
- `dangerous_tools: list[str] = Field(default_factory=list)`
- `source: str = 'user'`
- `default_enabled: bool = True`


---

`````python
# lc_agent/core/models.py
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """LLM model metadata."""

    id: str
    provider: str
    base_url: str
    context_limit: int = 8000
    api_key: str = ""


class AgentPreset(BaseModel):
    """Agent preset configuration (three-value semantics from nb_agent).

    For allowed_* fields:
      None  = all allowed (default)
      []    = all disabled
      ["a"] = only specified items allowed

    source: "builtin" | "code" | "user"
    default_enabled: controls whether tools/MCP/skills default to ON or OFF in the UI
    """

    id: str
    name: str
    system_prompt: str
    default_model: str

    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None

    dangerous_tools: list[str] = Field(default_factory=list)
    source: str = "user"
    default_enabled: bool = True

`````

--- **end of file: lc_agent/core/models.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/core/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/core/__init__.py`

#### 📦 Imports

- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent.core.models import ModelInfo`


---

`````python
# lc_agent/core/__init__.py
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset, ModelInfo

__all__ = ["AgentEngine", "AgentPreset", "ModelInfo"]

`````

--- **end of file: lc_agent/core/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/db/engine.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/db/engine.py`

#### 📦 Imports

- `from sqlalchemy.ext.asyncio import create_async_engine`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from sqlalchemy.orm import sessionmaker`
- `from sqlmodel import SQLModel`

#### 🔧 Public Functions (4)

- `def get_async_engine(url: str = 'sqlite+aiosqlite:///./lc_agent_data.db')`
  - *Line: 9*

- `def get_async_session(url: str = 'sqlite+aiosqlite:///./lc_agent_data.db') -> AsyncSession`
  - *Line: 16*

- `async def init_db(url: str = 'sqlite+aiosqlite:///./lc_agent_data.db')`
  - *Line: 24*
  - *Create all tables.*

- `def reset_engine()`
  - *Line: 31*
  - *Reset engine state (for testing).*


---

`````python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

_engine = None
_async_session_factory = None


def get_async_engine(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    global _engine
    if _engine is None:
        _engine = create_async_engine(url, echo=False)
    return _engine


def get_async_session(url: str = "sqlite+aiosqlite:///./lc_agent_data.db") -> AsyncSession:
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine(url)
        _async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory()


async def init_db(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    """Create all tables."""
    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def reset_engine():
    """Reset engine state (for testing)."""
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None

`````

--- **end of file: lc_agent/db/engine.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/db/models.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/db/models.py`

#### 📦 Imports

- `import uuid`
- `from datetime import datetime`
- `from datetime import timezone`
- `from sqlmodel import SQLModel`
- `from sqlmodel import Field`
- `from sqlalchemy import Column`
- `from sqlalchemy import JSON`

#### 🏛️ Classes (2)

##### 📌 `class AgentPresetDB(SQLModel)`
*Line: 12*

**Class Variables (11):**
- `__tablename__ = 'agent_presets'`
- `id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)`
- `name: str`
- `system_prompt: str = ''`
- `default_model: str = ''`
- `allowed_tool_groups: list[str] | None = Field(default=None, sa_column=Column(JSON))`
- `allowed_mcp_servers: list[str] | None = Field(default=None, sa_column=Column(JSON))`
- `allowed_skills: list[str] | None = Field(default=None, sa_column=Column(JSON))`
- `dangerous_tools: list[str] = Field(default_factory=list, sa_column=Column(JSON))`
- `created_at: datetime = Field(default_factory=utcnow)`
- `updated_at: datetime = Field(default_factory=utcnow)`

##### 📌 `class SessionMeta(SQLModel)`
*Line: 27*

**Class Variables (8):**
- `__tablename__ = 'sessions'`
- `id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)`
- `title: str = '新对话'`
- `agent_id: str = '__chat__'`
- `model: str = ''`
- `message_count: int = 0`
- `created_at: datetime = Field(default_factory=utcnow)`
- `updated_at: datetime = Field(default_factory=utcnow)`

#### 🔧 Public Functions (1)

- `def utcnow()`
  - *Line: 8*


---

`````python
import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


def utcnow():
    return datetime.now(timezone.utc)


class AgentPresetDB(SQLModel, table=True):
    __tablename__ = "agent_presets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    system_prompt: str = ""
    default_model: str = ""
    allowed_tool_groups: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_mcp_servers: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_skills: list[str] | None = Field(default=None, sa_column=Column(JSON))
    dangerous_tools: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "__chat__"
    model: str = ""
    message_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

`````

--- **end of file: lc_agent/db/models.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/db/repository.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/db/repository.py`

#### 📦 Imports

- `from datetime import datetime`
- `from datetime import timezone`
- `from sqlalchemy import select`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from lc_agent.db.models import AgentPresetDB`
- `from lc_agent.db.models import SessionMeta`

#### 🏛️ Classes (2)

##### 📌 `class PresetRepository`
*Line: 9*

**🔧 Constructor (`__init__`):**
- `def __init__(self, session: AsyncSession)`
  - **Parameters:**
    - `self`
    - `session: AsyncSession`

**Public Methods (5):**
- `async def list_all(self) -> list[AgentPresetDB]`
- `async def get_by_id(self, preset_id: str) -> AgentPresetDB | None`
- `async def create(self, **kwargs) -> AgentPresetDB`
- `async def update(self, preset_id: str, **kwargs) -> AgentPresetDB | None`
- `async def delete(self, preset_id: str) -> bool`

##### 📌 `class SessionRepository`
*Line: 48*

**🔧 Constructor (`__init__`):**
- `def __init__(self, session: AsyncSession)`
  - **Parameters:**
    - `self`
    - `session: AsyncSession`

**Public Methods (6):**
- `async def list_all(self, limit: int = 50) -> list[SessionMeta]`
- `async def get_by_id(self, session_id: str) -> SessionMeta | None`
- `async def create(self, **kwargs) -> SessionMeta`
- `async def update(self, session_id: str, **kwargs) -> SessionMeta | None`
- `async def delete(self, session_id: str) -> bool`
- `async def increment_messages(self, session_id: str) -> None`


---

`````python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import AgentPresetDB, SessionMeta


class PresetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[AgentPresetDB]:
        result = await self.session.execute(select(AgentPresetDB).order_by(AgentPresetDB.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, preset_id: str) -> AgentPresetDB | None:
        return await self.session.get(AgentPresetDB, preset_id)

    async def create(self, **kwargs) -> AgentPresetDB:
        preset = AgentPresetDB(**kwargs)
        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def update(self, preset_id: str, **kwargs) -> AgentPresetDB | None:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return None
        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        preset.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def delete(self, preset_id: str) -> bool:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return False
        await self.session.delete(preset)
        await self.session.commit()
        return True


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, limit: int = 50) -> list[SessionMeta]:
        result = await self.session.execute(
            select(SessionMeta).order_by(SessionMeta.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, session_id: str) -> SessionMeta | None:
        return await self.session.get(SessionMeta, session_id)

    async def create(self, **kwargs) -> SessionMeta:
        sess = SessionMeta(**kwargs)
        self.session.add(sess)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def update(self, session_id: str, **kwargs) -> SessionMeta | None:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return None
        for key, value in kwargs.items():
            if hasattr(sess, key):
                setattr(sess, key, value)
        sess.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def delete(self, session_id: str) -> bool:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return False
        await self.session.delete(sess)
        await self.session.commit()
        return True

    async def increment_messages(self, session_id: str) -> None:
        sess = await self.get_by_id(session_id)
        if sess:
            sess.message_count += 1
            sess.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

`````

--- **end of file: lc_agent/db/repository.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/db/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/db/__init__.py`

#### 📦 Imports

- `from lc_agent.db.models import AgentPresetDB`
- `from lc_agent.db.models import SessionMeta`
- `from lc_agent.db.engine import get_async_engine`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.engine import init_db`
- `from lc_agent.db.repository import PresetRepository`
- `from lc_agent.db.repository import SessionRepository`


---

`````python
from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_engine, get_async_session, init_db
from lc_agent.db.repository import PresetRepository, SessionRepository

__all__ = [
    "AgentPresetDB",
    "SessionMeta",
    "get_async_engine",
    "get_async_session",
    "init_db",
    "PresetRepository",
    "SessionRepository",
]

`````

--- **end of file: lc_agent/db/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/mcp/manager.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/mcp/manager.py`

#### 📦 Imports

- `from __future__ import annotations`
- `import asyncio`
- `import os`
- `from dataclasses import dataclass`
- `from dataclasses import field`
- `from typing import Any`
- `from mcp import ClientSession`
- `from mcp import StdioServerParameters`
- `from mcp.client.stdio import stdio_client`
- `from mcp import ClientSession`
- `from mcp.client.sse import sse_client`
- `from mcp import ClientSession`
- `from mcp.client.streamable_http import streamable_http_client`
- `from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas`
- `from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas`

#### 🏛️ Classes (2)

##### 📌 `class McpServerStatus`
*Line: 10*

**Class Variables (9):**
- `name: str`
- `type: str = 'local'`
- `command: str = ''`
- `url: str = ''`
- `enabled: bool = True`
- `status: str = 'disconnected'`
- `tools: list[str] = field(default_factory=list)`
- `tool_schemas: list[dict] = field(default_factory=list)`
- `error: str | None = None`

##### 📌 `class McpManager`
*Line: 22*

**Docstring:**
`````
Manages persistent MCP server connections and tool invocation.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, config: dict[str, dict])`
  - **Parameters:**
    - `self`
    - `config: dict[str, dict]`

**Public Methods (7):**
- `def get_server(self, name: str) -> McpServerStatus | None`
- `async def connect_all(self)`
  - *Connect to all configured MCP servers (persistent).*
- `async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str`
  - *Invoke a tool on a connected MCP server (serialized per server).*
- `def get_tools_for_server(self, server_name: str) -> list[str]`
  - *Get tool names for a given server.*
- `def get_langchain_tools(self) -> list`
  - *Get all connected MCP tools as LangChain StructuredTools.*
- `def get_filtered_langchain_tools(self, allowed_servers: list[str] | None) -> list`
  - *Get MCP tools filtered by allowed servers (three-value semantics).*
- `async def shutdown(self)`
  - *Clean up all persistent connections.*

**Properties (1):**
- `@property servers -> list[McpServerStatus]`


---

`````python
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpServerStatus:
    name: str
    type: str = "local"
    command: str = ""
    url: str = ""
    enabled: bool = True
    status: str = "disconnected"
    tools: list[str] = field(default_factory=list)
    tool_schemas: list[dict] = field(default_factory=list)
    error: str | None = None


class McpManager:
    """Manages persistent MCP server connections and tool invocation."""

    def __init__(self, config: dict[str, dict]):
        self._config = config
        self._servers: dict[str, McpServerStatus] = {}
        self._sessions: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._cleanup_tasks: list[Any] = []

        for name, conf in config.items():
            enabled = conf.get("enabled", True)
            server_type = conf.get("type", "local")
            command = conf.get("command", "")
            if isinstance(command, list):
                command = " ".join(command)
            self._servers[name] = McpServerStatus(
                name=name,
                type=server_type,
                command=command,
                url=conf.get("url", ""),
                enabled=enabled,
            )

    @property
    def servers(self) -> list[McpServerStatus]:
        return list(self._servers.values())

    def get_server(self, name: str) -> McpServerStatus | None:
        return self._servers.get(name)

    async def connect_all(self):
        """Connect to all configured MCP servers (persistent)."""
        for name, conf in self._config.items():
            if not conf.get("enabled", True):
                self._servers[name].status = "disabled"
                continue
            await self._connect_server(name, conf)

    async def _connect_server(self, name: str, conf: dict):
        """Establish a persistent connection to a single MCP server."""
        server_type = conf.get("type", "local")
        self._servers[name].status = "connecting"

        try:
            if server_type == "sse":
                await self._connect_sse_persistent(name, conf)
            elif server_type == "http":
                await self._connect_http_persistent(name, conf)
            else:
                await self._connect_stdio_persistent(name, conf)
        except Exception as e:
            self._servers[name].status = "error"
            self._servers[name].error = str(e)

    async def _connect_stdio_persistent(self, name: str, conf: dict):
        """Keep a stdio MCP server process alive."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        command_raw = conf.get("command", "")
        if isinstance(command_raw, list):
            cmd = command_raw[0]
            args = command_raw[1:]
        else:
            cmd = command_raw
            args = conf.get("args", [])

        env = {**os.environ, **conf.get("env", {})}
        params = StdioServerParameters(command=cmd, args=args, env=env)

        cm = stdio_client(params)
        transport = await cm.__aenter__()
        read, write = transport

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._cleanup_tasks.append((cm, session_cm))
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    async def _connect_sse_persistent(self, name: str, conf: dict):
        """Keep an SSE MCP connection alive."""
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        url = conf.get("url", "")
        if not url:
            raise ValueError(f"SSE server '{name}' requires a 'url' field")

        cm = sse_client(url=url)
        transport = await cm.__aenter__()
        read, write = transport

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._cleanup_tasks.append((cm, session_cm))
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    async def _connect_http_persistent(self, name: str, conf: dict):
        """Keep a StreamableHTTP MCP connection alive."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        url = conf.get("url", "")
        if not url:
            raise ValueError(f"HTTP server '{name}' requires a 'url' field")

        cm = streamable_http_client(url=url)
        transport = await cm.__aenter__()
        read, write = transport[0], transport[1]

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()
        await session.initialize()

        self._cleanup_tasks.append((cm, session_cm))
        self._sessions[name] = session
        self._extract_tools(name, await session.list_tools())

    def _extract_tools(self, name: str, tools_result):
        """Extract tool info from list_tools result."""
        tool_names = [t.name for t in tools_result.tools]
        tool_schemas = [
            {
                "name": t.name,
                "description": getattr(t, "description", "") or "",
                "input_schema": getattr(t, "inputSchema", {}) or {},
            }
            for t in tools_result.tools
        ]
        self._servers[name].status = "connected"
        self._servers[name].tools = tool_names
        self._servers[name].tool_schemas = tool_schemas
        self._servers[name].error = None
        self._locks[name] = asyncio.Lock()

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Invoke a tool on a connected MCP server (serialized per server)."""
        session = self._sessions.get(server_name)
        if session is None:
            return f"MCP server '{server_name}' not connected"

        lock = self._locks.get(server_name)
        try:
            if lock:
                async with lock:
                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, arguments),
                        timeout=60.0,
                    )
            else:
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=60.0,
                )
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
                else:
                    parts.append(str(content))
            return "\n".join(parts) if parts else "(empty result)"
        except asyncio.TimeoutError:
            return f"MCP tool '{tool_name}' timed out after 60s"
        except Exception as e:
            return f"MCP tool error: {e}"

    def get_tools_for_server(self, server_name: str) -> list[str]:
        """Get tool names for a given server."""
        server = self._servers.get(server_name)
        return server.tools if server else []

    def get_langchain_tools(self) -> list:
        """Get all connected MCP tools as LangChain StructuredTools."""
        from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas

        all_tools = []
        for server in self._servers.values():
            if server.enabled and server.status == "connected" and server.tool_schemas:
                invoke_fn = self._make_invoke_fn(server.name)
                tools = create_langchain_tools_from_schemas(server.name, server.tool_schemas, invoke_fn)
                all_tools.extend(tools)
        return all_tools

    def get_filtered_langchain_tools(self, allowed_servers: list[str] | None) -> list:
        """Get MCP tools filtered by allowed servers (three-value semantics)."""
        from lc_agent.mcp.tool_adapter import create_langchain_tools_from_schemas

        all_tools = []
        for server in self._servers.values():
            if not server.enabled or server.status != "connected" or not server.tool_schemas:
                continue
            if allowed_servers is not None and server.name not in allowed_servers:
                continue
            invoke_fn = self._make_invoke_fn(server.name)
            tools = create_langchain_tools_from_schemas(server.name, server.tool_schemas, invoke_fn)
            all_tools.extend(tools)
        return all_tools

    def _make_invoke_fn(self, server_name: str):
        """Create an async invoke function bound to a specific server."""
        async def invoke(tool_name: str, arguments: dict) -> str:
            return await self.call_tool(server_name, tool_name, arguments)
        return invoke

    async def shutdown(self):
        """Clean up all persistent connections."""
        for cm, session_cm in self._cleanup_tasks:
            try:
                await session_cm.__aexit__(None, None, None)
            except Exception:
                pass
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._sessions.clear()
        self._cleanup_tasks.clear()

`````

--- **end of file: lc_agent/mcp/manager.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/mcp/tool_adapter.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/mcp/tool_adapter.py`

#### 📝 Module Docstring

`````
Converts MCP tool schemas into LangChain StructuredTool instances.
`````

#### 📦 Imports

- `from __future__ import annotations`
- `from typing import Any`
- `from langchain_core.tools import StructuredTool`
- `from pydantic import BaseModel`
- `from pydantic import Field`
- `from pydantic import create_model`

#### 🔧 Public Functions (2)

- `def create_langchain_tools_from_schemas(server_name: str, tool_schemas: list[dict], invoke_fn: Any = None) -> list[StructuredTool]`
  - *Line: 44*
  - **Docstring:**
  `````
  Convert MCP tool schemas to LangChain StructuredTool list.
  
  Args:
      server_name: MCP server name for namespacing
      tool_schemas: List of {name, description, input_schema}
      invoke_fn: Optional async callable(tool_name, args) -> result
  `````

- `def mcp_tool_names_to_display(server_name: str, tool_names: list[str]) -> list[dict]`
  - *Line: 93*
  - *Convert MCP tool names to display format.*


---

`````python
"""Converts MCP tool schemas into LangChain StructuredTool instances."""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model


def _build_pydantic_model(tool_name: str, input_schema: dict) -> type[BaseModel]:
    """Dynamically create a Pydantic model from JSON Schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        python_type = _json_type_to_python(prop_def.get("type", "string"))
        description = prop_def.get("description", "")
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (python_type | None, Field(default=None, description=description))

    if not fields:
        fields["placeholder"] = (str | None, Field(default=None, description="no params"))

    model_name = f"McpInput_{tool_name}"
    return create_model(model_name, **fields)


def _json_type_to_python(json_type: str) -> type:
    """Map JSON Schema type to Python type."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)


def create_langchain_tools_from_schemas(
    server_name: str,
    tool_schemas: list[dict],
    invoke_fn: Any = None,
) -> list[StructuredTool]:
    """Convert MCP tool schemas to LangChain StructuredTool list.

    Args:
        server_name: MCP server name for namespacing
        tool_schemas: List of {name, description, input_schema}
        invoke_fn: Optional async callable(tool_name, args) -> result
    """
    tools = []
    for schema in tool_schemas:
        name = schema["name"]
        description = schema.get("description", "")
        input_schema = schema.get("input_schema", {"type": "object", "properties": {}})

        args_model = _build_pydantic_model(name, input_schema)
        full_name = f"mcp__{server_name}__{name}"

        if invoke_fn:
            async def _invoke(invoke=invoke_fn, tool_name=name, **kwargs):
                filtered = {k: v for k, v in kwargs.items() if v is not None}
                return await invoke(tool_name, filtered)

            tool = StructuredTool.from_function(
                func=None,
                coroutine=_invoke,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )
        else:
            def _placeholder(full=full_name, **kwargs):
                return f"MCP tool {full} not connected"

            tool = StructuredTool.from_function(
                func=_placeholder,
                name=full_name,
                description=f"[MCP:{server_name}] {description}",
                args_schema=args_model,
            )

        tools.append(tool)

    return tools


def mcp_tool_names_to_display(server_name: str, tool_names: list[str]) -> list[dict]:
    """Convert MCP tool names to display format."""
    return [
        {"name": f"mcp__{server_name}__{name}", "group": f"mcp__{server_name}", "description": f"MCP tool: {name}"}
        for name in tool_names
    ]

`````

--- **end of file: lc_agent/mcp/tool_adapter.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/mcp/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/mcp/__init__.py`

#### 📦 Imports

- `from lc_agent.mcp.manager import McpManager`


---

`````python
from lc_agent.mcp.manager import McpManager

__all__ = ["McpManager"]

`````

--- **end of file: lc_agent/mcp/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/app.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/app.py`

#### 📦 Imports

- `import mimetypes`
- `from pathlib import Path`
- `from fastapi import FastAPI`
- `from fastapi.middleware.cors import CORSMiddleware`
- `from fastapi.staticfiles import StaticFiles`
- `from lc_agent import __version__`
- `from lc_agent.server.routes.health import router as health_router`
- `from lc_agent.server.routes.tools import router as tools_router`
- `from lc_agent.server.routes.models import router as models_router`
- `from lc_agent.server.routes.agents import router as agents_router`
- `from lc_agent.server.routes.sessions import router as sessions_router`
- `from lc_agent.server.routes.skills import router as skills_router`
- `from lc_agent.server.routes.mcp import router as mcp_router`

#### 🔧 Public Functions (2)

- `def create_app(config: dict, lifespan = None) -> FastAPI`
  - *Line: 22*
  - *Create and configure the FastAPI application.*

- `def mount_static_files(app: FastAPI)`
  - *Line: 53*
  - *Mount static files AFTER WebSocket routes are registered.*


---

`````python
# lc_agent/server/app.py
import mimetypes
from pathlib import Path

from fastapi import FastAPI

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from lc_agent import __version__
from lc_agent.server.routes.health import router as health_router
from lc_agent.server.routes.tools import router as tools_router
from lc_agent.server.routes.models import router as models_router
from lc_agent.server.routes.agents import router as agents_router
from lc_agent.server.routes.sessions import router as sessions_router
from lc_agent.server.routes.skills import router as skills_router
from lc_agent.server.routes.mcp import router as mcp_router


def create_app(config: dict, lifespan=None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="lc_agent",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = config

    app.include_router(health_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    app.include_router(models_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(skills_router, prefix="/api")
    app.include_router(mcp_router, prefix="/api")

    return app


def mount_static_files(app: FastAPI):
    """Mount static files AFTER WebSocket routes are registered."""
    web_dist = Path(__file__).parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")

`````

--- **end of file: lc_agent/server/app.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/dependencies.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/dependencies.py`

#### 📦 Imports

- `from contextlib import asynccontextmanager`
- `from fastapi import Request`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.db.engine import get_async_session as _get_db_session`
- `from lc_agent.tools.registry import ToolRegistry`

#### 🔧 Public Functions (3)

- `def get_engine(request: Request) -> AgentEngine`
  - *Line: 11*
  - *Dependency to get the AgentEngine from app state.*

- `def get_registry(request: Request) -> ToolRegistry`
  - *Line: 16*
  - *Dependency to get the ToolRegistry singleton.*

- `async def get_db_session()`
  - *Line: 21*
  - *Dependency to get an async DB session.*


---

`````python
# lc_agent/server/dependencies.py
from contextlib import asynccontextmanager

from fastapi import Request

from lc_agent.core.engine import AgentEngine
from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.tools.registry import ToolRegistry


def get_engine(request: Request) -> AgentEngine:
    """Dependency to get the AgentEngine from app state."""
    return request.app.state.engine


def get_registry(request: Request) -> ToolRegistry:
    """Dependency to get the ToolRegistry singleton."""
    return ToolRegistry()


async def get_db_session():
    """Dependency to get an async DB session."""
    session = _get_db_session()
    try:
        yield session
    finally:
        await session.close()

`````

--- **end of file: lc_agent/server/dependencies.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/websocket.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/websocket.py`

#### 📦 Imports

- `import asyncio`
- `import uuid`
- `from typing import Any`
- `from fastapi import WebSocket`
- `from lc_agent.core.engine import AgentEngine`
- `import time`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.repository import SessionRepository`
- `from lc_agent.db.engine import get_async_session`
- `from lc_agent.db.repository import SessionRepository`
- `from langgraph.types import Command`

#### 🏛️ Classes (1)

##### 📌 `class ChatWebSocketHandler`
*Line: 11*

**Docstring:**
`````
Handles WebSocket connections for streaming chat.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, engine: AgentEngine)`
  - **Parameters:**
    - `self`
    - `engine: AgentEngine`

**Public Methods (3):**
- `async def connect(self, websocket: WebSocket, thread_id: str | None = None) -> str`
  - *Accept WebSocket connection.*
- `async def disconnect(self, thread_id: str)`
  - *Clean up on disconnect.*
- `async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict)`
  - *Process incoming message and stream response.*


---

`````python
# lc_agent/server/websocket.py
import asyncio
import uuid
from typing import Any

from fastapi import WebSocket

from lc_agent.core.engine import AgentEngine


class ChatWebSocketHandler:
    """Handles WebSocket connections for streaming chat."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self.active_connections: dict[str, WebSocket] = {}
        self._message_counts: dict[str, int] = {}
        self._cancel_flags: dict[str, bool] = {}

    async def connect(self, websocket: WebSocket, thread_id: str | None = None) -> str:
        """Accept WebSocket connection."""
        await websocket.accept()
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self.active_connections[thread_id] = websocket
        await websocket.send_json({"type": "connected", "thread_id": thread_id})
        return thread_id

    async def disconnect(self, thread_id: str):
        """Clean up on disconnect."""
        self.active_connections.pop(thread_id, None)
        self._cancel_flags.pop(thread_id, None)

    async def handle_message(self, websocket: WebSocket, thread_id: str, data: dict):
        """Process incoming message and stream response."""
        msg_type = data.get("type", "message")

        if msg_type == "cancel":
            self._cancel_flags[thread_id] = True
            return

        if msg_type == "message":
            import time
            content = data.get("content", "")
            preset_id = data.get("preset_id", "__chat__")
            self._cancel_flags[thread_id] = False
            usage_rounds: list[dict] = []
            round_start_time = time.time()

            is_first = self._message_counts.get(thread_id, 0) == 0
            if is_first:
                preliminary_title = content[:30].strip()
                await websocket.send_json({
                    "type": "title_update",
                    "thread_id": thread_id,
                    "title": preliminary_title,
                })
                asyncio.create_task(self._save_title(thread_id, preliminary_title))

            try:
                async for event in self.engine.chat_stream(content, thread_id, preset_id):
                    if self._cancel_flags.get(thread_id):
                        await websocket.send_json({"type": "cancelled"})
                        return
                    await self._send_event(websocket, event)
                    prev_len = len(usage_rounds)
                    self._accumulate_usage(event, usage_rounds)
                    if len(usage_rounds) > prev_len:
                        usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                        round_start_time = time.time()
                        await websocket.send_json({
                            "type": "llm_usage",
                            **usage_rounds[-1],
                        })

                done_payload: dict = {"type": "done"}
                if usage_rounds:
                    done_payload["usage"] = usage_rounds
                await websocket.send_json(done_payload)

                self._message_counts[thread_id] = self._message_counts.get(thread_id, 0) + 1
                if self._message_counts[thread_id] == 1:
                    asyncio.create_task(
                        self._generate_and_push_title(websocket, thread_id, content, preset_id)
                    )
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

        elif msg_type == "interrupt_response":
            approved = data.get("approved", False)
            preset_id = data.get("preset_id", "__chat__")
            self._cancel_flags[thread_id] = False
            try:
                from langgraph.types import Command

                agent = self.engine._agents.get(preset_id)
                if agent is None:
                    await websocket.send_json({"type": "error", "message": "No agent found for resume"})
                    return

                config = {"configurable": {"thread_id": thread_id}}
                resume_value = {"approved": approved}

                async for event in agent.astream_events(
                    Command(resume=resume_value),
                    config=config,
                    version="v2",
                ):
                    if self._cancel_flags.get(thread_id):
                        await websocket.send_json({"type": "cancelled"})
                        return
                    await self._send_event(websocket, event)
                await websocket.send_json({"type": "done"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    async def _save_title(self, thread_id: str, title: str):
        """Save title to DB without pushing to client."""
        try:
            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session()
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()
        except Exception:
            pass

    async def _generate_and_push_title(self, websocket: WebSocket, thread_id: str, first_message: str, preset_id: str = "__chat__"):
        """Generate title from first message using the agent's model, save to DB, and push to client."""
        try:
            model_id = ""
            if preset_id in self.engine.BUILTIN_IDS:
                for bp in self.engine.get_builtin_presets():
                    if bp.id == preset_id:
                        model_id = bp.default_model
                        break
            else:
                preset = self.engine._presets.get(preset_id) or self.engine._custom_presets.get(preset_id)
                if preset:
                    model_id = preset.default_model
            title = await self.engine.generate_title(first_message, model_id)

            from lc_agent.db.engine import get_async_session
            from lc_agent.db.repository import SessionRepository
            session = get_async_session()
            try:
                repo = SessionRepository(session)
                await repo.update(thread_id, title=title)
            finally:
                await session.close()

            await websocket.send_json({"type": "title_update", "thread_id": thread_id, "title": title})
        except Exception as e:
            print(f"[WS] Title generation failed: {e}")

    def _accumulate_usage(self, event: dict, usage_rounds: list[dict]):
        """Extract token usage from on_chat_model_end events."""
        kind = event.get("event", "")
        if kind != "on_chat_model_end":
            return

        output = event.get("data", {}).get("output")
        if not output:
            usage_rounds.append({"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cache_read_tokens": 0})
            return

        meta = getattr(output, "usage_metadata", None)
        if meta is None and hasattr(output, "response_metadata"):
            resp_meta = output.response_metadata or {}
            meta = resp_meta.get("token_usage") or resp_meta.get("usage")

        if meta:
            def _get(obj, key, default=0):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            input_t = _get(meta, "input_tokens", 0) or _get(meta, "prompt_tokens", 0)
            output_t = _get(meta, "output_tokens", 0) or _get(meta, "completion_tokens", 0)
            total_t = _get(meta, "total_tokens", 0) or (input_t + output_t)

            cache_read = 0
            if isinstance(meta, dict):
                details = meta.get("input_token_details") or {}
                cache_read = details.get("cache_read", 0) if isinstance(details, dict) else getattr(details, "cache_read", 0)
            else:
                details = getattr(meta, "input_token_details", None)
                if details:
                    cache_read = getattr(details, "cache_read", 0) if not isinstance(details, dict) else details.get("cache_read", 0)

            reasoning = 0
            if isinstance(meta, dict):
                out_details = meta.get("output_token_details") or {}
                reasoning = out_details.get("reasoning", 0) if isinstance(out_details, dict) else getattr(out_details, "reasoning", 0)
            else:
                out_details = getattr(meta, "output_token_details", None)
                if out_details:
                    reasoning = getattr(out_details, "reasoning", 0) if not isinstance(out_details, dict) else out_details.get("reasoning", 0)

            usage_rounds.append({
                "input_tokens": input_t or 0,
                "output_tokens": output_t or 0,
                "total_tokens": total_t or 0,
                "cache_read_tokens": cache_read or 0,
                "reasoning_tokens": reasoning or 0,
            })
        else:
            usage_rounds.append({"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cache_read_tokens": 0})

    async def _send_event(self, websocket: WebSocket, event: dict):
        """Convert LangGraph astream_events v2 to client-friendly format."""
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                additional = getattr(chunk, "additional_kwargs", None) or {}
                reasoning = additional.get("reasoning_content") or additional.get("reasoning")
                if reasoning:
                    await websocket.send_json({"type": "thinking", "content": reasoning})
                if hasattr(chunk, "content") and chunk.content:
                    await websocket.send_json({"type": "token", "content": chunk.content})

        elif kind == "on_tool_start":
            tool_input = event.get("data", {}).get("input", {})
            await websocket.send_json({
                "type": "tool_call",
                "name": event.get("name", ""),
                "run_id": event.get("run_id", ""),
                "args": tool_input,
            })

        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            result_str = str(output)
            await websocket.send_json({
                "type": "tool_result",
                "name": event.get("name", ""),
                "result": result_str,
            })

        elif kind == "on_chain_end":
            data_output = event.get("data", {}).get("output", {})
            if isinstance(data_output, dict) and "__interrupt" in str(data_output):
                await websocket.send_json({
                    "type": "interrupt",
                    "message": "Tool requires approval",
                    "data": data_output,
                })

`````

--- **end of file: lc_agent/server/websocket.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/__init__.py`

#### 📦 Imports

- `from lc_agent.server.app import create_app`


---

`````python
# lc_agent/server/__init__.py
from lc_agent.server.app import create_app

__all__ = ["create_app"]

`````

--- **end of file: lc_agent/server/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/skills/scanner.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/skills/scanner.py`

#### 📦 Imports

- `from __future__ import annotations`
- `import re`
- `from dataclasses import dataclass`
- `from pathlib import Path`
- `import yaml`

#### 🏛️ Classes (2)

##### 📌 `class SkillInfo`
*Line: 11*

**Class Variables (6):**
- `name: str`
- `description: str`
- `content: str`
- `file_path: str`
- `group: str = ''`
- `metadata: dict = None`

##### 📌 `class SkillScanner`
*Line: 24*

**Docstring:**
`````
Discovers and parses SKILL.md files from a directory.
`````

**🔧 Constructor (`__init__`):**
- `def __init__(self, directory: str = './skills')`
  - **Parameters:**
    - `self`
    - `directory: str = './skills'`

**Public Methods (5):**
- `def scan(self) -> list[SkillInfo]`
  - *Scan directory recursively for SKILL.md files.*
- `def get_by_name(self, name: str) -> SkillInfo | None`
  - *Get a skill by name.*
- `def get_filtered(self, allowed: list[str] | None) -> list[SkillInfo]`
  - **Docstring:**
  `````
  Filter skills by allowed list (three-value semantics).
  Also excludes runtime-disabled skills.
  `````
- `def get_groups(self) -> list[str]`
  - *Return unique skill group names.*
- `def get_by_group(self, group: str) -> list[SkillInfo]`
  - *Get all skills in a specific group.*

**Properties (1):**
- `@property skills -> list[SkillInfo]`


---

`````python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    description: str
    content: str
    file_path: str
    group: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SkillScanner:
    """Discovers and parses SKILL.md files from a directory."""

    def __init__(self, directory: str = "./skills"):
        self.directory = Path(directory)
        self._skills: list[SkillInfo] = []
        self._disabled_skills: set[str] = set()

    @property
    def skills(self) -> list[SkillInfo]:
        return self._skills

    def scan(self) -> list[SkillInfo]:
        """Scan directory recursively for SKILL.md files."""
        self._skills = []
        if not self.directory.exists():
            return self._skills

        for skill_file in self.directory.rglob("SKILL.md"):
            skill = self._parse_skill(skill_file)
            if skill:
                self._skills.append(skill)

        return self._skills

    def _parse_skill(self, path: Path) -> SkillInfo | None:
        """Parse a SKILL.md file with YAML frontmatter."""
        try:
            text = path.read_text(encoding="utf-8-sig")
            frontmatter, content = self._split_frontmatter(text)

            name = frontmatter.get("name", path.parent.name)
            description = frontmatter.get("description", "")
            metadata = frontmatter.get("metadata", {}) or {}
            group = metadata.get("group", "")

            return SkillInfo(
                name=name,
                description=description,
                content=content.strip(),
                file_path=str(path),
                group=group,
                metadata=metadata,
            )
        except Exception:
            return None

    def _split_frontmatter(self, text: str) -> tuple[dict, str]:
        """Split YAML frontmatter from markdown content."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if match:
            fm = yaml.safe_load(match.group(1)) or {}
            return fm, match.group(2)
        return {}, text

    def get_by_name(self, name: str) -> SkillInfo | None:
        """Get a skill by name."""
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def get_filtered(self, allowed: list[str] | None) -> list[SkillInfo]:
        """Filter skills by allowed list (three-value semantics).
        Also excludes runtime-disabled skills.
        """
        if allowed is None:
            skills = self._skills
        elif not allowed:
            return []
        else:
            skills = [s for s in self._skills if s.name in allowed]

        if self._disabled_skills:
            skills = [s for s in skills if s.name not in self._disabled_skills]
        return skills

    def get_groups(self) -> list[str]:
        """Return unique skill group names."""
        groups = set()
        for s in self._skills:
            if s.group:
                groups.add(s.group)
        return sorted(groups)

    def get_by_group(self, group: str) -> list[SkillInfo]:
        """Get all skills in a specific group."""
        return [s for s in self._skills if s.group == group]

`````

--- **end of file: lc_agent/skills/scanner.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/skills/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/skills/__init__.py`

#### 📦 Imports

- `from lc_agent.skills.scanner import SkillInfo`
- `from lc_agent.skills.scanner import SkillScanner`


---

`````python
from lc_agent.skills.scanner import SkillInfo, SkillScanner

__all__ = ["SkillInfo", "SkillScanner"]

`````

--- **end of file: lc_agent/skills/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/tools/builtin.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/tools/builtin.py`

#### 📦 Imports

- `from datetime import datetime`
- `from lc_agent.tools.registry import tool`

#### 🔧 Public Functions (1)

- `def get_current_time() -> str` `tool(group='builtin')`
  - *Line: 8*
  - *获取当前日期和时间。*


---

`````python
# lc_agent/tools/builtin.py
from datetime import datetime

from lc_agent.tools.registry import tool


@tool(group="builtin")
def get_current_time() -> str:
    """获取当前日期和时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

`````

--- **end of file: lc_agent/tools/builtin.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/tools/registry.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/tools/registry.py`

#### 📦 Imports

- `from __future__ import annotations`
- `import functools`
- `import re`
- `from typing import Any`
- `from typing import Callable`
- `from typing import overload`
- `from langchain_core.tools import BaseTool`
- `from langchain_core.tools import StructuredTool`

#### 🏛️ Classes (1)

##### 📌 `class ToolRegistry`
*Line: 13*

**Docstring:**
`````
Central registry for all tools, supporting groups and filtering.
`````

**Public Methods (6):**
- `def get_all_tools(self) -> list[BaseTool]`
  - *Return all registered tools as LangChain BaseTool instances.*
- `def get_tools_by_groups(self, groups: list[str]) -> list[BaseTool]`
  - *Return tools belonging to specified groups.*
- `def get_filtered_tools(self, allowed_groups: list[str] | None) -> list[BaseTool]`
  - **Docstring:**
  `````
  Filter tools by allowed groups (three-value semantics).
  
  None = all allowed, [] = none allowed, ["a","b"] = only those groups.
  Also excludes runtime-disabled groups.
  `````
- `def get_group_names(self) -> list[str]`
  - *Return unique list of all registered group names.*
- `def get_group_info(self) -> list[dict[str, str]]`
  - *Return group id + description pairs.*
- `def register(self, func: Callable, group: str = '', group_description: str = '') -> BaseTool`
  - **Docstring:**
  `````
  Register a function as a tool.
  
  Args:
      func: The function to register as a tool.
      group: ASCII group identifier, used as prefix in tool name.
             Must match ^[a-zA-Z0-9_-]+$ if provided.
      group_description: Human-readable group description for UI display.
             If not provided, defaults to the group value.
  `````

**Class Variables (4):**
- `_instance: ToolRegistry | None = None`
- `_global_tools: dict[str, dict[str, Any]] = {}`
- `_group_descriptions: dict[str, str] = {}`
- `_disabled_groups: set[str] = set()`

#### 🔧 Public Functions (5)

- `def tool(func: Callable) -> Callable` `overload`
  - *Line: 109*

- `def tool() -> Callable[[Callable], Callable]` `overload`
  - *Line: 113*

- `def tool(func: Callable | None = None)`
  - *Line: 116*
  - **Docstring:**
  `````
  Decorator to register a function as an agent tool.
  
  Usage:
      @tool
      def my_func(...): ...
  
      @tool(group="file_mgmt", group_description="文件管理")
      def my_func(...): ...
  `````

- `def decorator(fn: Callable) -> Callable`
  - *Line: 128*

- `def wrapper(*args, **kwargs)` `functools.wraps(fn)`
  - *Line: 132*


---

`````python
# lc_agent/tools/registry.py
from __future__ import annotations

import functools
import re
from typing import Any, Callable, overload

from langchain_core.tools import BaseTool, StructuredTool

_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class ToolRegistry:
    """Central registry for all tools, supporting groups and filtering."""

    _instance: ToolRegistry | None = None
    _global_tools: dict[str, dict[str, Any]] = {}
    _group_descriptions: dict[str, str] = {}
    _disabled_groups: set[str] = set()

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_all_tools(self) -> list[BaseTool]:
        """Return all registered tools as LangChain BaseTool instances."""
        return [entry["tool"] for entry in self._global_tools.values()]

    def get_tools_by_groups(self, groups: list[str]) -> list[BaseTool]:
        """Return tools belonging to specified groups."""
        return [
            entry["tool"]
            for entry in self._global_tools.values()
            if entry["group"] in groups
        ]

    def get_filtered_tools(self, allowed_groups: list[str] | None) -> list[BaseTool]:
        """Filter tools by allowed groups (three-value semantics).

        None = all allowed, [] = none allowed, ["a","b"] = only those groups.
        Also excludes runtime-disabled groups.
        """
        if allowed_groups is None:
            tools = self.get_all_tools()
        elif not allowed_groups:
            return []
        else:
            tools = self.get_tools_by_groups(allowed_groups)

        if self._disabled_groups:
            tools = [
                t for t in tools
                if self._global_tools.get(t.name, {}).get("group") not in self._disabled_groups
            ]
        return tools

    def get_group_names(self) -> list[str]:
        """Return unique list of all registered group names."""
        groups = set()
        for entry in self._global_tools.values():
            if entry["group"]:
                groups.add(entry["group"])
        return sorted(groups)

    def get_group_info(self) -> list[dict[str, str]]:
        """Return group id + description pairs."""
        groups = {}
        for entry in self._global_tools.values():
            g = entry["group"]
            if g and g not in groups:
                groups[g] = self._group_descriptions.get(g, g)
        return [{"id": gid, "description": desc} for gid, desc in sorted(groups.items())]

    def register(self, func: Callable, group: str = "", group_description: str = "") -> BaseTool:
        """Register a function as a tool.

        Args:
            func: The function to register as a tool.
            group: ASCII group identifier, used as prefix in tool name.
                   Must match ^[a-zA-Z0-9_-]+$ if provided.
            group_description: Human-readable group description for UI display.
                   If not provided, defaults to the group value.
        """
        if group and not _TOOL_NAME_PATTERN.match(group):
            raise ValueError(
                f"Tool group '{group}' must match ^[a-zA-Z0-9_-]+$. "
                f"Use ASCII for 'group' and put display name in 'group_description'."
            )

        if group:
            name = f"{group}__{func.__name__}"
        else:
            name = func.__name__

        if group and group_description:
            self._group_descriptions[group] = group_description

        lc_tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=func.__doc__ or f"Tool: {name}",
        )
        self._global_tools[name] = {"tool": lc_tool, "group": group, "func": func}
        return lc_tool


@overload
def tool(func: Callable) -> Callable: ...


@overload
def tool(*, group: str = "", group_description: str = "") -> Callable[[Callable], Callable]: ...


def tool(func: Callable | None = None, *, group: str = "", group_description: str = ""):
    """Decorator to register a function as an agent tool.

    Usage:
        @tool
        def my_func(...): ...

        @tool(group="file_mgmt", group_description="文件管理")
        def my_func(...): ...
    """
    registry = ToolRegistry()

    def decorator(fn: Callable) -> Callable:
        registry.register(fn, group=group, group_description=group_description)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

`````

--- **end of file: lc_agent/tools/registry.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/tools/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/tools/__init__.py`

#### 📦 Imports

- `from lc_agent.tools.registry import ToolRegistry`
- `from lc_agent.tools.registry import tool`


---

`````python
# lc_agent/tools/__init__.py
from lc_agent.tools.registry import ToolRegistry, tool

__all__ = ["ToolRegistry", "tool"]

`````

--- **end of file: lc_agent/tools/__init__.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/utils/loggers.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/utils/loggers.py`

#### 📦 Imports

- `import logging`


---

`````python
import logging

debug_logger = logging.getLogger("lc_agent.debug")


mcp_logger = logging.getLogger("lc_agent.mcp")
`````

--- **end of file: lc_agent/utils/loggers.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/agents.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/agents.py`

#### 📦 Imports

- `import uuid`
- `from datetime import datetime`
- `from datetime import timezone`
- `from fastapi import APIRouter`
- `from fastapi import Depends`
- `from fastapi import HTTPException`
- `from fastapi import Request`
- `from fastapi import Response`
- `from pydantic import BaseModel`
- `from sqlalchemy import select`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.core.models import AgentPreset`
- `from lc_agent.db.engine import get_async_session as _get_db_session`
- `from lc_agent.db.models import AgentPresetDB`
- `from lc_agent.server.dependencies import get_engine`
- `from lc_agent.tools.registry import ToolRegistry`

#### 🏛️ Classes (2)

##### 📌 `class AgentCreateRequest(BaseModel)`
*Line: 25*

**Class Variables (7):**
- `name: str`
- `system_prompt: str`
- `default_model: str`
- `allowed_tool_groups: list[str] | None = None`
- `allowed_mcp_servers: list[str] | None = None`
- `allowed_skills: list[str] | None = None`
- `dangerous_tools: list[str] = []`

##### 📌 `class AgentUpdateRequest(BaseModel)`
*Line: 35*

**Class Variables (7):**
- `name: str | None = None`
- `system_prompt: str | None = None`
- `default_model: str | None = None`
- `allowed_tool_groups: list[str] | None = None`
- `allowed_mcp_servers: list[str] | None = None`
- `allowed_skills: list[str] | None = None`
- `dangerous_tools: list[str] | None = None`

#### 🔧 Public Functions (6)

- `async def get_db()`
  - *Line: 17*

- `async def list_agents(engine: AgentEngine = Depends(get_engine), db = Depends(get_db))` `router.get('/agents')`
  - *Line: 61*
  - *List all agent presets (builtin + code + DB-persisted).*

- `async def create_agent(body: AgentCreateRequest, engine: AgentEngine = Depends(get_engine), db = Depends(get_db))` `router.post('/agents', status_code=201)`
  - *Line: 91*
  - *Create a new agent preset (persisted to DB).*

- `async def update_agent(agent_id: str, body: AgentUpdateRequest, engine: AgentEngine = Depends(get_engine), db = Depends(get_db))` `router.put('/agents/{agent_id}')`
  - *Line: 126*
  - *Update an agent preset.*

- `async def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine), db = Depends(get_db))` `router.delete('/agents/{agent_id}', status_code=204)`
  - *Line: 177*
  - *Delete an agent preset.*

- `def activate_agent(agent_id: str, request: Request, engine: AgentEngine = Depends(get_engine))` `router.post('/agents/{agent_id}/activate')`
  - *Line: 200*
  - **Docstring:**
  `````
  Apply an agent's default toggle state to MCP servers and tool groups.
  
  - Agents with default_enabled=False (Empty): disable all MCP + tool groups
  - Agents with default_enabled=True (Power): enable all MCP + tool groups
  - Chat agent (allowed=[]): no change needed (preset blocks everything)
  `````


---

`````python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset
from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.db.models import AgentPresetDB
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["agents"])


async def get_db():
    session = _get_db_session()
    try:
        yield session
    finally:
        await session.close()


class AgentCreateRequest(BaseModel):
    name: str
    system_prompt: str
    default_model: str
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] = []


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    default_model: str | None = None
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] | None = None


def _preset_to_dict(p: AgentPreset) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "system_prompt": p.system_prompt,
        "default_model": p.default_model,
        "allowed_tool_groups": p.allowed_tool_groups,
        "allowed_mcp_servers": p.allowed_mcp_servers,
        "allowed_skills": p.allowed_skills,
        "dangerous_tools": p.dangerous_tools,
        "source": p.source,
        "default_enabled": p.default_enabled,
    }


@router.get("/agents")
async def list_agents(engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """List all agent presets (builtin + code + DB-persisted)."""
    result = []

    for bp in engine.get_builtin_presets():
        result.append(_preset_to_dict(bp))

    for p in engine._custom_presets.values():
        result.append(_preset_to_dict(p))

    stmt = select(AgentPresetDB)
    rows = await db.execute(stmt)
    for row in rows.scalars().all():
        result.append({
            "id": row.id,
            "name": row.name,
            "system_prompt": row.system_prompt,
            "default_model": row.default_model,
            "allowed_tool_groups": row.allowed_tool_groups,
            "allowed_mcp_servers": row.allowed_mcp_servers,
            "allowed_skills": row.allowed_skills,
            "dangerous_tools": row.dangerous_tools,
            "source": "user",
            "default_enabled": True,
        })

    return result


@router.post("/agents", status_code=201)
async def create_agent(body: AgentCreateRequest, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Create a new agent preset (persisted to DB)."""
    preset_db = AgentPresetDB(
        id=str(uuid.uuid4()),
        name=body.name,
        system_prompt=body.system_prompt,
        default_model=body.default_model,
        allowed_tool_groups=body.allowed_tool_groups,
        allowed_mcp_servers=body.allowed_mcp_servers,
        allowed_skills=body.allowed_skills,
        dangerous_tools=body.dangerous_tools,
    )
    db.add(preset_db)
    await db.commit()
    await db.refresh(preset_db)

    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        dangerous_tools=preset_db.dangerous_tools,
    )
    engine._presets[preset.id] = preset

    return {
        **preset.model_dump(),
        "source": "user",
    }


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdateRequest, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Update an agent preset."""
    if agent_id in engine.BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot edit builtin agent")

    update_data = body.model_dump(exclude_unset=True)

    if agent_id in engine._custom_presets:
        allowed_fields = {"allowed_tool_groups", "allowed_mcp_servers", "allowed_skills", "dangerous_tools"}
        invalid_fields = set(update_data.keys()) - allowed_fields
        if invalid_fields:
            raise HTTPException(
                status_code=403,
                detail=f"Code agent only allows modifying: {', '.join(allowed_fields)}. Got: {', '.join(invalid_fields)}"
            )
        existing = engine._custom_presets[agent_id]
        updated = existing.model_copy(update=update_data)
        engine._custom_presets[agent_id] = updated
        return {**updated.model_dump(), "source": "code"}

    stmt = select(AgentPresetDB).where(AgentPresetDB.id == agent_id)
    result = await db.execute(stmt)
    preset_db = result.scalar_one_or_none()
    if preset_db is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    for key, value in update_data.items():
        setattr(preset_db, key, value)
    preset_db.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(preset_db)

    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        dangerous_tools=preset_db.dangerous_tools,
    )
    engine._presets[preset.id] = preset

    if agent_id in engine._agents:
        del engine._agents[agent_id]

    return {**preset.model_dump(), "source": "user"}


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Delete an agent preset."""
    if agent_id in engine.BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot delete builtin agent")
    if agent_id in engine._custom_presets:
        raise HTTPException(status_code=403, detail="Cannot delete code-registered agent")

    stmt = select(AgentPresetDB).where(AgentPresetDB.id == agent_id)
    result = await db.execute(stmt)
    preset_db = result.scalar_one_or_none()
    if preset_db is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(preset_db)
    await db.commit()

    engine._presets.pop(agent_id, None)
    engine._agents.pop(agent_id, None)

    return Response(status_code=204)


@router.post("/agents/{agent_id}/activate")
def activate_agent(agent_id: str, request: Request, engine: AgentEngine = Depends(get_engine)):
    """Apply an agent's default toggle state to MCP servers and tool groups.

    - Agents with default_enabled=False (Empty): disable all MCP + tool groups
    - Agents with default_enabled=True (Power): enable all MCP + tool groups
    - Chat agent (allowed=[]): no change needed (preset blocks everything)
    """
    from lc_agent.tools.registry import ToolRegistry

    preset = engine._resolve_preset(agent_id)
    manager = getattr(request.app.state, "mcp_manager", None)
    registry = ToolRegistry()

    if preset.allowed_tool_groups == [] and preset.allowed_mcp_servers == []:
        return {"agent_id": agent_id, "action": "none", "reason": "preset blocks all"}

    target_enabled = preset.default_enabled

    changed_mcp = []
    if manager:
        for server in manager.servers:
            if server.enabled != target_enabled:
                server.enabled = target_enabled
                if not target_enabled:
                    server.status = "disabled"
                elif server.name in manager._sessions:
                    server.status = "connected"
                else:
                    server.status = "disconnected"
                changed_mcp.append(server.name)

    changed_groups = []
    for group in registry.get_group_names():
        is_disabled = group in registry._disabled_groups
        if target_enabled and is_disabled:
            registry._disabled_groups.discard(group)
            changed_groups.append(group)
        elif not target_enabled and not is_disabled:
            registry._disabled_groups.add(group)
            changed_groups.append(group)

    if changed_mcp or changed_groups:
        engine._mcp_generation += 1

    return {
        "agent_id": agent_id,
        "default_enabled": target_enabled,
        "changed_mcp": changed_mcp,
        "changed_groups": changed_groups,
    }

`````

--- **end of file: lc_agent/server/routes/agents.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/health.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/health.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import Request`
- `from lc_agent import __version__`

#### 🔧 Public Functions (1)

- `async def health(request: Request)` `router.get('/health')`
  - *Line: 10*
  - *Health check endpoint.*


---

`````python
# lc_agent/server/routes/health.py
from fastapi import APIRouter, Request

from lc_agent import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """Health check endpoint."""
    config = request.app.state.config
    return {
        "status": "ok",
        "version": __version__,
        "config_loaded": config.get("_config_path") is not None,
    }

`````

--- **end of file: lc_agent/server/routes/health.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/mcp.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/mcp.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import HTTPException`
- `from fastapi import Request`

#### 🔧 Public Functions (2)

- `def list_mcp_servers(request: Request)` `router.get('/mcp')`
  - *Line: 7*
  - *List MCP servers with their status.*

- `def toggle_mcp_server(name: str, request: Request)` `router.post('/mcp/{name}/toggle')`
  - *Line: 28*
  - *Toggle a MCP server's enabled state at runtime.*


---

`````python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["mcp"])


@router.get("/mcp")
def list_mcp_servers(request: Request):
    """List MCP servers with their status."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        return []
    return [
        {
            "name": s.name,
            "type": s.type,
            "command": s.command,
            "url": s.url,
            "enabled": s.enabled,
            "status": s.status,
            "tools": s.tools,
            "error": s.error,
        }
        for s in manager.servers
    ]


@router.post("/mcp/{name}/toggle")
def toggle_mcp_server(name: str, request: Request):
    """Toggle a MCP server's enabled state at runtime."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="MCP manager not found")
    server = manager.get_server(name)
    if server is None:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    server.enabled = not server.enabled
    if not server.enabled:
        server.status = "disabled"
    else:
        has_session = name in manager._sessions
        if has_session:
            server.status = "connected"
        else:
            server.status = "disconnected"
    engine = getattr(request.app.state, "engine", None)
    if engine:
        engine._mcp_generation += 1
    return {"name": name, "enabled": server.enabled, "status": server.status}

`````

--- **end of file: lc_agent/server/routes/mcp.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/models.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/models.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import Depends`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.server.dependencies import get_engine`

#### 🔧 Public Functions (1)

- `def list_models(engine: AgentEngine = Depends(get_engine))` `router.get('/models')`
  - *Line: 10*
  - *List all configured models.*


---

`````python
from fastapi import APIRouter, Depends

from lc_agent.core.engine import AgentEngine
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models(engine: AgentEngine = Depends(get_engine)):
    """List all configured models."""
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "base_url": m.base_url,
            "context_limit": m.context_limit,
        }
        for m in engine.get_models()
    ]

`````

--- **end of file: lc_agent/server/routes/models.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/sessions.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/sessions.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import Depends`
- `from fastapi import HTTPException`
- `from fastapi import Request`
- `from fastapi import Response`
- `from pydantic import BaseModel`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from lc_agent.db.repository import SessionRepository`
- `from lc_agent.server.dependencies import get_db_session`
- `from lc_agent.server.dependencies import get_engine`

#### 🏛️ Classes (2)

##### 📌 `class SessionCreateRequest(BaseModel)`
*Line: 11*

**Class Variables (3):**
- `title: str = '新对话'`
- `agent_id: str = '__chat__'`
- `model: str = ''`

##### 📌 `class SessionUpdateRequest(BaseModel)`
*Line: 17*

**Class Variables (1):**
- `title: str | None = None`

#### 🔧 Public Functions (5)

- `async def list_sessions(db: AsyncSession = Depends(get_db_session))` `router.get('/sessions')`
  - *Line: 22*

- `async def create_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db_session))` `router.post('/sessions', status_code=201)`
  - *Line: 40*

- `async def update_session(session_id: str, body: SessionUpdateRequest, db: AsyncSession = Depends(get_db_session))` `router.put('/sessions/{session_id}')`
  - *Line: 47*

- `async def delete_session(session_id: str, db: AsyncSession = Depends(get_db_session))` `router.delete('/sessions/{session_id}', status_code=204)`
  - *Line: 57*

- `async def get_session_messages(session_id: str, request: Request)` `router.get('/sessions/{session_id}/messages')`
  - *Line: 66*
  - *Retrieve message history for a session from the LangGraph checkpoint.*


---

`````python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.repository import SessionRepository
from lc_agent.server.dependencies import get_db_session, get_engine

router = APIRouter(tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"
    agent_id: str = "__chat__"
    model: str = ""


class SessionUpdateRequest(BaseModel):
    title: str | None = None


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    sessions = await repo.list_all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "agent_id": s.agent_id,
            "model": s.model,
            "message_count": s.message_count,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.post("/sessions", status_code=201)
async def create_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    session = await repo.create(title=body.title, agent_id=body.agent_id, model=body.model)
    return {"id": session.id, "title": session.title}


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    update_data = body.model_dump(exclude_unset=True)
    result = await repo.update(session_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": result.id, "title": result.title}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request):
    """Retrieve message history for a session from the LangGraph checkpoint."""
    engine = request.app.state.engine
    checkpointer = engine._checkpointer
    if checkpointer is None:
        return []

    try:
        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple is None:
            return []

        checkpoint = checkpoint_tuple.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        result = []
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

            item = {"role": msg_type, "content": content}

            if tool_calls:
                item["tool_calls"] = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {}), "id": tc.get("id", "")}
                    for tc in tool_calls
                ]

            if msg_type == "tool":
                item["tool_call_id"] = getattr(msg, "tool_call_id", "")
                item["name"] = getattr(msg, "name", "")

            result.append(item)

        return result
    except Exception as e:
        print(f"[Sessions] Failed to load messages for {session_id}: {e}")
        return []

`````

--- **end of file: lc_agent/server/routes/sessions.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/skills.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/skills.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import HTTPException`
- `from fastapi import Request`

#### 🔧 Public Functions (3)

- `def list_skills(request: Request)` `router.get('/skills')`
  - *Line: 7*
  - *List discovered skills.*

- `def toggle_skill(name: str, request: Request)` `router.post('/skills/{name}/toggle')`
  - *Line: 25*
  - *Toggle a skill's enabled state at runtime.*

- `def list_skill_groups(request: Request)` `router.get('/skills/groups')`
  - *Line: 43*
  - *List skills grouped by their metadata.group field.*


---

`````python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["skills"])


@router.get("/skills")
def list_skills(request: Request):
    """List discovered skills."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []
    return [
        {
            "name": s.name,
            "description": s.description,
            "group": s.group,
            "file_path": s.file_path,
            "enabled": s.name not in scanner._disabled_skills,
        }
        for s in scanner.skills
    ]


@router.post("/skills/{name}/toggle")
def toggle_skill(name: str, request: Request):
    """Toggle a skill's enabled state at runtime."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        raise HTTPException(status_code=404, detail="Skill scanner not found")
    skill = next((s for s in scanner.skills if s.name == name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if name in scanner._disabled_skills:
        scanner._disabled_skills.discard(name)
        enabled = True
    else:
        scanner._disabled_skills.add(name)
        enabled = False
    return {"name": name, "enabled": enabled}


@router.get("/skills/groups")
def list_skill_groups(request: Request):
    """List skills grouped by their metadata.group field."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []

    groups: dict[str, list] = {}
    for s in scanner.skills:
        group_name = s.group or "__ungrouped__"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({"name": s.name, "description": s.description})

    return [
        {"group": g, "skills": skills}
        for g, skills in sorted(groups.items())
    ]

`````

--- **end of file: lc_agent/server/routes/skills.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/tools.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/tools.py`

#### 📦 Imports

- `from fastapi import APIRouter`
- `from fastapi import Depends`
- `from fastapi import Request`
- `from lc_agent.core.engine import AgentEngine`
- `from lc_agent.server.dependencies import get_engine`
- `from lc_agent.server.dependencies import get_registry`
- `from lc_agent.tools.registry import ToolRegistry`

#### 🔧 Public Functions (3)

- `def list_tools(registry: ToolRegistry = Depends(get_registry))` `router.get('/tools')`
  - *Line: 11*
  - *List all registered tools.*

- `def list_tool_groups(registry: ToolRegistry = Depends(get_registry))` `router.get('/tools/groups')`
  - *Line: 26*
  - *List tool groups with their tools.*

- `def toggle_tool_group(group_id: str, registry: ToolRegistry = Depends(get_registry), engine: AgentEngine = Depends(get_engine))` `router.post('/tools/groups/{group_id}/toggle')`
  - *Line: 50*
  - *Toggle a tool group's enabled state.*


---

`````python
from fastapi import APIRouter, Depends, Request

from lc_agent.core.engine import AgentEngine
from lc_agent.server.dependencies import get_engine, get_registry
from lc_agent.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools(registry: ToolRegistry = Depends(get_registry)):
    """List all registered tools."""
    tools = []
    for name, entry in registry._global_tools.items():
        group = entry["group"]
        tools.append({
            "name": name,
            "group": group,
            "group_description": registry._group_descriptions.get(group, group),
            "description": entry["tool"].description,
        })
    return tools


@router.get("/tools/groups")
def list_tool_groups(registry: ToolRegistry = Depends(get_registry)):
    """List tool groups with their tools."""
    groups: dict[str, list] = {}
    for name, entry in registry._global_tools.items():
        group_name = entry["group"] or "__ungrouped__"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({
            "name": name,
            "description": entry["tool"].description,
        })
    disabled = registry._disabled_groups
    return [
        {
            "id": group,
            "description": registry._group_descriptions.get(group, group),
            "tools": tools,
            "enabled": group not in disabled,
        }
        for group, tools in sorted(groups.items())
    ]


@router.post("/tools/groups/{group_id}/toggle")
def toggle_tool_group(
    group_id: str,
    registry: ToolRegistry = Depends(get_registry),
    engine: AgentEngine = Depends(get_engine),
):
    """Toggle a tool group's enabled state."""
    if group_id in registry._disabled_groups:
        registry._disabled_groups.discard(group_id)
        enabled = True
    else:
        registry._disabled_groups.add(group_id)
        enabled = False
    engine._mcp_generation += 1
    return {"id": group_id, "enabled": enabled}

`````

--- **end of file: lc_agent/server/routes/tools.py** (project: lc_agent) --- 

---


--- **start of file: lc_agent/server/routes/__init__.py** (project: lc_agent) --- 


### 📄 Python File Metadata: `lc_agent/server/routes/__init__.py`


---

`````python


`````

--- **end of file: lc_agent/server/routes/__init__.py** (project: lc_agent) --- 

---

# markdown content namespace: lc_agent 前端源码 (Vue 3) 


## lc_agent File Tree (relative dir: `frontend/src`)


`````

└── frontend
    └── src
        ├── App.vue
        ├── api
        │   ├── http.ts
        │   └── websocket.ts
        ├── components
        │   ├── chat
        │   │   ├── ChatBubble.vue
        │   │   ├── ChatInput.vue
        │   │   ├── InterruptDialog.vue
        │   │   ├── TokenUsagePanel.vue
        │   │   └── ToolCallCard.vue
        │   ├── dialogs
        │   │   └── AgentEditorDialog.vue
        │   ├── layout
        │   │   ├── AppHeader.vue
        │   │   ├── LeftSidebar.vue
        │   │   └── RightPanel.vue
        │   └── panels
        │       ├── ModelSelector.vue
        │       └── ToolGroupPanel.vue
        ├── composables
        │   └── useTheme.ts
        ├── main.ts
        ├── router
        │   └── index.ts
        ├── stores
        │   ├── agents.ts
        │   ├── chat.ts
        │   ├── sessions.ts
        │   └── tools.ts
        ├── utils
        │   └── markdown.ts
        └── views
            ├── ChatView.vue
            └── TestSegments.vue

`````

---


## lc_agent (relative dir: `frontend/src`)  Included Files (total: 24 files)


- `frontend/src/App.vue`

- `frontend/src/main.ts`

- `frontend/src/api/http.ts`

- `frontend/src/api/websocket.ts`

- `frontend/src/composables/useTheme.ts`

- `frontend/src/router/index.ts`

- `frontend/src/stores/agents.ts`

- `frontend/src/stores/chat.ts`

- `frontend/src/stores/sessions.ts`

- `frontend/src/stores/tools.ts`

- `frontend/src/utils/markdown.ts`

- `frontend/src/views/ChatView.vue`

- `frontend/src/views/TestSegments.vue`

- `frontend/src/components/chat/ChatBubble.vue`

- `frontend/src/components/chat/ChatInput.vue`

- `frontend/src/components/chat/InterruptDialog.vue`

- `frontend/src/components/chat/TokenUsagePanel.vue`

- `frontend/src/components/chat/ToolCallCard.vue`

- `frontend/src/components/dialogs/AgentEditorDialog.vue`

- `frontend/src/components/layout/AppHeader.vue`

- `frontend/src/components/layout/LeftSidebar.vue`

- `frontend/src/components/layout/RightPanel.vue`

- `frontend/src/components/panels/ModelSelector.vue`

- `frontend/src/components/panels/ToolGroupPanel.vue`


---


--- **start of file: frontend/src/App.vue** (project: lc_agent) --- 

`````vue
<template>
  <ConfigProvider :theme="isDark ? 'dark' : 'light'">
  <div class="app-container">
    <AppHeader
      :model-name="toolsStore.currentModel || agentsStore.currentAgent?.default_model || 'N/A'"
      :connected="chatStore.isConnected"
      @edit-agent="editCurrentAgent"
      @new-agent="createNewAgent"
      @new-chat="handleNewChat"
    />

    <div class="app-body">
      <LeftSidebar
        :collapsed="sidebarCollapsed"
        @new-chat="handleNewChat"
        @switch-session="handleSwitchSession"
        @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      />

      <main class="chat-main">
        <router-view />
      </main>

      <RightPanel />
    </div>

    <AgentEditorDialog ref="agentEditorRef" />
  </div>
  </ConfigProvider>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ConfigProvider } from 'vue-element-plus-x'
import { useTheme } from '@/composables/useTheme'
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore } from '@/stores/agents'
import { useSessionsStore } from '@/stores/sessions'
import AppHeader from '@/components/layout/AppHeader.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightPanel from '@/components/layout/RightPanel.vue'
import AgentEditorDialog from '@/components/dialogs/AgentEditorDialog.vue'

const { isDark } = useTheme()

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()
const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()
const sessionsStore = useSessionsStore()
const agentEditorRef = ref<InstanceType<typeof AgentEditorDialog>>()
const sidebarCollapsed = ref(false)
let skipAgentWatch = false

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
    sessionsStore.init(),
  ])

  const agentQuery = route.query.agent as string
  if (agentQuery && agentsStore.agents.find(a => a.id === agentQuery)) {
    agentsStore.selectAgent(agentQuery)
  }

  const sessionId = route.params.sessionId as string
  if (sessionId) {
    restoreSession(sessionId)
  }
})

watch(() => route.params.sessionId, (newId) => {
  if (newId && typeof newId === 'string') {
    restoreSession(newId)
  }
})

async function restoreSession(sessionId: string) {
  if (chatStore.threadId === sessionId) return
  const session = sessionsStore.sessions.find(s => s.id === sessionId)
  if (session) {
    sessionsStore.selectSession(sessionId)
    if (session.agent_id && session.agent_id !== agentsStore.currentAgentId) {
      skipAgentWatch = true
      agentsStore.selectAgent(session.agent_id)
    }
    chatStore.clearMessages()
    chatStore.disconnect()
    await chatStore.loadMessages(sessionId)
    chatStore.connect(sessionId)
  }
}

function handleNewChat() {
  const session = sessionsStore.createLocalSession(agentsStore.currentAgentId)
  chatStore.clearMessages()
  chatStore.disconnect()
  router.push({ name: 'chat', params: { sessionId: session.id }, query: { agent: agentsStore.currentAgentId } })
}

async function handleSwitchSession(sessionId: string) {
  if (chatStore.threadId === sessionId) {
    const session = sessionsStore.sessions.find(s => s.id === sessionId)
    const agentId = session?.agent_id || agentsStore.currentAgentId
    router.push({ name: 'chat', params: { sessionId }, query: { agent: agentId } })
    return
  }
  const session = sessionsStore.sessions.find(s => s.id === sessionId)
  sessionsStore.selectSession(sessionId)
  chatStore.clearMessages()
  chatStore.disconnect()
  await chatStore.loadMessages(sessionId)
  chatStore.connect(sessionId)
  const agentId = session?.agent_id || agentsStore.currentAgentId
  if (session?.agent_id && session.agent_id !== agentsStore.currentAgentId) {
    skipAgentWatch = true
    agentsStore.selectAgent(session.agent_id)
  }
  router.push({ name: 'chat', params: { sessionId }, query: { agent: agentId } })
}

watch(() => agentsStore.currentAgentId, (newAgentId) => {
  if (skipAgentWatch) {
    skipAgentWatch = false
    return
  }
  if (route.name === 'home' || route.name === 'chat') {
    const session = sessionsStore.createLocalSession(newAgentId)
    chatStore.clearMessages()
    chatStore.disconnect()
    router.push({ name: 'chat', params: { sessionId: session.id }, query: { agent: newAgentId } })
  }
})

function editCurrentAgent() {
  agentEditorRef.value?.open(agentsStore.currentAgent)
}

function createNewAgent() {
  agentEditorRef.value?.open()
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--el-bg-color-page);
  position: relative;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>

`````

--- **end of file: frontend/src/App.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/main.ts** (project: lc_agent) --- 

`````typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')

`````

--- **end of file: frontend/src/main.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/api/http.ts** (project: lc_agent) --- 

`````typescript
const BASE_URL = '/api'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string }>('/health'),

  getTools: () => fetchApi<{ name: string; group: string; group_description: string; description: string }[]>('/tools'),
  getToolGroups: () => fetchApi<{ id: string; description: string; tools: { name: string; description: string }[]; enabled: boolean }[]>('/tools/groups'),
  toggleToolGroup: (groupId: string) => fetchApi<{ id: string; enabled: boolean }>(`/tools/groups/${groupId}/toggle`, { method: 'POST' }),

  getModels: () => fetchApi<{ id: string; provider: string; base_url: string; context_limit: number }[]>('/models'),

  getMcpServers: () => fetchApi<any[]>('/mcp'),
  toggleMcpServer: (name: string) => fetchApi<{ name: string; enabled: boolean }>(`/mcp/${name}/toggle`, { method: 'POST' }),
  getSkills: () => fetchApi<any[]>('/skills'),
  toggleSkill: (name: string) => fetchApi<{ name: string; enabled: boolean }>(`/skills/${name}/toggle`, { method: 'POST' }),

  getAgents: () => fetchApi<any[]>('/agents'),
  createAgent: (data: object) => fetchApi<any>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id: string, data: object) => fetchApi<any>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => fetchApi<void>(`/agents/${id}`, { method: 'DELETE' }),
  activateAgent: (id: string) => fetchApi<any>(`/agents/${id}/activate`, { method: 'POST' }),

  getSessions: () => fetchApi<any[]>('/sessions'),
  createSession: (data: { title?: string; agent_id?: string; model?: string }) =>
    fetchApi<{ id: string; title: string }>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  updateSession: (id: string, data: { title?: string }) =>
    fetchApi<any>(`/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSession: (id: string) =>
    fetchApi<void>(`/sessions/${id}`, { method: 'DELETE' }),
  getSessionMessages: (id: string) =>
    fetchApi<any[]>(`/sessions/${id}/messages`),
}

`````

--- **end of file: frontend/src/api/http.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/api/websocket.ts** (project: lc_agent) --- 

`````typescript
export interface WsMessage {
  type: string
  content?: string
  thread_id?: string
  title?: string
  name?: string
  result?: string
  message?: string
  run_id?: string
  args?: Record<string, any>
  action_requests?: any[]
  review_configs?: any[]
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cache_read_tokens?: number
  usage?: any[]
}

export type WsEventHandler = (msg: WsMessage) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private handlers: Map<string, WsEventHandler[]> = new Map()
  private _threadId: string | null = null

  constructor(baseUrl: string = '') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = baseUrl || window.location.host
    this.url = `${protocol}//${host}/ws/chat`
  }

  get threadId() { return this._threadId }
  get connected() { return this.ws?.readyState === WebSocket.OPEN }

  connect(threadId?: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const url = threadId ? `${this.url}/${threadId}` : this.url
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('[WS] Connected')
      }

      this.ws.onmessage = (event) => {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'connected') {
          this._threadId = msg.thread_id || null
          resolve(this._threadId!)
        }
        this.emit(msg.type, msg)
      }

      this.ws.onerror = (err) => {
        console.error('[WS] Error:', err)
        reject(err)
      }

      this.ws.onclose = () => {
        console.log('[WS] Disconnected')
        this.emit('disconnected', { type: 'disconnected' })
      }
    })
  }

  send(data: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  sendMessage(content: string) {
    this.send({ type: 'message', content })
  }

  sendInterruptResponse(approved: boolean, presetId: string) {
    this.send({
      type: 'interrupt_response',
      approved,
      preset_id: presetId,
    })
  }

  sendCancel() {
    this.send({ type: 'cancel' })
  }

  on(event: string, handler: WsEventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, [])
    }
    this.handlers.get(event)!.push(handler)
  }

  off(event: string, handler: WsEventHandler) {
    const handlers = this.handlers.get(event)
    if (handlers) {
      const idx = handlers.indexOf(handler)
      if (idx >= 0) handlers.splice(idx, 1)
    }
  }

  private emit(event: string, msg: WsMessage) {
    const handlers = this.handlers.get(event) || []
    handlers.forEach(h => h(msg))
    const allHandlers = this.handlers.get('*') || []
    allHandlers.forEach(h => h(msg))
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
    this._threadId = null
  }
}

`````

--- **end of file: frontend/src/api/websocket.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/composables/useTheme.ts** (project: lc_agent) --- 

`````typescript
import { useDark, useToggle } from '@vueuse/core'

export function useTheme() {
  const isDark = useDark({
    selector: 'html',
    attribute: 'class',
    valueDark: 'dark',
    valueLight: '',
  })
  const toggleDark = useToggle(isDark)

  return { isDark, toggleDark }
}

`````

--- **end of file: frontend/src/composables/useTheme.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/router/index.ts** (project: lc_agent) --- 

`````typescript
import { createRouter, createWebHashHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: ChatView,
    },
    {
      path: '/c/:sessionId',
      name: 'chat',
      component: ChatView,
      props: true,
    },
    {
      path: '/test-segments',
      name: 'test-segments',
      component: () => import('@/views/TestSegments.vue'),
    },
  ],
})

export default router

`````

--- **end of file: frontend/src/router/index.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/stores/agents.ts** (project: lc_agent) --- 

`````typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

export interface AgentPreset {
  id: string
  name: string
  system_prompt: string
  default_model: string
  allowed_tool_groups: string[] | null
  allowed_mcp_servers: string[] | null
  allowed_skills: string[] | null
  dangerous_tools: string[]
  source: 'builtin' | 'code' | 'user'
  default_enabled: boolean
}

const BUILTIN_IDS = new Set(['__chat__', '__empty__', '__power__'])

export const useAgentsStore = defineStore('agents', () => {
  const agents = ref<AgentPreset[]>([])
  const currentAgentId = ref('__chat__')

  const currentAgent = computed(() =>
    agents.value.find(a => a.id === currentAgentId.value) || agents.value[0]
  )

  const isBuiltin = computed(() => BUILTIN_IDS.has(currentAgentId.value))

  const isChatAgent = computed(() => currentAgentId.value === '__chat__')

  async function init() {
    try {
      agents.value = await api.getAgents()
    } catch (e) {
      console.error('[AgentsStore] Failed to fetch:', e)
    }
  }

  async function createAgent(data: Omit<AgentPreset, 'id'>) {
    const created = await api.createAgent(data)
    agents.value.push(created)
    return created
  }

  async function updateAgent(id: string, data: Partial<AgentPreset>) {
    const updated = await api.updateAgent(id, data)
    const idx = agents.value.findIndex(a => a.id === id)
    if (idx >= 0) agents.value[idx] = updated
    return updated
  }

  async function deleteAgent(id: string) {
    if (BUILTIN_IDS.has(id)) return
    await api.deleteAgent(id)
    agents.value = agents.value.filter(a => a.id !== id)
    if (currentAgentId.value === id) currentAgentId.value = '__chat__'
  }

  async function selectAgent(id: string) {
    currentAgentId.value = id
    try {
      await api.activateAgent(id)
    } catch {
      // Non-critical: agent may still work without explicit activation
    }
  }

  function getAgentName(agentId: string): string {
    const agent = agents.value.find(a => a.id === agentId)
    return agent?.name || agentId
  }

  function isAgentBuiltin(id: string): boolean {
    return BUILTIN_IDS.has(id)
  }

  return {
    agents,
    currentAgentId,
    currentAgent,
    isBuiltin,
    isChatAgent,
    init,
    createAgent,
    updateAgent,
    deleteAgent,
    selectAgent,
    getAgentName,
    isAgentBuiltin,
  }
})

`````

--- **end of file: frontend/src/stores/agents.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/stores/chat.ts** (project: lc_agent) --- 

`````typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ChatWebSocket, type WsMessage } from '@/api/websocket'
import { useSessionsStore } from '@/stores/sessions'
import { api } from '@/api/http'

export interface LlmRoundUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  cacheReadTokens: number
  reasoningTokens: number
  duration?: number
}

export interface MessageUsage {
  rounds: LlmRoundUsage[]
  toolCallCount: number
  totalDuration?: number
}

export interface ContentSegment {
  type: 'text' | 'tool'
  text?: string
  toolCall?: ToolCall
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  isStreaming?: boolean
  usage?: MessageUsage
}

export interface ToolCall {
  name: string
  args?: Record<string, any>
  result?: string
  status: 'pending' | 'running' | 'done' | 'error'
  startTime?: number
  duration?: number
  resultLength?: number
}

export interface InterruptInfo {
  actionRequests: any[]
  reviewConfigs: any[]
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isConnected = ref(false)
  const threadId = ref<string | null>(null)
  const interrupt = ref<InterruptInfo | null>(null)
  const ws = ref<ChatWebSocket | null>(null)

  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  async function connect(existingThreadId?: string) {
    ws.value = new ChatWebSocket()

    let streamStartTime = 0
    let currentRoundStart = 0
    let inThinking = false

    ws.value.on('thinking', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (!inThinking) {
          inThinking = true
          last.content += '<!--THINK_START-->'
        }
        last.content += msg.content || ''
      }
    })

    ws.value.on('token', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (inThinking) {
          inThinking = false
          last.content += '<!--THINK_END-->'
        }
        last.content += msg.content || ''
      }
    })

    ws.value.on('llm_usage', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.usage) {
        const roundDuration = currentRoundStart ? Date.now() - currentRoundStart : undefined
        last.usage.rounds.push({
          inputTokens: msg.input_tokens || 0,
          outputTokens: msg.output_tokens || 0,
          totalTokens: msg.total_tokens || 0,
          cacheReadTokens: msg.cache_read_tokens || 0,
          reasoningTokens: 0,
          duration: roundDuration,
        })
        currentRoundStart = Date.now()
      }
    })


    ws.value.on('tool_call', (msg: WsMessage) => {
      if (!isStreaming.value) {
        isStreaming.value = true
        streamStartTime = Date.now()
        currentRoundStart = Date.now()
        messages.value.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
          usage: { rounds: [], toolCallCount: 0 },
        })
      }
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        if (inThinking) {
          inThinking = false
          last.content += '<!--THINK_END-->'
        }
        if (!last.toolCalls) last.toolCalls = []
        const tcIdx = last.toolCalls.length
        const tc: ToolCall = {
          name: msg.name || '',
          args: msg.args,
          status: 'running',
          startTime: Date.now(),
        }
        last.toolCalls.push(tc)
        last.content += `\n<!--TOOL:${tcIdx}-->\n`
        if (last.usage) {
          last.usage.toolCallCount++
        }
      }
    })

    ws.value.on('tool_result', (msg: WsMessage) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.toolCalls) {
        const tc = last.toolCalls.find(t => t.name === msg.name && t.status === 'running')
        if (tc) {
          tc.result = msg.result
          tc.status = 'done'
          tc.duration = tc.startTime ? Date.now() - tc.startTime : undefined
          tc.resultLength = msg.result?.length || 0
        }
      }
    })

    ws.value.on('interrupt', (msg: WsMessage) => {
      interrupt.value = {
        actionRequests: msg.action_requests || [],
        reviewConfigs: msg.review_configs || [],
      }
    })

    ws.value.on('done', (msg: WsMessage) => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) {
        last.isStreaming = false
        if (last.usage && streamStartTime) {
          last.usage.totalDuration = Date.now() - streamStartTime
        }
        const usageData = (msg as any).usage as any[] | undefined
        if (usageData && usageData.length > 0 && last.usage) {
          if (last.usage.rounds.length === 0) {
            const newRounds = usageData.map((r: any) => ({
              inputTokens: r.input_tokens || 0,
              outputTokens: r.output_tokens || 0,
              totalTokens: r.total_tokens || 0,
              cacheReadTokens: r.cache_read_tokens || 0,
              reasoningTokens: r.reasoning_tokens || 0,
              duration: r.duration_ms || undefined,
            }))
            last.usage.rounds.splice(0, last.usage.rounds.length, ...newRounds)
          }
        }
      }
    })

    ws.value.on('cancelled', () => {
      isStreaming.value = false
      const last = messages.value[messages.value.length - 1]
      if (last) last.isStreaming = false
    })

    ws.value.on('error', (msg: WsMessage) => {
      isStreaming.value = false
      console.error('[Chat] Error:', msg.message)
    })

    ws.value.on('history', (msg: WsMessage) => {
      const historyMessages = (msg as any).messages || []
      messages.value = historyMessages.map((m: any, idx: number) => ({
        id: crypto.randomUUID(),
        role: m.role === 'human' ? 'user' : m.role === 'ai' ? 'assistant' : m.role,
        content: m.content || '',
        timestamp: Date.now() - (historyMessages.length - idx) * 1000,
      }))
    })

    ws.value.on('title_update', (msg: WsMessage) => {
      if (msg.thread_id && msg.title) {
        const sessionsStore = useSessionsStore()
        sessionsStore.updateTitleLocal(msg.thread_id, msg.title)
      }
    })

    try {
      const tid = await ws.value.connect(existingThreadId)
      threadId.value = tid
      isConnected.value = true
    } catch (e) {
      console.error('[Chat] Failed to connect:', e)
      isConnected.value = false
    }
  }

  async function sendMessage(content: string, presetId: string = '__chat__') {
    if (!content.trim()) return

    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId && sessionsStore.isLocalSession(sessionId)) {
      const isFirstMessage = sessionsStore.currentSession?.message_count === 0
      const realId = await sessionsStore.persistSession(sessionId)
      // Always reconnect with the persisted session ID
      ws.value?.disconnect()
      await connect(realId)
      // Immediately show user's message as title for new conversations
      if (isFirstMessage) {
        sessionsStore.updateTitleLocal(realId, content.trim().slice(0, 30))
      }
    } else if (!ws.value || !isConnected.value) {
      if (sessionId) await connect(sessionId)
    }

    if (!ws.value) return

    messages.value.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    })

    ws.value.send({
      type: 'message',
      content: content.trim(),
      preset_id: presetId,
    })
  }

  function respondToInterrupt(approved: boolean, presetId: string = '__chat__') {
    ws.value?.sendInterruptResponse(approved, presetId)
    interrupt.value = null
  }

  async function loadMessages(sessionId: string) {
    try {
      const rawMessages = await api.getSessionMessages(sessionId)
      if (!rawMessages || rawMessages.length === 0) return

      const loaded: ChatMessage[] = []
      for (const msg of rawMessages) {
        if (msg.role === 'human') {
          loaded.push({
            id: crypto.randomUUID(),
            role: 'user',
            content: msg.content || '',
            timestamp: Date.now(),
          })
        } else if (msg.role === 'ai') {
          const chatMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: msg.content || '',
            timestamp: Date.now(),
          }
          if (msg.tool_calls && msg.tool_calls.length > 0) {
            chatMsg.toolCalls = msg.tool_calls.map((tc: any) => ({
              name: tc.name,
              args: tc.args || {},
              status: 'done' as const,
            }))
          }
          loaded.push(chatMsg)
        } else if (msg.role === 'tool') {
          const lastAssistant = [...loaded].reverse().find(m => m.role === 'assistant')
          if (lastAssistant?.toolCalls) {
            const tc = lastAssistant.toolCalls.find(t => t.name === msg.name && !t.result)
            if (tc) {
              const resultStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
              tc.result = resultStr
              tc.resultLength = resultStr.length
            }
          }
        }
      }
      messages.value = loaded
    } catch (e) {
      console.error('[Chat] Failed to load messages:', e)
    }
  }

  function stopGeneration() {
    if (ws.value && isStreaming.value) {
      ws.value.sendCancel()
    }
  }

  function clearMessages() {
    messages.value = []
  }

  function disconnect() {
    ws.value?.disconnect()
    isConnected.value = false
  }

  return {
    messages,
    isStreaming,
    isConnected,
    threadId,
    interrupt,
    lastMessage,
    connect,
    loadMessages,
    sendMessage,
    stopGeneration,
    respondToInterrupt,
    clearMessages,
    disconnect,
  }
})

`````

--- **end of file: frontend/src/stores/chat.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/stores/sessions.ts** (project: lc_agent) --- 

`````typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'

export interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  created_at: string
  updated_at: string
}

export const useSessionsStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const localSessionIds = ref<Set<string>>(new Set())

  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value)
  )

  function isLocalSession(id: string): boolean {
    return localSessionIds.value.has(id)
  }

  async function init() {
    try {
      sessions.value = await api.getSessions()
    } catch (e) {
      console.error('[SessionsStore] Failed to fetch:', e)
    }
  }

  function createLocalSession(agentId: string = '__chat__', model: string = ''): Session {
    const existing = sessions.value.find(
      s => s.agent_id === agentId && s.message_count === 0 && localSessionIds.value.has(s.id)
    )
    if (existing) {
      currentSessionId.value = existing.id
      return existing
    }

    const id = crypto.randomUUID()
    const session: Session = {
      id,
      title: '新对话',
      agent_id: agentId,
      model,
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    sessions.value.unshift(session)
    localSessionIds.value.add(id)
    currentSessionId.value = id
    return session
  }

  async function persistSession(id: string): Promise<string> {
    if (!localSessionIds.value.has(id)) return id
    const session = sessions.value.find(s => s.id === id)
    if (!session) return id

    const created = await api.createSession({
      agent_id: session.agent_id,
      model: session.model,
    })
    localSessionIds.value.delete(id)
    const newId = created.id || id
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx >= 0) {
      sessions.value[idx] = { ...sessions.value[idx], ...created, id: newId }
    }
    if (currentSessionId.value === id) {
      currentSessionId.value = newId
    }
    return newId
  }

  async function createSession(agentId: string = '__chat__', model: string = '') {
    const created = await api.createSession({ agent_id: agentId, model })
    sessions.value.unshift({
      ...created,
      agent_id: agentId,
      model,
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    currentSessionId.value = created.id
    return created
  }

  async function deleteSession(id: string) {
    await api.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0]?.id || null
    }
  }

  async function updateTitle(id: string, title: string) {
    await api.updateSession(id, { title })
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  function updateTitleLocal(id: string, title: string) {
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  const groupedByAgent = computed(() => {
    const agentsStore = useAgentsStore()
    const groups: Record<string, { agentName: string; agentSource: string; sessions: Session[] }> = {}
    for (const s of sessions.value) {
      const key = s.agent_id || '__chat__'
      if (!groups[key]) {
        const agent = agentsStore.agents.find(a => a.id === key)
        groups[key] = {
          agentName: agentsStore.getAgentName(key),
          agentSource: agent?.source || 'user',
          sessions: [],
        }
      }
      groups[key].sessions.push(s)
    }
    return Object.entries(groups).map(([agentId, data]) => ({
      agentId,
      agentName: data.agentName,
      agentSource: data.agentSource,
      sessions: data.sessions,
    }))
  })

  function selectSession(id: string) {
    currentSessionId.value = id
  }

  return { sessions, currentSessionId, currentSession, groupedByAgent, init, createSession, createLocalSession, persistSession, isLocalSession, deleteSession, updateTitle, updateTitleLocal, selectSession }
})

`````

--- **end of file: frontend/src/stores/sessions.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/stores/tools.ts** (project: lc_agent) --- 

`````typescript
import { defineStore } from 'pinia'
import { ref, computed, watch, reactive } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'

export interface ToolGroup {
  id: string
  description: string
  tools: { name: string; description: string }[]
  enabled: boolean
}

export interface ModelInfo {
  id: string
  provider: string
  base_url: string
  context_limit: number
}

export const useToolsStore = defineStore('tools', () => {
  const groups = ref<ToolGroup[]>([])
  const models = ref<ModelInfo[]>([])
  const mcpServers = ref<any[]>([])
  const skills = ref<any[]>([])
  const currentModel = ref('')

  const localOverrides = reactive<Record<string, boolean>>({})

  function _effectiveEnabled(key: string, serverEnabled: boolean): boolean {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return serverEnabled
    if (key in localOverrides) return localOverrides[key]
    return agent.default_enabled ? serverEnabled : false
  }

  const filteredGroups = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return groups.value
    const allowed = agent.allowed_tool_groups
    return groups.value.map(g => ({
      ...g,
      enabled: _effectiveEnabled(`group:${g.id}`, g.enabled) && (allowed === null || allowed.includes(g.id)),
      allowed: allowed === null || allowed.includes(g.id),
    }))
  })

  const filteredMcp = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return mcpServers.value
    const allowed = agent.allowed_mcp_servers
    return mcpServers.value.map((s: any) => ({
      ...s,
      enabled: _effectiveEnabled(`mcp:${s.name}`, s.enabled) && (allowed === null || allowed.includes(s.name)),
      allowed: allowed === null || allowed.includes(s.name),
    }))
  })

  const filteredSkills = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return skills.value
    const allowed = agent.allowed_skills
    return skills.value.map((s: any) => ({
      ...s,
      enabled: _effectiveEnabled(`skill:${s.name}`, s.enabled !== false) && (allowed === null || allowed.includes(s.name)),
      allowed: allowed === null || allowed.includes(s.name),
    }))
  })

  function _clearOverrides() {
    for (const key of Object.keys(localOverrides)) {
      delete localOverrides[key]
    }
  }

  async function init() {
    try {
      const [groupsData, modelsData, mcpData, skillsData] = await Promise.all([
        api.getToolGroups(),
        api.getModels(),
        api.getMcpServers(),
        api.getSkills(),
      ])
      groups.value = groupsData
      models.value = modelsData
      mcpServers.value = mcpData
      skills.value = skillsData
      if (modelsData.length > 0 && !currentModel.value) {
        currentModel.value = modelsData[0].id
      }

      const agentsStore = useAgentsStore()
      watch(() => agentsStore.currentAgentId, () => {
        _clearOverrides()
      })
    } catch (e) {
      console.error('[ToolsStore] Failed to fetch:', e)
    }
  }

  async function toggleGroup(groupId: string) {
    const key = `group:${groupId}`
    const current = _effectiveEnabled(key, groups.value.find(g => g.id === groupId)?.enabled ?? true)
    localOverrides[key] = !current
    try {
      await api.toggleToolGroup(groupId)
      const group = groups.value.find(g => g.id === groupId)
      if (group) group.enabled = !group.enabled
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle group failed:', e)
    }
  }

  async function toggleMcp(serverName: string) {
    const key = `mcp:${serverName}`
    const server = mcpServers.value.find((s: any) => s.name === serverName)
    const current = _effectiveEnabled(key, server?.enabled ?? true)
    localOverrides[key] = !current
    try {
      const result = await api.toggleMcpServer(serverName)
      if (server) {
        server.enabled = !server.enabled
        server.status = result.enabled ? (server.status === 'disabled' ? 'disconnected' : server.status) : 'disabled'
      }
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle MCP failed:', e)
    }
  }

  async function toggleSkill(skillName: string) {
    const key = `skill:${skillName}`
    const skill = skills.value.find((s: any) => s.name === skillName)
    const current = _effectiveEnabled(key, skill?.enabled !== false)
    localOverrides[key] = !current
    try {
      await api.toggleSkill(skillName)
      if (skill) skill.enabled = !skill.enabled
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle skill failed:', e)
    }
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
  }

  return {
    groups, models, mcpServers, skills, currentModel,
    filteredGroups, filteredMcp, filteredSkills,
    init, toggleGroup, toggleMcp, toggleSkill, setModel,
  }
})

`````

--- **end of file: frontend/src/stores/tools.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/utils/markdown.ts** (project: lc_agent) --- 

`````typescript
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

export function renderMarkdown(text: string): string {
  return md.render(text)
}

`````

--- **end of file: frontend/src/utils/markdown.ts** (project: lc_agent) --- 

---


--- **start of file: frontend/src/views/ChatView.vue** (project: lc_agent) --- 

`````vue
<template>
  <div class="chat-view">
    <div class="messages-container">
      <Welcome
        v-if="messages.length === 0 && !isLoading"
        title="Start a conversation"
        description="Ask me anything"
        variant="borderless"
      />
      <BubbleList
        v-else
        :list="bubbleList"
        max-height="100%"
        :auto-scroll="isStreaming"
        :virtual="false"
      >
        <template #content="{ item }">
          <div class="bubble-content-wrap">
            <template v-if="item.segments && item.segments.length > 0">
              <template v-for="(seg, segIdx) in item.segments" :key="segIdx">
                <div
                  v-if="seg.type === 'text' && seg.text"
                  class="markdown-body"
                  v-html="renderMarkdown(seg.text)"
                />
                <div v-else-if="seg.type === 'tool' && item.toolCalls && seg.toolIndex != null" class="tool-call-inline">
                  <ToolCallCard
                    :tool-call="item.toolCalls[seg.toolIndex!]"
                    :collapsed="item.toolCalls[seg.toolIndex!]?.status === 'done'"
                  />
                </div>
              </template>
            </template>
            <template v-else>
              <div
                v-if="item.isMarkdown"
                class="markdown-body"
                v-html="renderMarkdown(stripThinkingMarkers(item.content || ''))"
              />
              <span v-else>{{ item.content }}</span>
            </template>
            <TokenUsagePanel
              v-if="item.usage"
              :usage="item.usage"
              :tool-calls="item.toolCalls"
            />
          </div>
        </template>
      </BubbleList>
      <Thinking
        v-if="isLoading && !isStreaming"
        status="thinking"
        content=""
      />
    </div>

    <ChatInput
      :is-streaming="isStreaming"
      @send="handleSend"
      @stop="handleStop"
    />

    <InterruptDialog
      :interrupt="interrupt"
      @decide="handleInterruptDecide"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { BubbleList, Thinking, Welcome } from 'vue-element-plus-x'
import type { BubbleListItemProps } from 'vue-element-plus-x/types/BubbleList'
import { useChatStore } from '@/stores/chat'
import type { ToolCall, MessageUsage } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import { renderMarkdown } from '@/utils/markdown'
import ChatInput from '@/components/chat/ChatInput.vue'
import InterruptDialog from '@/components/chat/InterruptDialog.vue'
import ToolCallCard from '@/components/chat/ToolCallCard.vue'
import TokenUsagePanel from '@/components/chat/TokenUsagePanel.vue'

interface ContentSegment {
  type: 'text' | 'tool'
  text?: string
  toolIndex?: number
}

type ChatBubbleItem = BubbleListItemProps & {
  isMarkdown?: boolean
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  usage?: MessageUsage
}

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const { messages, isStreaming, interrupt } = storeToRefs(chatStore)

const isLoading = computed(() => {
  const msgs = messages.value
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  return last.role === 'user' && !isStreaming.value
})

const bubbleList = computed((): ChatBubbleItem[] =>
  messages.value
    .filter(msg => msg.role === 'user' || msg.role === 'assistant')
    .map((msg, idx, arr) => ({
      key: msg.id,
      role: msg.role === 'assistant' ? 'ai' : 'user',
      placement: msg.role === 'user' ? 'end' : 'start',
      content: msg.content || '',
      shape: 'corner' as const,
      variant: (msg.role === 'user' ? 'outlined' : 'filled') as 'outlined' | 'filled',
      isMarkdown: msg.role !== 'user',
      toolCalls: msg.toolCalls,
      usage: msg.usage,
      segments: msg.role === 'assistant' && msg.toolCalls?.length
        ? parseSegments(msg.content || '', msg.toolCalls)
        : undefined,
      loading:
        msg.role === 'assistant'
        && idx === arr.length - 1
        && isStreaming.value
        && !msg.content,
      avatarSize: '28px',
      avatarGap: '8px',
    })),
)


function stripThinkingMarkers(content: string): string {
  return content.replace(/<!--(?:THINK_START|THINK_END)-->/g, '').trim()
}

function parseSegments(content: string, toolCalls?: ToolCall[]): ContentSegment[] {
  const segments: ContentSegment[] = []
  const pattern = /<!--TOOL:(\d+)-->/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index).trim()
    if (textBefore) {
      segments.push({ type: 'text', text: stripThinkingMarkers(textBefore) })
    }
    const toolIdx = parseInt(match[1], 10)
    if (toolCalls && toolIdx < toolCalls.length) {
      segments.push({ type: 'tool', toolIndex: toolIdx })
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) {
    segments.push({ type: 'text', text: stripThinkingMarkers(remaining) })
  }

  return segments
}

function handleSend(content: string) {
  chatStore.sendMessage(content, agentsStore.currentAgentId)
}

function handleStop() {
  chatStore.stopGeneration()
}

function handleInterruptDecide(decision: { type: string }) {
  chatStore.respondToInterrupt(decision.type === 'approve', agentsStore.currentAgentId)
}


onMounted(() => {
  chatStore.connect()
})
</script>

<style scoped>
.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}

.messages-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  background: var(--el-bg-color-page);
}

.messages-container :deep(.elx-bubble-list) {
  width: 100%;
}

.messages-container :deep(.elx-bubble) {
  max-width: 85% !important;
}

.messages-container :deep(.elx-bubble__content) {
  max-width: none !important;
}

.bubble-content-wrap {
  width: 100%;
}

.tool-call-inline {
  margin: 8px 0;
  position: relative;
  z-index: 1;
  pointer-events: auto !important;
}

.messages-container :deep([style*="pointer-events"]) .tool-call-inline,
.messages-container :deep(.tool-call-card) {
  pointer-events: auto !important;
  cursor: pointer;
}

.messages-container :deep(.markdown-body) {
  line-height: 1.7;
  font-size: 14px;
  overflow-wrap: break-word;
}

.messages-container :deep(.markdown-body pre) {
  border-radius: 8px;
  overflow-x: auto;
}

.messages-container :deep(.elx-welcome) {
  background: var(--el-bg-color-overlay) !important;
  border: 1px solid var(--el-border-color-lighter) !important;
  border-radius: 12px;
  color: var(--el-text-color-primary);
}

.messages-container :deep(.elx-welcome__title) {
  color: var(--el-text-color-primary) !important;
}

.messages-container :deep(.elx-welcome__description) {
  color: var(--el-text-color-secondary) !important;
}
</style>

`````

--- **end of file: frontend/src/views/ChatView.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/views/TestSegments.vue** (project: lc_agent) --- 

`````vue
<template>
  <div style="padding:20px; background:var(--el-bg-color-page); min-height:100vh; color:var(--el-text-color-regular);">
    <h2>Segments Rendering Test</h2>
    <button @click="simulateStream" style="padding:8px 16px; margin:10px 0;">
      Simulate Stream (think → tool → answer)
    </button>
    <button @click="resetMsg" style="padding:8px 16px; margin:10px;">Reset</button>
    <div style="margin:10px 0; font-size:12px; color:var(--el-text-color-secondary);">
      Segments: {{ msg.segments?.length || 0 }} | Content length: {{ msg.content.length }}
    </div>
    <ChatBubble :message="msg" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import type { ChatMessage, ToolCall } from '@/stores/chat'

const msg = ref<ChatMessage>({
  id: 'test-1',
  role: 'assistant',
  content: '',
  timestamp: Date.now(),
  isStreaming: false,
  usage: { rounds: [], toolCallCount: 0 },
})

function resetMsg() {
  msg.value = {
    id: 'test-' + Date.now(),
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
    isStreaming: false,
    usage: { rounds: [], toolCallCount: 0 },
  }
}

async function simulateStream() {
  resetMsg()
  msg.value.isStreaming = true
  
  const addToken = (text: string) => {
    msg.value.content += text
    const segs = msg.value.segments!
    const last = segs[segs.length - 1]
    if (last && last.type === 'text') {
      last.text = (last.text || '') + text
    } else {
      segs.push({ type: 'text', text })
    }
  }
  
  const addTool = (name: string) => {
    const tc: ToolCall = { name, args: { query: 'test' }, status: 'running' }
    if (!msg.value.toolCalls) msg.value.toolCalls = []
    const tcIdx = msg.value.toolCalls.length
    msg.value.toolCalls.push(tc)
    msg.value.content += `\n<!--TOOL:${tcIdx}-->\n`
    msg.value.usage!.toolCallCount++
  }
  
  const finishTool = (name: string) => {
    const tc = msg.value.toolCalls?.find(t => t.name === name && t.status === 'running')
    if (tc) {
      tc.status = 'done'
      tc.result = 'Some result data...'
      tc.duration = 1234
    }
  }
  
  const delay = (ms: number) => new Promise(r => setTimeout(r, ms))
  
  // Phase 1: thinking text
  for (const char of '我来查询相关文档...\n') {
    addToken(char)
    await delay(30)
  }
  
  // Phase 2: tool call
  await delay(200)
  addTool('mcp__docs__search')
  await delay(1000)
  finishTool('mcp__docs__search')
  
  // Phase 3: more thinking
  await delay(200)
  for (const char of '继续查找更多资料...\n') {
    addToken(char)
    await delay(30)
  }
  
  // Phase 4: another tool
  await delay(200)
  addTool('mcp__reference__get_symbol')
  await delay(800)
  finishTool('mcp__reference__get_symbol')
  
  // Phase 5: final answer
  await delay(200)
  for (const char of '## 最终答案\n\n这是一个总结性回答。') {
    addToken(char)
    await delay(20)
  }
  
  msg.value.isStreaming = false
  msg.value.usage!.totalDuration = 5000
}
</script>

`````

--- **end of file: frontend/src/views/TestSegments.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/chat/ChatBubble.vue** (project: lc_agent) --- 

`````vue
<!-- @deprecated Use EPX BubbleList in ChatView instead. Kept for TestSegments.vue. -->
<template>
  <div class="chat-bubble" :class="[message.role, { streaming: message.isStreaming }]">
    <div class="bubble-avatar" :class="message.role">
      <span v-if="message.role === 'user'" class="avatar-icon">👨‍💻</span>
      <span v-else class="avatar-icon">🤖</span>
    </div>
    <div class="bubble-body">
      <div class="bubble-label">
        <span v-if="message.role === 'user'" class="role-name user-name">You</span>
        <span v-else class="role-name ai-name">{{ modelLabel }}</span>
        <button
          v-if="showEdit"
          class="edit-btn"
          title="编辑并重发"
          @click="$emit('edit')"
        >✏️</button>
      </div>
      <div class="bubble-content">
        <template v-if="message.role === 'assistant'">
          <template v-for="(seg, idx) in renderedSegments" :key="idx">
            <ToolCallCard v-if="seg.type === 'tool' && seg.toolCall" :tool-call="seg.toolCall" :collapsed="true" />
            <div v-else-if="seg.type === 'text' && seg.html" :class="seg.cls">
              <div v-if="seg.cls === 'thinking-block'" class="thinking-header">
                <span class="thinking-icon">💭</span>
                <span class="thinking-label">思考中</span>
              </div>
              <div v-html="seg.html" class="markdown-body" />
            </div>
          </template>
        </template>
        <div v-else-if="message.role === 'user'" class="plain-text">{{ message.content }}</div>

        <span v-if="message.isStreaming" class="streaming-cursor">▊</span>

        <TokenUsagePanel v-if="message.role === 'assistant' && !message.isStreaming && message.usage" :usage="message.usage" :tool-calls="message.toolCalls" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import { useToolsStore } from '@/stores/tools'
import ToolCallCard from './ToolCallCard.vue'
import TokenUsagePanel from './TokenUsagePanel.vue'
import type { ChatMessage, ToolCall } from '@/stores/chat'

interface RenderedSegment {
  type: 'text' | 'tool'
  html?: string
  cls?: string
  toolCall?: ToolCall
}

const props = defineProps<{
  message: ChatMessage
  showEdit?: boolean
}>()
defineEmits<{ edit: [] }>()
const toolsStore = useToolsStore()

const renderedSegments = computed((): RenderedSegment[] => {
  const content = props.message.content
  if (!content) return []

  const toolCalls = props.message.toolCalls || []
  const markerRe = /<!--(?:TOOL:(\d+)|THINK_START|THINK_END)-->/g
  const parts: RenderedSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let lastToolSegIdx = -1
  let inThinking = false

  while ((match = markerRe.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index).trim()
    const marker = match[0]

    if (marker === '<!--THINK_START-->') {
      if (textBefore) {
        parts.push({ type: 'text', html: renderMarkdown(textBefore), cls: 'content-block' })
      }
      inThinking = true
    } else if (marker === '<!--THINK_END-->') {
      if (textBefore) {
        parts.push({ type: 'text', html: renderMarkdown(textBefore), cls: 'thinking-block' })
      }
      inThinking = false
    } else {
      // TOOL marker
      if (textBefore) {
        parts.push({ type: 'text', html: renderMarkdown(textBefore), cls: inThinking ? 'thinking-block' : 'content-block' })
      }
      const tcIdx = parseInt(match[1], 10)
      if (toolCalls[tcIdx]) {
        lastToolSegIdx = parts.length
        parts.push({ type: 'tool', toolCall: toolCalls[tcIdx] })
      }
    }
    lastIndex = match.index + match[0].length
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) {
    parts.push({ type: 'text', html: renderMarkdown(remaining), cls: inThinking ? 'thinking-block' : 'content-block' })
  }

  // If no explicit THINK markers, fall back to old heuristic: text before last tool = thinking
  const hasThinkMarkers = content.includes('<!--THINK_START-->')
  if (!hasThinkMarkers && lastToolSegIdx >= 0) {
    for (let i = 0; i < parts.length; i++) {
      if (parts[i].type === 'text') {
        parts[i].cls = i < lastToolSegIdx ? 'thinking-block' : 'content-block'
      }
    }
  }

  return parts
})

const modelLabel = computed(() => {
  const model = toolsStore.currentModel
  if (!model) return 'AI'
  const parts = model.split('/')
  return parts[parts.length - 1] || 'AI'
})
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid transparent;
}

.chat-bubble.user {
  background: #0f2b1e;
  border-color: #1b4332;
}

.chat-bubble.assistant {
  background: var(--el-fill-color-light);
  border-color: var(--el-border-color);
}

.bubble-avatar {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bubble-avatar.user {
  background: linear-gradient(135deg, #2ea043, #238636);
  box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
}

.bubble-avatar.assistant {
  background: var(--el-fill-color);
}

.bubble-body {
  flex: 1;
  min-width: 0;
}

.bubble-label {
  margin-bottom: 4px;
}

.role-name {
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  color: #56d364;
}

.ai-name {
  color: var(--el-text-color-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.bubble-content {
  overflow-wrap: break-word;
  line-height: 1.7;
  font-size: 14px;
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: var(--el-color-primary);
  font-size: 16px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.thinking-block {
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.2);
  border-left: 3px solid rgba(234, 179, 8, 0.6);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 8px 0;
  position: relative;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 0 4px;
  user-select: none;
  border-bottom: 1px solid rgba(139, 148, 158, 0.1);
  margin-bottom: 6px;
}

.thinking-icon {
  font-size: 13px;
}

.thinking-label {
  font-size: 11px;
  color: #eab308;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.thinking-toggle {
  font-size: 10px;
  color: #6e7681;
  margin-left: auto;
}

.thinking-block :deep(.markdown-body) {
  font-size: 12.5px !important;
  color: #d4a017 !important;
  font-style: italic;
  line-height: 1.65;
  opacity: 0.9;
}

.thinking-block :deep(.markdown-body p) {
  color: #d4a017;
  margin: 4px 0;
}

.thinking-block :deep(.markdown-body code) {
  background: rgba(234, 179, 8, 0.12);
  color: #eab308;
}

.thinking-block :deep(.markdown-body strong) {
  color: #facc15;
  font-style: normal;
}

.content-block {
  margin: 4px 0;
}

.tool-calls {
  margin-bottom: 8px;
}

.edit-btn {
  margin-left: 8px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.chat-bubble.user:hover .edit-btn {
  opacity: 0.7;
}

.edit-btn:hover {
  opacity: 1 !important;
  background: rgba(255, 255, 255, 0.1);
}
</style>

`````

--- **end of file: frontend/src/components/chat/ChatBubble.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/chat/ChatInput.vue** (project: lc_agent) --- 

`````vue
<template>
  <div class="chat-input-wrapper">
    <XSender
      ref="senderRef"
      :loading="isStreaming"
      :disabled="!isConnected"
      placeholder="Send a message..."
      submit-type="enter"
      clearable
      auto-focus
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { XSender } from 'vue-element-plus-x'
import { useChatStore } from '@/stores/chat'

defineProps<{
  isStreaming?: boolean
  editContent?: string
}>()

const emit = defineEmits<{
  send: [content: string]
  stop: []
  cancelEdit: []
}>()

const chatStore = useChatStore()
const { isStreaming, isConnected } = storeToRefs(chatStore)
const senderRef = ref<InstanceType<typeof XSender>>()

function handleSubmit() {
  const model = senderRef.value?.getModelValue()
  const text = model?.text ?? ''
  if (!text.trim()) return
  emit('send', text.trim())
  senderRef.value?.clear()
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: 10px 20px 14px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
}

.chat-input-wrapper :deep(.elx-x-sender) {
  background: var(--el-bg-color-overlay) !important;
  border-color: var(--el-border-color) !important;
  border-radius: 8px;
}

.chat-input-wrapper :deep(.chat-rich-text) {
  background: transparent !important;
}

.chat-input-wrapper :deep([contenteditable="true"]) {
  color: var(--el-text-color-primary) !important;
}

.chat-input-wrapper :deep([contenteditable="true"] p),
.chat-input-wrapper :deep([contenteditable="true"] span) {
  color: inherit !important;
}

.chat-input-wrapper :deep(.elx-x-sender__chat) {
  background: transparent !important;
}

.chat-input-wrapper :deep(.chat-grid-wrap) {
  color: var(--el-text-color-primary) !important;
}
</style>

`````

--- **end of file: frontend/src/components/chat/ChatInput.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/chat/InterruptDialog.vue** (project: lc_agent) --- 

`````vue
<template>
  <el-dialog
    v-model="visible"
    title="⚠️ 工具需要审批"
    width="500px"
    :close-on-click-modal="false"
  >
    <div v-for="(action, idx) in interrupt?.actionRequests ?? []" :key="idx" class="action-item">
      <p><strong>工具:</strong> {{ action.name }}</p>
      <pre class="action-args">{{ JSON.stringify(action.arguments, null, 2) }}</pre>
    </div>

    <template #footer>
      <el-button @click="reject">拒绝</el-button>
      <el-button type="primary" @click="approve">批准执行</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InterruptInfo } from '@/stores/chat'

const props = defineProps<{ interrupt: InterruptInfo | null }>()
const emit = defineEmits<{ decide: [decision: { type: string; message?: string }] }>()

const visible = computed({
  get: () => props.interrupt !== null,
  set: () => {},
})

function approve() {
  emit('decide', { type: 'approve' })
}

function reject() {
  emit('decide', { type: 'reject', message: '用户拒绝了此操作' })
}
</script>

<style scoped>
.action-item {
  margin-bottom: 14px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.action-args {
  background: var(--el-fill-color);
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  margin-top: 8px;
  border: 1px solid var(--el-border-color);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
</style>

`````

--- **end of file: frontend/src/components/chat/InterruptDialog.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/chat/TokenUsagePanel.vue** (project: lc_agent) --- 

`````vue
<template>
  <div v-if="usage && (usage.rounds.length > 0 || usage.toolCallCount > 0 || usage.totalDuration)" class="token-usage-panel">
    <div class="usage-header" @click.stop="expanded = !expanded">
      <span class="usage-title">Token 用量</span>
      <div class="usage-badges">
        <span class="badge badge-rounds">🔄 {{ usage.rounds.length }} Rounds</span>
        <span v-if="usage.toolCallCount" class="badge badge-tools" @click.stop="toolsExpanded = !toolsExpanded">🔧 {{ usage.toolCallCount }} 工具</span>
        <span v-if="usage.totalDuration" class="badge badge-time">⏱ {{ formatDuration(usage.totalDuration) }}</span>
      </div>
    </div>

    <div v-if="usage.rounds.length > 0" class="usage-summary">
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalInput) }}</div>
        <div class="summary-label">输入</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalOutput) }}</div>
        <div class="summary-label">输出</div>
        <div v-if="totalReasoning > 0" class="summary-sub reasoning">Reasoning: {{ formatTokens(totalReasoning) }}</div>
      </div>
      <div class="summary-card card-cached">
        <div class="summary-value">{{ formatTokens(totalCached) }}</div>
        <div class="summary-label">缓存</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ formatTokens(totalAll) }}</div>
        <div class="summary-label">Total</div>
        <div v-if="usage.totalDuration" class="summary-sub time">{{ formatDuration(usage.totalDuration) }}</div>
      </div>
    </div>
    <div v-else-if="usage.totalDuration" class="usage-summary-minimal">
      <span class="minimal-info">总耗时 {{ formatDuration(usage.totalDuration) }}</span>
      <span v-if="usage.toolCallCount" class="minimal-info">· {{ usage.toolCallCount }} 次工具调用</span>
    </div>

    <div v-if="expanded && usage.rounds.length > 1" class="usage-details">
      <div class="details-header">
        <span class="detail-toggle" @click="expanded = !expanded">▾ Per-round Details</span>
        <span class="rounds-badge">{{ usage.rounds.length }} Rounds</span>
      </div>
      <table class="details-table">
        <thead>
          <tr>
            <th>#</th>
            <th>输入</th>
            <th>输出</th>
            <th>Total</th>
            <th>Cached</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(round, i) in usage.rounds" :key="i">
            <td class="col-num">{{ i + 1 }}</td>
            <td>{{ formatTokens(round.inputTokens) }}</td>
            <td>{{ formatTokens(round.outputTokens) }}</td>
            <td>{{ formatTokens(round.totalTokens) }}</td>
            <td>{{ formatTokens(round.cacheReadTokens) }}</td>
            <td class="col-duration">{{ round.duration ? formatDuration(round.duration) : '-' }}</td>
          </tr>
          <tr class="row-sum">
            <td class="col-num">Sum</td>
            <td>{{ formatTokens(totalInput) }}</td>
            <td>{{ formatTokens(totalOutput) }}</td>
            <td>{{ formatTokens(totalAll) }}</td>
            <td>{{ formatTokens(totalCached) }}</td>
            <td class="col-duration">{{ usage.totalDuration ? formatDuration(usage.totalDuration) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="toolsExpanded && toolCalls && toolCalls.length > 0" class="tools-details">
      <div class="details-header">
        <span class="detail-toggle" @click="toolsExpanded = false">▾ Tool Calls</span>
        <span class="tools-badge">{{ toolCalls.length }} 工具</span>
      </div>
      <table class="details-table">
        <thead>
          <tr>
            <th>#</th>
            <th class="th-name">名称</th>
            <th>状态</th>
            <th>耗时</th>
            <th>返回长度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(tc, i) in toolCalls" :key="i">
            <td class="col-num">{{ i + 1 }}</td>
            <td class="col-tool-name">{{ tc.name }}</td>
            <td><span class="status-dot" :class="tc.status" />{{ statusLabel(tc.status) }}</td>
            <td class="col-duration">{{ tc.duration ? formatDuration(tc.duration) : '-' }}</td>
            <td>{{ tc.resultLength ? formatSize(tc.resultLength) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MessageUsage, ToolCall } from '@/stores/chat'

const props = defineProps<{
  usage: MessageUsage | undefined
  toolCalls?: ToolCall[]
}>()
const expanded = ref(false)
const toolsExpanded = ref(false)

const totalInput = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.inputTokens, 0) || 0
)
const totalOutput = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.outputTokens, 0) || 0
)
const totalAll = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.totalTokens, 0) || 0
)
const totalCached = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + r.cacheReadTokens, 0) || 0
)
const totalReasoning = computed(() =>
  props.usage?.rounds.reduce((s, r) => s + (r.reasoningTokens || 0), 0) || 0
)

function formatTokens(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function formatDuration(ms: number): string {
  if (ms < 1000) return ms + 'ms'
  return (ms / 1000).toFixed(1) + 's'
}

function formatSize(len: number): string {
  if (len < 1024) return `${len} chars`
  return `${(len / 1024).toFixed(1)}K`
}

function statusLabel(status: string): string {
  switch (status) {
    case 'done': return '完成'
    case 'running': return '执行中'
    case 'error': return '错误'
    default: return '等待'
  }
}
</script>

<style scoped>
.token-usage-panel {
  margin-top: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
}

.usage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  margin-bottom: 10px;
}

.usage-title {
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.usage-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.badge-rounds {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.badge-tools {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
  border: 1px solid var(--el-border-color);
}

.badge-time {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  border: 1px solid var(--el-color-success-light-5);
}

.usage-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
}

.summary-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-family: 'JetBrains Mono', monospace;
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-primary);
  margin-top: 4px;
  font-weight: 600;
}

.summary-sub {
  font-size: 10px;
  margin-top: 2px;
}

.card-cached .summary-value {
  color: var(--el-color-success);
}

.summary-sub.cached {
  color: var(--el-color-success);
}

.summary-sub.reasoning {
  color: var(--el-text-color-regular);
}

.summary-sub.time {
  color: var(--el-text-color-secondary);
}

.usage-details {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color);
  padding-top: 10px;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-toggle {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  cursor: pointer;
}

.rounds-badge {
  font-size: 10px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 1px 6px;
  border-radius: 8px;
}

.details-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.details-table th {
  color: var(--el-text-color-secondary);
  font-weight: 500;
  text-align: right;
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color);
}

.details-table th:first-child {
  text-align: left;
}

.details-table td {
  color: var(--el-text-color-regular);
  text-align: right;
  padding: 4px 8px;
}

.col-num {
  text-align: left !important;
  color: var(--el-text-color-secondary) !important;
  font-weight: 600;
}

.col-duration {
  color: var(--el-color-warning) !important;
}

.row-sum {
  border-top: 1px solid var(--el-border-color);
}

.row-sum td {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.usage-summary-minimal {
  display: flex;
  gap: 6px;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.minimal-info {
  font-family: 'JetBrains Mono', monospace;
}

.badge-tools {
  cursor: pointer;
  transition: all 0.15s ease;
}

.badge-tools:hover {
  background: var(--el-fill-color-light);
  transform: scale(1.05);
}

.tools-details {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color);
  padding-top: 10px;
}

.tools-badge {
  font-size: 10px;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color);
  padding: 1px 6px;
  border-radius: 8px;
}

.col-tool-name {
  text-align: left !important;
  color: var(--el-color-primary) !important;
  font-weight: 500;
}

.th-name {
  text-align: left !important;
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.status-dot.done {
  background: var(--el-color-success);
}

.status-dot.running {
  background: var(--el-color-warning);
}

.status-dot.error {
  background: var(--el-color-danger);
}
</style>

`````

--- **end of file: frontend/src/components/chat/TokenUsagePanel.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/chat/ToolCallCard.vue** (project: lc_agent) --- 

`````vue
<template>
  <div class="tool-call-card" :class="[toolCall.status, { 'is-collapsed': isCollapsed }]">
    <div class="tool-header" @click.stop="toggleCollapse">
      <span class="collapse-icon">{{ isCollapsed ? '▸' : '▾' }}</span>
      <el-icon v-if="toolCall.status === 'running'" class="spinning">
        <Loading />
      </el-icon>
      <el-icon v-else-if="toolCall.status === 'done'" style="color: var(--el-color-success)">
        <Check />
      </el-icon>
      <span class="tool-name">{{ toolCall.name }}</span>
      <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
      <span class="tool-meta" v-if="toolCall.status === 'done'">
        <span v-if="toolCall.duration" class="meta-item">⏱ {{ formatDuration(toolCall.duration) }}</span>
        <span v-if="toolCall.resultLength" class="meta-item">📦 {{ formatSize(toolCall.resultLength) }}</span>
      </span>
    </div>
    <template v-if="!isCollapsed">
    <div v-if="toolCall.args && Object.keys(toolCall.args).length > 0" class="tool-args">
      <div v-for="arg in formatArgs(toolCall.args)" :key="arg.key" class="arg-row">
        <span class="arg-key">{{ arg.key }}:</span>
        <span class="arg-value">{{ arg.value }}</span>
      </div>
    </div>
    <div v-if="toolCall.result" class="tool-result">
      <pre>{{ toolCall.result }}</pre>
      <button v-if="isLong" class="fullscreen-btn" @click.stop="showModal = true" title="查看完整内容">⛶</button>
    </div>
    </template>

    <teleport to="body">
      <div v-if="showModal" class="tool-modal-backdrop" @click="showModal = false">
        <div class="tool-modal" @click.stop>
          <div class="tool-modal-header">
            <span class="tool-modal-title">{{ toolCall.name }}</span>
            <div class="modal-actions">
              <button class="modal-toggle-btn" :class="{ active: renderMode }" @click="renderMode = !renderMode">
                {{ renderMode ? '📄 原文' : '✨ 渲染' }}
              </button>
              <button class="tool-modal-close" @click="showModal = false">✕</button>
            </div>
          </div>
          <pre v-if="!renderMode" class="tool-modal-body">{{ toolCall.result }}</pre>
          <div v-else class="tool-modal-body rendered" v-html="renderedResult" />
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Loading, Check } from '@element-plus/icons-vue'
import type { ToolCall } from '@/stores/chat'

const props = defineProps<{ toolCall: ToolCall; collapsed?: boolean }>()
const showModal = ref(false)
const renderMode = ref(false)
const isCollapsed = ref(props.collapsed ?? false)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

const isLong = computed(() => (props.toolCall.result?.length || 0) > 300)

const renderedResult = computed(() => {
  if (!props.toolCall.result) return ''
  return props.toolCall.result
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\\n/g, '\n')
    .replace(/\n/g, '<br>')
    .replace(/  /g, '&nbsp;&nbsp;')
})

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatSize(len: number): string {
  if (len < 1024) return `${len} chars`
  return `${(len / 1024).toFixed(1)}K chars`
}

function formatArgs(args: Record<string, any>): { key: string; value: string }[] {
  return Object.entries(args).map(([k, v]) => {
    let val = typeof v === 'string' ? v : JSON.stringify(v)
    if (val.length > 100) val = val.slice(0, 100) + '...'
    return { key: k, value: val }
  })
}

const statusType = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return 'warning'
    case 'done': return 'success'
    case 'error': return 'danger'
    default: return 'info'
  }
})

const statusLabel = computed(() => {
  switch (props.toolCall.status) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '错误'
    default: return '等待'
  }
})
</script>

<style scoped>
.tool-call-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  background: var(--el-fill-color-light);
  border-left: 3px solid var(--el-text-color-secondary);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.tool-call-card.running {
  border-left-color: var(--el-color-primary);
  box-shadow: 0 0 12px color-mix(in srgb, var(--el-color-primary) 8%, transparent);
}

.tool-call-card.done {
  border-left-color: var(--el-color-success);
}

.tool-call-card.error {
  border-left-color: var(--el-color-danger);
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.tool-header:hover {
  opacity: 0.85;
}

.collapse-icon {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  width: 12px;
  flex-shrink: 0;
}

.is-collapsed {
  padding: 6px 14px;
}

.tool-name {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--el-color-primary);
  font-weight: 500;
}

.tool-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.meta-item {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.tool-args {
  margin-top: 6px;
  padding: 5px 8px;
  background: var(--el-fill-color);
  border-radius: 4px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
}

.arg-row {
  display: flex;
  gap: 6px;
  padding: 1px 0;
  line-height: 1.5;
}

.arg-key {
  color: var(--el-color-primary);
  flex-shrink: 0;
  font-weight: 500;
}

.arg-value {
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.tool-result {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--el-fill-color);
  border-radius: 6px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  position: relative;
}

.tool-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-secondary);
}

.fullscreen-btn {
  position: sticky;
  bottom: 0;
  float: right;
  padding: 2px 8px;
  font-size: 14px;
  color: var(--el-color-primary);
  background: var(--el-bg-color);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.fullscreen-btn:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.tool-modal-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--el-bg-color-page) 70%, transparent);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.tool-modal {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 16px 48px color-mix(in srgb, var(--el-bg-color-page) 50%, transparent);
  min-width: 500px;
}

.tool-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
  gap: 12px;
}

.modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-toggle-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-toggle-btn:hover {
  background: var(--el-fill-color-light);
}

.modal-toggle-btn.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.tool-modal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.tool-modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  font-size: 16px;
  cursor: pointer;
}

.tool-modal-close:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.tool-modal-body {
  flex: 1;
  padding: 16px;
  margin: 0;
  overflow: auto;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-regular);
}

.tool-modal-body.rendered {
  white-space: normal;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.spinning {
  animation: spin 1s linear infinite;
  color: var(--el-color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

`````

--- **end of file: frontend/src/components/chat/ToolCallCard.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/dialogs/AgentEditorDialog.vue** (project: lc_agent) --- 

`````vue
<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 Agent' : '新建 Agent'"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-alert v-if="isCodeAgent" type="warning" :closable="false" style="margin-bottom: 12px">
      此智能体由代码注册（CompiledGraph），仅可修改运行时配置（工具/MCP/Skills）。
    </el-alert>

    <el-form :model="form" label-width="100px" label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" :disabled="isCodeAgent" placeholder="例如：Code Assistant" />
      </el-form-item>

      <el-form-item label="模型">
        <el-select v-model="form.default_model" :disabled="isCodeAgent" style="width:100%" placeholder="选择默认模型">
          <el-option
            v-for="model in toolsStore.models"
            :key="model.id"
            :label="`${model.id} (${model.provider})`"
            :value="model.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="系统提示词">
        <el-input
          v-model="form.system_prompt"
          :disabled="isCodeAgent"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 12 }"
          placeholder="定义 Agent 的行为和角色..."
        />
      </el-form-item>

      <el-form-item label="允许的工具组">
        <div class="tool-group-select">
          <el-radio-group v-model="toolGroupMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="toolGroupMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedGroups">
              <el-checkbox
                v-for="group in toolsStore.groups"
                :key="group.id"
                :value="group.id"
              >
                {{ group.description || group.id }} ({{ group.tools.length }} tools)
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="允许的 MCP 服务器">
        <div class="tool-group-select">
          <el-radio-group v-model="mcpMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="mcpMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedMcpServers">
              <el-checkbox
                v-for="server in toolsStore.mcpServers"
                :key="server.name"
                :value="server.name"
              >
                {{ server.name }}
                <el-tag size="small" :type="server.status === 'connected' ? 'success' : 'info'" style="margin-left:4px">
                  {{ server.tools?.length || 0 }} tools
                </el-tag>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="允许的 Skills">
        <div class="tool-group-select">
          <el-radio-group v-model="skillsMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="skillsMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedSkills">
              <el-checkbox
                v-for="skill in toolsStore.skills"
                :key="skill.name"
                :value="skill.name"
              >
                {{ skill.name }}
                <span class="skill-hint">{{ skill.description }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="危险工具（需要审批）">
        <el-input
          v-model="dangerousToolsStr"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="每行一个工具名, 例如: filesystem__delete_file"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="danger" v-if="isEdit && !agentsStore.isAgentBuiltin(editingId!) && !isCodeAgent" @click="handleDelete">
        删除
      </el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore, type AgentPreset } from '@/stores/agents'

const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()

const visible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const editingSource = ref<'builtin' | 'code' | 'user'>('user')
const toolGroupMode = ref<'all' | 'none' | 'custom'>('all')
const selectedGroups = ref<string[]>([])
const mcpMode = ref<'all' | 'none' | 'custom'>('all')
const selectedMcpServers = ref<string[]>([])
const skillsMode = ref<'all' | 'none' | 'custom'>('all')
const selectedSkills = ref<string[]>([])

const isCodeAgent = ref(false)

const form = ref({
  name: '',
  system_prompt: '',
  default_model: '',
})

const dangerousToolsStr = ref('')

function open(agent?: AgentPreset) {
  if (agent) {
    isEdit.value = true
    editingId.value = agent.id
    editingSource.value = agent.source || 'user'
    isCodeAgent.value = agent.source === 'code'
    form.value.name = agent.name
    form.value.system_prompt = agent.system_prompt
    form.value.default_model = agent.default_model
    dangerousToolsStr.value = (agent.dangerous_tools || []).join('\n')

    if (agent.allowed_tool_groups === null) {
      toolGroupMode.value = 'all'
      selectedGroups.value = []
    } else if (agent.allowed_tool_groups.length === 0) {
      toolGroupMode.value = 'none'
      selectedGroups.value = []
    } else {
      toolGroupMode.value = 'custom'
      selectedGroups.value = [...agent.allowed_tool_groups]
    }

    if (agent.allowed_mcp_servers === null) {
      mcpMode.value = 'all'
      selectedMcpServers.value = []
    } else if (agent.allowed_mcp_servers.length === 0) {
      mcpMode.value = 'none'
      selectedMcpServers.value = []
    } else {
      mcpMode.value = 'custom'
      selectedMcpServers.value = [...agent.allowed_mcp_servers]
    }

    if (agent.allowed_skills === null) {
      skillsMode.value = 'all'
      selectedSkills.value = []
    } else if (agent.allowed_skills.length === 0) {
      skillsMode.value = 'none'
      selectedSkills.value = []
    } else {
      skillsMode.value = 'custom'
      selectedSkills.value = [...agent.allowed_skills]
    }
  } else {
    isEdit.value = false
    editingId.value = ''
    editingSource.value = 'user'
    isCodeAgent.value = false
    form.value = { name: '', system_prompt: '', default_model: toolsStore.currentModel }
    dangerousToolsStr.value = ''
    toolGroupMode.value = 'all'
    selectedGroups.value = []
    mcpMode.value = 'all'
    selectedMcpServers.value = []
    skillsMode.value = 'all'
    selectedSkills.value = []
  }
  visible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const allowed_tool_groups =
      toolGroupMode.value === 'all' ? null :
      toolGroupMode.value === 'none' ? [] :
      selectedGroups.value

    const allowed_mcp_servers =
      mcpMode.value === 'all' ? null :
      mcpMode.value === 'none' ? [] :
      selectedMcpServers.value

    const allowed_skills =
      skillsMode.value === 'all' ? null :
      skillsMode.value === 'none' ? [] :
      selectedSkills.value

    const data = {
      name: form.value.name,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      allowed_tool_groups,
      allowed_mcp_servers,
      allowed_skills,
      dangerous_tools: dangerousToolsStr.value.split('\n').map(s => s.trim()).filter(Boolean),
    }

    if (isEdit.value) {
      await agentsStore.updateAgent(editingId.value, data)
    } else {
      await agentsStore.createAgent(data as any)
    }
    visible.value = false
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  await agentsStore.deleteAgent(editingId.value)
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.tool-group-select {
  width: 100%;
}

.custom-groups {
  margin-top: 8px;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.custom-groups .el-checkbox {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.skill-hint {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-left: 4px;
  opacity: 0.7;
}
</style>

`````

--- **end of file: frontend/src/components/dialogs/AgentEditorDialog.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/layout/AppHeader.vue** (project: lc_agent) --- 

`````vue
<template>
  <header class="app-header">
    <div class="header-left">
      <span class="logo">⚡ lc_agent</span>
    </div>
    <div class="header-center">
      <el-select
        :model-value="agentsStore.currentAgentId"
        size="small"
        style="width: 240px"
        @change="agentsStore.selectAgent"
      >
        <el-option
          v-for="agent in agentsStore.agents"
          :key="agent.id"
          :label="agent.name"
          :value="agent.id"
        >
          <div class="agent-option">
            <span>{{ agent.name }}</span>
            <span v-if="agent.source === 'builtin'" class="source-badge badge-builtin">内置</span>
            <span v-else-if="agent.source === 'code'" class="source-badge badge-code">代码</span>
            <span v-else class="source-badge badge-user">自建</span>
          </div>
        </el-option>
      </el-select>
      <button class="header-btn btn-edit" @click="$emit('editAgent')" :disabled="agentsStore.isBuiltin">编辑</button>
      <button class="header-btn btn-new-agent" @click="$emit('newAgent')">+ 新Agent</button>
      <button class="header-btn btn-new-chat" @click="$emit('newChat')">+ 新对话</button>
    </div>
    <div class="header-right">
      <span class="model-badge">{{ modelName }}</span>
      <span class="status-dot" :class="connected ? 'connected' : 'disconnected'" />
      <span class="status-text">{{ connected ? '已连接' : '未连接' }}</span>
      <el-button :icon="isDark ? Sunny : Moon" circle size="small" @click="toggleDark()" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAgentsStore } from '@/stores/agents'
import { useTheme } from '@/composables/useTheme'
import { Sunny, Moon } from '@element-plus/icons-vue'

const agentsStore = useAgentsStore()
const { isDark, toggleDark } = useTheme()

defineProps<{
  modelName: string
  connected: boolean
}>()

defineEmits<{
  editAgent: []
  newAgent: []
  newChat: []
}>()
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  height: 52px;
  z-index: 100;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-badge {
  font-size: 12px;
  padding: 3px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  color: var(--el-text-color-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--el-color-success);
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: var(--el-color-danger);
}

.status-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.agent-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.source-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.badge-builtin {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.badge-code {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
  border: 1px solid var(--el-color-warning-light-5);
}

.badge-user {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  border: 1px solid var(--el-color-success-light-5);
}

.header-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.header-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-edit {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  border: 1px solid var(--el-border-color);
}

.btn-edit:hover:not(:disabled) {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.btn-new-agent {
  background: var(--el-color-success);
  color: var(--el-color-white);
}

.btn-new-agent:hover {
  background: var(--el-color-success-light-3);
}

.btn-new-chat {
  background: var(--el-color-primary);
  color: var(--el-color-white);
}

.btn-new-chat:hover {
  background: var(--el-color-primary-light-3);
}
</style>

`````

--- **end of file: frontend/src/components/layout/AppHeader.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/layout/LeftSidebar.vue** (project: lc_agent) --- 

`````vue
<template>
  <aside class="left-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <transition name="fade">
        <span v-if="!collapsed" class="sidebar-brand">Chats</span>
      </transition>
      <div v-if="!collapsed" class="header-actions">
        <button class="action-btn" @click="toggleAllGroups" :title="allCollapsed ? '全部展开' : '全部折叠'">
          <span v-if="allCollapsed">⊞</span>
          <span v-else>⊟</span>
        </button>
        <button class="toggle-btn" @click="emit('toggleCollapse')" :title="collapsed ? '展开侧边栏' : '收起侧边栏'">
          <span class="toggle-icon" :class="{ flipped: collapsed }">«</span>
        </button>
      </div>
      <button v-else class="toggle-btn" @click="emit('toggleCollapse')" title="展开侧边栏">
        <span class="toggle-icon flipped">«</span>
      </button>
    </div>

    <div v-if="!collapsed" class="session-list">
      <Conversations
        v-model:active="currentSessionId"
        :items="conversationItems"
        :show-tooltip="true"
        :show-built-in-menu="true"
        :groupable="true"
        ungrouped-title="未分组"
        row-key="id"
        @change="handleSessionChange"
        @menu-command="handleMenuCommand"
      >
        <template #groupTitle="{ group }">
          <div
            class="group-header"
            :data-group="group.title"
            :class="{ 'is-collapsed': collapsedGroups.has(group.title) }"
            @click.stop="toggleGroup(group.title)"
          >
            <span class="group-arrow" :class="{ collapsed: collapsedGroups.has(group.title) }">▶</span>
            <span class="group-name">{{ group.title }}</span>
            <span class="group-count">{{ group.children?.length || 0 }}</span>
          </div>
        </template>
      </Conversations>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect, nextTick, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Conversations } from 'vue-element-plus-x'
import type { ConversationItem, ConversationMenuCommand } from 'vue-element-plus-x/types/Conversations'
import { useSessionsStore } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'

defineProps<{ collapsed: boolean }>()

const sessionsStore = useSessionsStore()
const agentsStore = useAgentsStore()
const emit = defineEmits<{ newChat: []; switchSession: [id: string]; toggleCollapse: [] }>()

const collapsedGroups = ref<Set<string>>(new Set())

const allCollapsed = computed(() => {
  const groupNames = new Set(conversationItems.value.map(i => i.group).filter(Boolean))
  return groupNames.size > 0 && groupNames.size === collapsedGroups.value.size
})

function toggleGroup(title: string) {
  if (collapsedGroups.value.has(title)) {
    collapsedGroups.value.delete(title)
  } else {
    collapsedGroups.value.add(title)
  }
  nextTick(syncCollapsedDOM)
}

function syncCollapsedDOM() {
  const headers = document.querySelectorAll('.group-header[data-group]')
  headers.forEach(header => {
    const groupName = header.getAttribute('data-group') || ''
    const groupItems = header.closest('.elx-conversations__group')?.querySelector('.elx-conversations__group-items') as HTMLElement | null
    if (groupItems) {
      if (collapsedGroups.value.has(groupName)) {
        groupItems.style.display = 'none'
      } else {
        groupItems.style.display = ''
      }
    }
  })
}

function toggleAllGroups() {
  if (allCollapsed.value) {
    collapsedGroups.value.clear()
  } else {
    const groupNames = new Set(conversationItems.value.map(i => i.group).filter(Boolean))
    collapsedGroups.value = groupNames as Set<string>
  }
  nextTick(syncCollapsedDOM)
}

const conversationItems = computed<ConversationItem[]>(() =>
  sessionsStore.sessions.map(s => ({
    id: s.id,
    label: s.title || 'New Chat',
    group: agentsStore.getAgentName(s.agent_id || '__chat__'),
  }))
)

const currentSessionId = computed({
  get: () => sessionsStore.currentSessionId ?? undefined,
  set: (_val: string | number | undefined) => { /* handled by @change */ },
})

function handleSessionChange(item: ConversationItem) {
  emit('switchSession', String(item.id))
}

async function handleMenuCommand(command: ConversationMenuCommand, item: ConversationItem) {
  const id = String(item.id)
  const cmd = typeof command === 'string' ? command : String(command)

  if (cmd === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('输入新标题', '重命名', {
        inputValue: item.label || '',
        inputValidator: (v) => !!v?.trim() || '标题不能为空',
      })
      if (value?.trim()) {
        await sessionsStore.updateTitle(id, value.trim())
      }
    } catch {
      // cancelled
    }
    return
  }

  if (cmd === 'delete') {
    const wasCurrent = id === sessionsStore.currentSessionId
    await sessionsStore.deleteSession(id)
    if (wasCurrent) {
      if (sessionsStore.sessions.length > 0) {
        emit('switchSession', sessionsStore.sessions[0].id)
      } else {
        emit('newChat')
      }
    }
  }
}
</script>

<style scoped>
.left-sidebar {
  width: 260px;
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.left-sidebar.collapsed {
  width: 56px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--el-border-color);
}

.sidebar-brand {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.3px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.toggle-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.toggle-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-icon.flipped {
  transform: rotate(180deg);
}

.session-list {
  flex: 1;
  overflow: hidden;
}

.session-list :deep(.elx-conversations) {
  height: 100%;
  width: 100%;
  --elx-conversations-list-auto-bg-color: transparent !important;
}

.session-list :deep(.elx-conversations__list) {
  width: 100% !important;
  height: 100% !important;
  padding: 4px 4px !important;
  background: transparent !important;
  background-color: transparent !important;
  border-radius: 0 !important;
}

.session-list :deep(.elx-conversations-item) {
  margin: 0;
  padding: 8px 8px;
  border-radius: 6px;
  color: var(--el-text-color-regular);
}

.session-list :deep(.elx-conversations-item__label) {
  max-width: none !important;
  color: var(--el-text-color-regular) !important;
}

.session-list :deep(.elx-conversations-item--active) {
  background: var(--el-color-primary-light-9) !important;
}

.session-list :deep(.elx-conversations-item--active .elx-conversations-item__label) {
  color: var(--el-color-primary) !important;
  font-weight: 600;
}

/* Group header custom styling */
.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 8px 4px 8px;
  margin-top: 4px;
  cursor: pointer;
  border-top: 1px solid var(--el-border-color-lighter);
  user-select: none;
  transition: background 0.15s;
  border-radius: 4px;
}

.group-header:hover {
  background: var(--el-fill-color-lighter);
}

.session-list :deep(.elx-conversations__group:first-child .group-header) {
  border-top: none;
  margin-top: 0;
}

.group-arrow {
  font-size: 9px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s ease;
  transform: rotate(90deg);
  flex-shrink: 0;
}

.group-arrow.collapsed {
  transform: rotate(0deg);
}

.group-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.3px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-count {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color);
  padding: 1px 5px;
  border-radius: 8px;
  flex-shrink: 0;
}

/* Hide group items when collapsed */
.session-list :deep(.elx-conversations__group-items) {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}

/* Reset EPX default group title styling (we use custom slot content) */
.session-list :deep(.elx-conversations__group-title) {
  all: unset !important;
  display: block !important;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

`````

--- **end of file: frontend/src/components/layout/LeftSidebar.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/layout/RightPanel.vue** (project: lc_agent) --- 

`````vue
<template>
  <aside class="right-panel">
    <div class="panel-section">
      <h4>模型</h4>
      <ModelSelector
        :models="toolsStore.models"
        :current-model="toolsStore.currentModel"
        @change="toolsStore.setModel"
      />
    </div>

    <template v-if="!agentsStore.isChatAgent">
      <div class="panel-section">
        <h4>工具</h4>
        <ToolGroupPanel
          :groups="toolsStore.filteredGroups"
          @toggle="toolsStore.toggleGroup"
        />
      </div>

      <div class="panel-section">
        <h4>MCP 服务器</h4>
        <div v-for="server in toolsStore.filteredMcp" :key="server.name" class="mcp-item" :class="{ 'not-allowed': !server.allowed }">
          <div class="mcp-header">
            <div class="mcp-left">
              <el-switch
                :model-value="server.enabled"
                :disabled="!server.allowed"
                size="small"
                @change="toolsStore.toggleMcp(server.name)"
              />
              <span class="mcp-name">{{ server.name }}</span>
            </div>
            <el-tag size="small" :type="!server.allowed ? 'warning' : server.status === 'connected' ? 'success' : server.status === 'error' ? 'danger' : server.status === 'disabled' ? 'warning' : 'info'">
              {{ !server.allowed ? '未授权' : server.status === 'connected' ? '已连接' : server.status === 'error' ? '错误' : server.status === 'disabled' ? '已禁用' : '未连接' }}
            </el-tag>
          </div>
          <div v-if="server.error && server.allowed" class="mcp-error">{{ server.error }}</div>
          <div v-if="server.tools && server.tools.length && server.allowed" class="mcp-tools">
            <el-tag v-for="tool in server.tools.slice(0, 5)" :key="tool" size="small" :class="server.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'">{{ tool }}</el-tag>
            <el-tag v-if="server.tools.length > 5" size="small" :class="server.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'">+{{ server.tools.length - 5 }}</el-tag>
          </div>
        </div>
        <p v-if="!toolsStore.mcpServers.length" class="empty-hint">暂无 MCP 服务器</p>
      </div>

      <div class="panel-section">
        <h4>Skills</h4>
        <div v-for="skill in toolsStore.filteredSkills" :key="skill.name" class="skill-item" :class="{ 'not-allowed': !skill.allowed, 'skill-disabled': !skill.enabled }">
          <div class="skill-header">
            <el-switch
              :model-value="skill.enabled"
              :disabled="!skill.allowed"
              size="small"
              @change="toolsStore.toggleSkill(skill.name)"
            />
            <span class="skill-name" :class="{ dimmed: !skill.enabled }">{{ skill.name }}</span>
          </div>
          <span class="skill-desc">{{ skill.description }}</span>
        </div>
        <p v-if="!toolsStore.skills.length" class="empty-hint">暂无 Skills</p>
      </div>
    </template>

    <div v-if="agentsStore.isChatAgent" class="panel-section chat-only-hint">
      <div class="hint-box">
        <span class="hint-icon">💬</span>
        <span class="hint-text">Chat 模式：纯对话，无工具</span>
        <span class="hint-sub">切换至 Empty 或 Power 智能体以启用工具</span>
      </div>
    </div>

    <div class="panel-section status-section">
      <h4>状态</h4>
      <div class="status-item">
        <span>连接:</span>
        <el-tag :type="chatStore.isConnected ? 'success' : 'danger'" size="small">
          {{ chatStore.isConnected ? '已连接' : '未连接' }}
        </el-tag>
      </div>
      <div v-if="chatStore.threadId" class="status-item">
        <span>Thread:</span>
        <code>{{ chatStore.threadId.slice(0, 8) }}...</code>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useToolsStore } from '@/stores/tools'
import { useChatStore } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import ModelSelector from '@/components/panels/ModelSelector.vue'
import ToolGroupPanel from '@/components/panels/ToolGroupPanel.vue'

const toolsStore = useToolsStore()
const chatStore = useChatStore()
const agentsStore = useAgentsStore()
</script>

<style scoped>
.right-panel {
  width: 300px;
  background: var(--el-bg-color);
  border-left: 1px solid var(--el-border-color);
  padding: 16px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.panel-section h4 {
  margin: 0 0 10px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.7px;
  font-weight: 600;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color);
}

.empty-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 4px 0;
  opacity: 0.6;
}

.status-section .status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.status-section code {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.mcp-item {
  margin-bottom: 8px;
  padding: 8px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  transition: border-color 0.15s ease;
}

.mcp-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.mcp-item:has(.el-switch:not(.is-checked)) {
  opacity: 0.75;
  border: 1px dashed var(--el-color-warning-light-5) !important;
  background: var(--el-color-warning-light-9) !important;
}

.mcp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mcp-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mcp-error {
  font-size: 11px;
  color: var(--el-color-danger);
  margin-top: 4px;
  word-break: break-all;
  opacity: 0.8;
}

.mcp-name {
  font-size: 13px;
  font-weight: 500;
}

.mcp-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.skill-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  transition: border-color 0.15s ease;
}

.skill-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.skill-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
  transition: color 0.15s ease, opacity 0.15s ease;
}

.skill-name.dimmed {
  color: var(--el-text-color-secondary);
  opacity: 0.6;
}

.skill-disabled {
  opacity: 0.85;
  border: 1px dashed var(--el-border-color) !important;
  background: var(--el-fill-color-lighter) !important;
}

.skill-disabled .skill-name {
  color: var(--el-text-color-secondary) !important;
  text-decoration: line-through;
}

.skill-disabled .skill-desc {
  color: var(--el-text-color-placeholder);
}

.skill-desc {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-top: 3px;
  line-height: 1.5;
}

.not-allowed {
  opacity: 0.6;
}

.not-allowed .skill-name {
  color: var(--el-text-color-secondary) !important;
}

.not-allowed .skill-desc {
  color: var(--el-text-color-secondary);
}

.chat-only-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hint-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
}

.hint-icon {
  font-size: 32px;
}

.hint-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.hint-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  opacity: 0.7;
}
</style>

`````

--- **end of file: frontend/src/components/layout/RightPanel.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/panels/ModelSelector.vue** (project: lc_agent) --- 

`````vue
<template>
  <div class="model-selector">
    <el-select
      :model-value="currentModel"
      placeholder="选择模型"
      size="small"
      style="width: 100%"
      @change="$emit('change', $event)"
    >
      <el-option
        v-for="model in models"
        :key="model.id"
        :label="model.id"
        :value="model.id"
      >
        <span>{{ model.id }}</span>
        <span style="float:right; color:var(--el-text-color-secondary); font-size:11px">
          {{ model.provider }}
        </span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  models: { id: string; provider: string; context_limit: number }[]
  currentModel: string
}>()
defineEmits<{ change: [modelId: string] }>()
</script>

<style scoped>
.model-selector {
  margin-bottom: 8px;
}
</style>

`````

--- **end of file: frontend/src/components/panels/ModelSelector.vue** (project: lc_agent) --- 

---


--- **start of file: frontend/src/components/panels/ToolGroupPanel.vue** (project: lc_agent) --- 

`````vue
<template>
  <div class="tool-group-panel">
    <div v-for="group in groups" :key="group.id" class="group-item" :class="{ 'not-allowed': !(group as any).allowed && (group as any).allowed !== undefined }">
      <div class="group-header">
        <span class="group-name">{{ group.description || group.id }}</span>
        <el-switch
          :model-value="group.enabled"
          :disabled="(group as any).allowed === false"
          size="small"
          @change="$emit('toggle', group.id)"
        />
      </div>
      <div class="group-tools">
        <el-tag
          v-for="tool in group.tools"
          :key="tool.name"
          size="small"
          :class="group.enabled ? 'tool-tag-enabled' : 'tool-tag-disabled'"
        >
          {{ tool.name.split('__').pop() }}
        </el-tag>
      </div>
    </div>
    <p v-if="!groups.length" class="empty">暂无工具</p>
  </div>
</template>

<script setup lang="ts">
import type { ToolGroup } from '@/stores/tools'

defineProps<{ groups: ToolGroup[] }>()
defineEmits<{ toggle: [groupId: string] }>()
</script>

<style scoped>
.group-item {
  margin-bottom: 8px;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.group-item:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-fill-color);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.group-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.group-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  opacity: 0.6;
}

.not-allowed {
  opacity: 0.4;
  border-style: dashed;
  border-color: var(--el-border-color) !important;
}
</style>

`````

--- **end of file: frontend/src/components/panels/ToolGroupPanel.vue** (project: lc_agent) --- 

---

# markdown content namespace: 项目规划文档 


## lc_agent File Tree (relative dir: `docs/my_docs`)


`````

└── docs
    └── my_docs
        └── task.md

`````

---


## lc_agent (relative dir: `docs/my_docs`)  Included Files (total: 1 files)


- `docs/my_docs/task.md`


---


--- **start of file: docs/my_docs/task.md** (project: lc_agent) --- 

`````markdown

# 1. 开发一个 lc_agent 的框架

使用langchain  langgraph deepagents 框架技术开发，


功能要类似nb_agent框架， 但是不使用tui终端，而是使用web界面。web采用vue + element-ui-plus 框架。

lc_agent 定位是一个框架， 然后用户可以导入lc_agent 框架开发，开发自己的具体的agent应用。可以在页面创建智能体。

后端采用fastapi + sqlmodel ，要使用asyncio生态编程

# 2. nb_agent 项目文件夹
ai先必须熟悉nb_agent框架，以及nb_agent_bfzs项目和nb_agent之间的关系。

nb_agent 项目文件夹：
"D:\codes\nb_agent"   

nb_agent_bfzs(基于nb_agent框架开发的自定义项目)项目文件夹:
"D:\codes\nb_agent_bfzs"

我是让你参考nb_agent，内让你照抄， 尽量使用langchain全家桶的2026年最新用法，不用学nb_agent那样都自己实现。

# 3.AI 写langchain 家族框架代码时候的规则

## 3.1 写 langchain / langgraph / deepagents 代码时，禁止使用ai预训练的过时的语法写法。
  要使用最新的框架语法。 写代码时候要用 docs-langchain 和 reference-langchain 这个两个langchain官方文档的mcp工具查询框架最新用法。


## 3.2 如果有必要，要用 nb_rag mcp查询 langchain / langgraph / deepagents  用法
  如果官方的文档，不够用，ai要调用 nbrag mcp的一些列工具来查询用法，要多次多轮深入调用nbrag的一系列工具，不要浅尝辄止，没检索足够足够的资料就开始回答。

  nbrag已向量化langchain相关源码和教程到知识库 `langchain_ai_codes_and_docs`

  langchain_ai_codes_and_docs 知识库包含如下文件件的内容
  ```python
  r'D:\codes\docs\src',
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_anthropic",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_classic",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_community",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_core",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_deepseek",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_google_genai",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_openai",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_protocol",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_text_splitters",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langdetect",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langgraph",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langgraph_sdk",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langsmith",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\deepagents",
  ```

## 3.3 ai可以从 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 目录下深入 langchain 相关的源码，包含函数入参和注释和用法。

ai可以从 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 目录下深入 langchain 相关的源码，包含函数入参和注释和用法。


# 4 web界面

web界面要需要非常炫酷黑暗风， 要使用vue + element-ui-plus 框架。
采用左边菜单栏，中间内容区的方式，右边显示现在nbagent tui那些模型 tools 和 mcp skill，可以热切换屏蔽和激活。

不要照抄 nb_agent tui的布局和相似，因为python开发的tui有固定的局限性，web要按照最佳实践来设计和开发。

# 5 所有 tools 和 mcp 和 skills 都能快速按分组屏蔽
tools 和 mcp 都要能方便按分组激活和屏蔽

例如skill.md 的 希望题头元数据如果加上 ,方便快速激活或者屏蔽一组技能
metadata
    group: "技能组1"$

# 6 关于智能体

智能体就是langchian的 complinedgraph类型， 用户可以在python代码在创建多个agent，页面要能显示这些智能体。

并且支持用户在页面创建智能体， 就像nbaegnt那样的是 promote + tools + mcp + skills 的组合。
`````

--- **end of file: docs/my_docs/task.md** (project: lc_agent) --- 

---

