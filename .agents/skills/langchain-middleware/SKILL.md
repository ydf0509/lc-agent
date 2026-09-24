---
name: langchain-middleware
description: >-
  Guide on how to use LangChain's AgentMiddleware to add tools and inject system prompts into
  lc-agent agents, as opposed to registering tools via the @tool decorator.
  Use when adding tools that are tightly coupled with system prompt guidance (e.g. ask_user,
  write_todos), creating middleware that controls which agents receive specific tools,
  or injecting text blocks into agent system messages.
---

# LangChain AgentMiddleware 使用指南

在 lc-agent 里，向 agent 添加 **工具 + 系统提示词** 有两条路：

| 方式 | 适用场景 |
|------|---------|
| `@tool` 装饰器 + `ToolRegistry` | 普通业务工具，所有 agent 都可用，用户可在 UI 中开关 |
| `AgentMiddleware` | 工具和提示词必须**捆绑**出现，或需要**按 agent 条件注入**（如仅顶层 agent）|

---

## 基础类

```python
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage
```

`AgentMiddleware` 有两个扩展点：
- `self.tools`：提供给 agent 的工具列表（可选）
- `wrap_model_call` / `awrap_model_call`：拦截 LLM 调用，修改 request（注入系统提示词）

---

## 模式 1：只注入系统提示词（无工具）

lc-agent 已内置 `SystemPromptMiddleware`，直接使用即可，无需自己实现：

```python
from lc_agent.middlewares import SystemPromptMiddleware
```

**使用：**

```python
middleware.append(SystemPromptMiddleware("你的提示词文本", "MyPromptMiddleware"))
# 前置到 system prompt 最前面：
middleware.append(SystemPromptMiddleware("子 agent 规则", "SubagentRules", prepend=True))
```

如需自行实现（不常见），参考 `lc_agent/middlewares/system_prompt.py` 中的实现。

---

## 模式 2：同时注入工具 + 系统提示词

工具在 `__init__` 里用 `@tool` 创建，挂到 `self.tools`；系统提示词通过 `wrap_model_call` 注入。

```python
from typing import Annotated, Any
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command, interrupt

SYSTEM_PROMPT = "<my_tool_rules>\n...使用规则...\n</my_tool_rules>"

class MyToolMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        super().__init__()

        @tool(description="工具对 LLM 的描述")
        def _my_tool(
            param: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command[Any]:
            """工具函数 docstring（可选）。"""
            # 如果需要阻断执行等待用户输入：
            response = interrupt({"type": "my_tool", "param": param, "tool_call_id": tool_call_id})
            # 处理 response，返回 Command
            return Command(update={"messages": [ToolMessage("结果", tool_call_id=tool_call_id)]})

        _my_tool.name = "my_tool"   # 设置 LLM 看到的工具名
        self.tools = [_my_tool]

    def _patched_system(self, existing):
        new_content = [*(existing.content_blocks if existing else []),
                       {"type": "text", "text": f"\n\n{SYSTEM_PROMPT}"}]
        return SystemMessage(content_blocks=new_content)

    def wrap_model_call(self, request, handler):
        return handler(request.override(system_message=self._patched_system(request.system_message)))

    async def awrap_model_call(self, request, handler):
        return await handler(request.override(system_message=self._patched_system(request.system_message)))
```

---

## 关键规则

### 1. `interrupt()` 只能在顶层 agent 中使用
`interrupt()` 依赖 LangGraph checkpoint，需要前端 SSE 监听同一 `thread_id`。
子 agent（`_depth > 0`）有独立的 `thread_id`，前端不会收到其 interrupt 事件，会导致死锁。

```python
# engine.py 中的正确做法——只在顶层注入带 interrupt 的 middleware
if _depth == 0:
    middleware.append(MyInterruptMiddleware())
```

### 2. `@tool` 工具名和函数名解耦
在 `__init__` 内用 `_my_tool.name = "my_tool"` 手动设置 LLM 看到的工具名，
避免内部函数名（以 `_` 开头）泄露给 LLM。

### 3. 工具不需要在 ToolRegistry 注册
middleware 提供的工具通过 `self.tools` 传给 `create_agent`，不经过 `ToolRegistry`。
这类工具不会出现在 Web UI 的工具开关列表中。

### 4. 不要写 `from __future__ import annotations`
lc-agent 禁止在任何文件顶部写此语句。`@tool`/`@lc_tool` 装饰器使用 `get_type_hints()`
动态解析注解，该语句会导致局部变量 `NameError`。

---

## lc-agent 已有 middleware 示例

| Middleware | 位置 | 提供工具 | 注入提示词 |
|-----------|------|---------|---------|
| `AskUserMiddleware` | `lc_agent/middlewares/ask_user.py` | `ask_user` | `ASK_USER_SYSTEM_PROMPT` |
| `QuickToolsMiddleware` | `lc_agent/middlewares/quick_tools.py` | 任意工具列表 | 可选静态文本 |
| `SystemPromptMiddleware` | `lc_agent/middlewares/system_prompt.py` | 无 | 任意文本块 |
| `TodoListMiddleware` | `langchain.agents.middleware` | `write_todos` | todo 使用规则 |
| `SkillsMiddleware` | `nb_langchain_agentskills` | `skill__load_skill` 等 | skills 列表 |
| `SummarizationMiddleware` | `langchain.agents.middleware` | 无 | 上下文摘要规则 |

---

## 模式 3：快速注入工具 + 提示词（推荐用法）

不需要写 middleware 类时，直接使用 `QuickToolsMiddleware`：

```python
from lc_agent.middlewares import QuickToolsMiddleware
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述。"""
    return f"结果: {param}"

# 在 build_agent() 中
middleware.append(
    QuickToolsMiddleware(
        middleware_name="MyToolsMiddleware",
        tools=[my_tool],
        system_prompt="你有 `my_tool` 工具，使用时注意……",
    )
)
```

仅注入工具、不注入提示词时省略 `system_prompt`：

```python
middleware.append(QuickToolsMiddleware(middleware_name="MyTools", tools=[tool1, tool2]))
```

> **注意**：`QuickToolsMiddleware` 适合无需拦截执行流（不用 `interrupt()`）的场景。  
> 需要 `interrupt()` 或复杂拦截逻辑时，还是写专用 middleware 类（参见模式 2）。

---

## 在 engine.py 中挂载

```python
# build_agent() 中，按条件追加 middleware
if _depth == 0:
    middleware.append(MyInterruptMiddleware())     # 仅顶层
middleware.append(SystemPromptMiddleware("..."))   # 所有 agent
```

middleware 列表最终传给 `create_agent(middleware=middleware, ...)`。
