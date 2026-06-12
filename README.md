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
| AI 引擎 | LangGraph `create_react_agent` |
| 后端 | FastAPI + SQLModel + asyncio |
| 前端 | Vue 3 + TypeScript + Element Plus + Vite |
| 数据库 | SQLite (aiosqlite) |
| 通信 | WebSocket (流式) + REST API |

## License

MIT
