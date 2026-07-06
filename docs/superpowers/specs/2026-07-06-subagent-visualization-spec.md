# 子Agent完整可视化 Spec

## 目标

为 lc-agent 增加子Agent能力：

- 网页创建Agent可配置允许调用哪些子Agent。
- 主Agent通过 `task` 工具调用子Agent。
- 子Agent可以是网页创建Agent，也可以是代码注册Agent。
- 主聊天区只显示子Agent摘要卡片，不刷屏。
- 点击摘要卡片进入完整子Agent运行视图。
- 子Agent运行过程持久化，刷新后仍可查看。
- 支持多层子Agent调用，但必须限制递归深度。

## 非目标

- 不整体迁移到 `deepagents.create_deep_agent`。
- 不让网页编辑代码注册Agent的工具、MCP、Skills、子Agent配置。
- 不在主聊天区展开完整子Agent过程。
- 第一版不提供子Agent过程视图内继续输入。

## 后端 Agent 配置

新增字段：

```python
allowed_sub_agents: list[str] | None = None
```

三值语义保持和工具/MCP/Skills一致：

```text
None = 全部允许
[] = 全部禁止
["agent_a", "agent_b"] = 只允许指定Agent
```

默认策略：

| Agent类型 | 默认值 |
|---|---|
| `__chat__` | `[]` |
| `__empty__` | `[]` |
| `__power__` | `None` |
| 网页新建Agent | `[]` |
| 代码Agent | `[]`，只读展示 |

## 代码Agent边界

1. 网页Agent可以调用代码Agent，因为代码Agent已通过 `app.add_agent()` 注册到 `_agents`，可以作为被调用者。
2. 代码Agent默认不会自动获得 `task` 工具，框架不注入。
3. 代码Agent在前端继续只读，不允许网页配置它的工具/MCP/Skills/子Agent。
4. 代码Agent如果要主动调用子Agent，应由业务代码显式添加调用工具。

## 后端子Agent执行模型

新增轻量 `SubAgentMiddleware`，参考 deepagents 的 `SubAgentMiddleware`，但不整体引入 deepagents。

职责：

- 构建 `task` 工具。
- 注入主Agent系统提示词，列出可用子Agent。
- 校验 `subagent_type` 是否允许。
- 创建子Agent运行记录。
- 调用子Agent。
- 持久化子Agent事件。
- 返回最终结果给主Agent。

工具入参：

```python
class TaskInput(BaseModel):
    description: str
    subagent_type: str
```

工具返回：

```python
Command(
    update={
        "messages": [ToolMessage(content=final_answer, tool_call_id=runtime.tool_call_id)]
    }
)
```

## LangChain 标记规则

为配合 LangChain `SubagentTransformer`，所有由框架构建的网页Agent应调用：

```python
create_agent(..., name=preset.id)
```

代码Agent注册时应包装 runnable：

```python
graph.with_config({
    "metadata": {"lc_agent_name": name},
    "run_name": name,
})
```

这样后续可以从事件 metadata 中识别子Agent归属。

## 子Agent运行隔离

每次子Agent调用创建独立 run：

```text
sub_agent_run_id = uuid
parent_session_id = 主会话ID
parent_tool_run_id = task工具run_id
sub_agent_id = 被调用Agent ID
sub_thread_id = parent_thread_id:sub:parent_tool_run_id:sub_agent_id
```

子Agent使用独立 `thread_id`，避免 checkpoint 混入主Agent。

## 防递归规则

后端维护调用链：

```python
call_stack = ["main_agent", "research_agent", "review_agent"]
```

限制：

- 默认最大深度：`3`。
- 禁止调用已在 `call_stack` 中出现的Agent。
- 默认禁止Agent调用自己。
- 超限时 `task` 工具返回明确错误信息给主Agent。

错误示例：

```text
拒绝调用子Agent：检测到循环调用 main_agent -> research_agent -> main_agent
```

## 持久化模型

### `SubAgentRun`

记录一次子Agent调用：

```python
id: str
parent_session_id: str
parent_message_id: str | None
parent_tool_run_id: str
parent_agent_id: str
sub_agent_id: str
sub_agent_name: str
sub_thread_id: str
task_description: str
status: "running" | "done" | "error" | "cancelled"
summary: str
final_result: str
started_at: datetime
ended_at: datetime | None
depth: int
```

### `SubAgentEvent`

记录子Agent运行过程：

```python
id: str
run_id: str
event_type: str
payload: dict
sequence: int
created_at: datetime
```

事件类型复用现有前端能理解的：

```text
token
thinking
tool_call
tool_result
llm_usage
interrupt
done
error
sub_agent_call
sub_agent_update
sub_agent_done
sub_agent_error
```

## SSE 协议

主Agent流中，子Agent只发摘要事件，不刷屏。

### 子Agent开始

```json
{
  "type": "sub_agent_call",
  "run_id": "sub-run-id",
  "parent_tool_run_id": "tool-run-id",
  "sub_agent_id": "research_agent",
  "sub_agent_name": "research_agent",
  "task_description": "帮我研究...",
  "status": "running",
  "depth": 1
}
```

### 子Agent进度

```json
{
  "type": "sub_agent_update",
  "run_id": "sub-run-id",
  "status": "running",
  "current_step": "正在调用 nbrag_search",
  "tool_call_count": 3,
  "token_count": 1200
}
```

### 子Agent完成

```json
{
  "type": "sub_agent_done",
  "run_id": "sub-run-id",
  "status": "done",
  "summary": "完成研究，找到 5 条相关资料",
  "final_result": "..."
}
```

### 子Agent错误

```json
{
  "type": "sub_agent_error",
  "run_id": "sub-run-id",
  "status": "error",
  "message": "..."
}
```

## 前端主聊天区

主聊天区不展示子Agent详细过程，只展示摘要卡片。

卡片内容：

```text
子Agent：research_agent
任务：帮我研究...
状态：执行中 / 已完成 / 失败
当前步骤：正在调用 nbrag_search
工具调用：3 次
耗时：12.4s
[查看完整过程]
```

卡片位置：

- 作为 `task` 工具调用卡片的特殊渲染。
- 保留在主Agent回复中。
- 刷新页面后仍显示。

## 子Agent完整过程视图

点击“查看完整过程”后，中间聊天区切换到子Agent视图。

顶部：

```text
← 返回主Agent对话
主Agent / research_agent
任务：帮我研究...
状态：已完成
```

内容复用现有聊天渲染：

- thinking 折叠块。
- token 输出。
- 工具调用卡片。
- HTTP trace。
- token usage。
- 错误提示。

多层子Agent：

```text
主Agent / research_agent / code_reviewer
```

点击返回：

- 返回上一级。
- 最终返回主Agent对话。
- 保持主Agent滚动位置。

## 前端数据流

新增 API：

```text
GET /api/sub-agent-runs/{run_id}
GET /api/sub-agent-runs/{run_id}/events
```

可选 API：

```text
GET /api/sessions/{session_id}/sub-agent-runs
```

前端新增 store：

```text
subAgentRunsStore
```

职责：

- 读取 run详情。
- 读取 events。
- 把 events 转成和 `ChatMessage` 类似的数据结构。
- 管理当前视图栈。

## 用户体验规则

- 子Agent运行时，主聊天区摘要卡片实时更新。
- 不在主聊天区展开子Agent全部过程。
- 子Agent过程页只读，不提供继续输入。
- 主Agent取消时，应尽量取消正在运行的子Agent。
- 子Agent失败时，主Agent收到失败工具结果，并继续决定如何回复。
- 子Agent审批 interrupt 第一版沿用现有审批弹窗，但事件归属要显示是哪个子Agent触发。

## 验收标准

- 管理员可在网页Agent编辑器中配置允许调用的子Agent。
- 网页Agent可调用网页Agent。
- 网页Agent可调用代码注册Agent。
- 代码注册Agent仍然只读，框架不会自动给它注入 `task` 工具。
- 未授权子Agent调用会被拒绝。
- 循环调用会被拒绝。
- 主聊天区只显示子Agent摘要卡片。
- 子Agent摘要卡片在运行中实时更新状态。
- 点击摘要卡片可进入完整子Agent过程视图。
- 刷新页面后仍能查看历史子Agent过程。
- 子Agent过程视图可展示 token、thinking、工具调用、工具结果、错误、usage。
- 子Agent最终结果会作为 `ToolMessage` 返回给主Agent。

## 测试策略

后端测试：

- `allowed_sub_agents` 创建/更新/列表。
- 禁止未授权子Agent调用。
- 网页Agent调用网页Agent。
- 网页Agent调用代码Agent。
- 递归调用被阻止。
- 子Agent run/event 持久化。
- `task` 返回 ToolMessage 给主Agent。
- 子Agent失败时状态为 `error`。

前端测试：

- Agent编辑器能配置子Agent。
- 子Agent工具卡正确显示。
- 点击卡片进入过程视图。
- 返回主Agent视图。
- 刷新后仍能打开历史子Agent过程。
