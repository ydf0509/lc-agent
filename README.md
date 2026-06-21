# lc-agent

基于 LangChain / LangGraph 的 AI Agent 框架，内置 Web UI。lc-agent 既是框架又是产品。
用户可以在自己项目导入lc-agent框架，使用langchain框架开发自己的具体的agent应用；用户也可以不写代码，直接在页面创建配置智能体。

[lc-agent-bfzs](https://github.com/ydf0509/lc-agent-bfzs) 是基于lc-agent框架开发的自定义项目,是用于演示使用lc-agent框架的项目。

## 定位

lc-agent 是一个**可导入的框架**，用户在自己的项目中 `import lc_agent` 来开发自定义 Agent 应用，无需 clone 或修改框架代码。 用户如果一行代码不会写，也可以使用他来接入mcp和skills来实现agent，这就好比你使用codex claudecode opencode等工具，虽然你不会改造codex claudecode的源码但是可以接入mcp 和skills来实现自己的个性化agent。

如果你啥mcp 和skills都不配置，直接使用lc-agent。只配置baseurl 和apikey，那么也可以使用内置的chat智能体，就是那种不能执行工具的，就好像你在deepseek 豆包网页上聊天那种，此时大模型只能聊天不能调用工具操作你的电脑。

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

## 自问自答
### 1. lc-agent 能做什么？
答：
可以当做是openwebui privategpt来使用，自定义apikey和baseurl，实现聊天功能。
也可以当做是codex claudecode opencode来使用，配置编程专用mcp serena和skills。
可以当做是langchain 智能体的管理界面，管理自己的智能体，同时支持热切换模型 skills  mcp tools，比频繁修改代码然后重启在控制台循环提问好很多。

### 2. lc-agent 比一般的llm网页聊天工具有什么优势？
答：
lc-agent比一般的llm网页聊天项目录入openwebui这种，加了更多可视化利于码农调试agent的内容
例如把工具调用入参和响应时间和返回内容可视化做得非常好，几乎等同于有了langsmith langfuse那种可观测性了，
把agent会话的每一轮tokens 消耗、缓存命中详细记录，让人心里有谱，花了多少tokens

### 3. lc-agent 知否有rag知识库的功能？

答： [nbrag](https://github.com/ydf0509/nbrag) ，lc-agent不重复实现rag知识库，通过把nbrag这个mcp配置给agent，实现agentic rag功能，nbrag远超dify 和 openwebui 内置的知识库检索能力。


## License

MIT
