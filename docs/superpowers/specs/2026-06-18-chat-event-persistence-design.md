# 聊天工具调用和 Token 统计持久化设计

**日期：** 2026-06-18
**状态：** 已确认
**范围：** 新产生的聊天回复在刷新页面或重新进入历史会话后，工具调用卡片、工具结果和 Token 统计可以按首次生成时的结构恢复。

## 目标

让 lc-agent 的聊天历史从“只恢复最终文本”升级为“恢复可渲染的回答时间线”。新回复产生时，后端保存本轮 assistant 的工具调用、工具结果、耗时和 Token 用量；历史接口返回这些结构化字段；前端加载历史时使用同一套消息结构渲染。

## 当前问题

实时聊天时，WebSocket 会向前端推送 `tool_call`、`tool_result`、`llm_usage` 和最终 `done`。前端把这些事件临时挂在当前 assistant 消息上，所以首次回答时能看到工具卡片和 Token 面板。

刷新页面或打开历史会话时，前端通过 `/api/sessions/{session_id}/messages` 恢复消息。这个接口目前主要从 LangGraph checkpoint 读取 `messages`，只返回 `role`、`content`、部分 `tool_calls` 和 tool message 信息。它没有返回前端实时渲染所需的完整 UI 元数据，前端也没有重新插入工具占位符，因此历史里工具调用和 Token 统计会消失。

## 非目标

- 不兼容修复前已经生成的老会话。
- 不写数据迁移脚本。
- 不改变 LangGraph checkpoint 的职责。
- 不重做聊天 Markdown 渲染。
- 不改变工具执行协议、Agent 行为或模型调用方式。
- 不追求“流式生成过程逐 token 重播”，只恢复回答完成后的可读结构。

## 持久化策略

新增一张聊天 UI 消息表，保存前端历史回放需要的结构化数据。LangGraph checkpoint 继续负责 Agent 状态；新增表负责 Web UI 展示状态。

每条记录代表一条可展示聊天消息：

- `id`：消息记录 ID。
- `session_id`：所属会话。
- `role`：`user`、`assistant` 或其他可展示角色。
- `content`：最终展示用 Markdown 文本，保留实时渲染时插入的 `<!--TOOL:n-->` 工具占位符。
- `tool_calls`：assistant 消息的工具调用和结果数组。
- `usage`：assistant 消息的 Token 统计和耗时。
- `created_at`：创建时间。

早期开发阶段没有历史包袱，因此不做旧数据兼容。修复上线后，新发送的用户消息和新生成的 assistant 消息都写入这张表。历史接口优先读取这张表；如果某个会话没有 UI 消息记录，则返回空列表或保留现有 checkpoint fallback，但不为老会话补造工具和 Token 数据。

## 数据结构

`tool_calls` 保存为 JSON 数组，每项结构和前端 `ChatMessage.toolCalls` 对齐：

```json
{
  "name": "nbrag_search_and_fetch",
  "runId": "abc",
  "args": {
    "collection_name": "langchain_ai_codes_and_docs",
    "query": "langgraph checkpointer"
  },
  "status": "success",
  "result": "...",
  "duration": 1.42
}
```

`usage` 保存为 JSON 对象，结构和前端 `TokenUsagePanel` 对齐：

```json
{
  "rounds": [
    {
      "round": 1,
      "modelName": "gpt-5",
      "inputTokens": 1200,
      "outputTokens": 320,
      "cacheRead": 400,
      "reasoningTokens": 0,
      "totalTokens": 1520,
      "duration": 2.6
    }
  ]
}
```

## 后端流程

### WebSocket 实时生成

1. 用户发送消息后，服务端立即保存一条 `user` UI 消息。
2. 服务端创建本轮 assistant UI 暂存对象。
3. 收到 `tool_call` 事件时，把工具名称、run id 和参数追加到本轮 assistant 的 `tool_calls`。
4. 收到 `tool_result` 事件时，按 `run_id` 回填对应工具调用的结果、状态和耗时。
5. 收到 `llm_usage` 事件时，把本轮模型调用统计追加到 `usage.rounds`。
6. 生成完成后，保存一条 `assistant` UI 消息，包含最终展示内容、完整 `tool_calls` 和 `usage`。展示内容保留工具占位符，用来恢复工具卡片在回答中的原始位置。

如果生成失败，已保存的用户消息保留；assistant 消息只在有最终内容或可展示错误时保存。失败事件仍通过 WebSocket 返回给前端。

### 历史接口

`GET /api/sessions/{session_id}/messages` 返回 UI 消息表中的记录，并包含：

- `role`
- `content`
- `tool_calls`
- `usage`
- `created_at`

接口字段保持 snake_case，前端在 store 中转换成 camelCase。

## 前端流程

实时 WebSocket 渲染逻辑继续保留。历史加载时，`chat.ts` 把后端返回的 `tool_calls` 转成 `toolCalls`，把 `usage` 转成 `usage`。如果 assistant 内容里已经带有 `<!--TOOL:n-->` 占位符，则直接使用；如果缺少占位符，再按工具顺序兜底插入。

这样 `ChatView.vue` 现有的 `parseSegments(content, toolCalls)` 可以继续工作，历史消息和实时消息走相同渲染路径。

## 测试策略

### 后端测试

新增 repository 测试：

- 可以保存 user UI 消息。
- 可以保存 assistant UI 消息，包含 `tool_calls` 和 `usage`。
- 可以按 session 顺序读取 UI 消息。

新增 session route 测试：

- 当 UI 消息表有记录时，历史接口返回 `tool_calls` 和 `usage`。
- 新接口不需要为老 checkpoint 会话补造 Token 统计。

### 前端测试

新增 store 单元测试：

- `loadMessages()` 能把 `tool_calls` 转成 `toolCalls`。
- assistant 历史消息有工具调用时，会插入对应数量的 `<!--TOOL:n-->` 标记。
- `usage` 会保留到前端消息对象上，供 `TokenUsagePanel` 渲染。

### 验证

使用 Python 3.12 环境运行后端相关测试：

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_sessions.py tests/test_repository.py -q
```

在前端目录运行构建：

```powershell
npm run build
```

## 风险

- WebSocket 里实时事件和持久化事件必须共用同一份累积状态，否则首次展示和历史展示可能不一致。
- 工具结果可能很长，JSON 存储会放大数据库体积；本次先完整保存，后续如果需要再做截断或附件化。
- 如果一次回复中存在多个同名工具调用，必须用 `run_id` 优先匹配工具结果，不能只按工具名匹配。

## 验收标准

- 新会话里调用工具后，首次生成时能看到工具卡片、工具结果和 Token 面板。
- 刷新页面后，同一轮 assistant 回复仍能看到工具卡片、工具结果和 Token 面板。
- 从历史会话列表进入该会话后，展示结果和刷新后保持一致。
- 不要求修复前的老会话恢复工具卡片或 Token 面板。
- 后端相关测试通过。
- 前端构建通过。
