# Inline Todo Progress Card Design

## Summary

Simplify the `write_todos` implementation by removing backend special-casing, and add inline todo progress cards to the chat message flow. The right panel TodoList is retained.

## Current State (Problem)

- Backend intercepts `write_todos` tool calls in `websocket.py`, converting them to a dedicated `{ type: "todos", todos: [...] }` WebSocket message type
- Frontend has a separate event handler for this message type, updating `chatStore.todos`
- The TodoList only appears in the right panel (`RightPanel.vue`)
- Chat area has zero visibility into todo progress — users must open the right panel (or drawer on mobile) to see it
- Over-engineered: a normal tool call was given special plumbing for no clear benefit

## Design

### Principle

`write_todos` is a regular tool — treat it like one. The frontend decides how to render it based on the tool name.

### Backend Changes

Remove the `write_todos` interception in `websocket.py`. Let it flow through the normal tool_call pipeline:

```
Agent calls write_todos → backend sends { type: "tool_call", name: "write_todos", args: { todos: [...] } }
```

No new backend code needed.

### Frontend Changes

#### 1. Message Rendering (ChatView or ToolCallCard area)

When rendering a tool_call message, check `tool_name`:
- If `name === 'write_todos'` → render `TodoProgressCard.vue`
- Otherwise → render existing `ToolCallCard.vue`

#### 2. New Component: `TodoProgressCard.vue`

Location: `frontend/src/components/chat/TodoProgressCard.vue`

**Compact view (default):**
- Shows the current `in_progress` step text
- Progress indicator: `[completed_count / total_count]` with a mini progress bar
- Spinning/pulse icon to indicate active work
- Click anywhere to expand

**Expanded view:**
- Full list of all todo items with status icons:
  - ✅ `completed`
  - 🔄 `in_progress` (animated)
  - ○ `pending`
- Click to collapse back

**Data extraction:** Parse `args.todos` from the tool_call message payload.

#### 3. Right Panel Data Sync

When a `write_todos` tool_call is received/rendered:
- Extract `args.todos` and update `chatStore.todos`
- Right panel `TodoList.vue` continues to display the latest state as before
- No changes to `TodoList.vue` or `RightPanel.vue`

#### 4. Remove Legacy Plumbing

- Delete the `ws.on('todos', ...)` handler in `chatStore` (or `chat.ts`)
- The `chatStore.todos` reactive ref stays — it's just updated from tool_call data now instead of a dedicated message type

### Visual Design

```
┌─────────────────────────────────────────────────┐
│ 🔄 正在执行: 实现用户认证模块         [2/5] ━━░░░ │  ← compact (default)
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 📋 任务进度                            [2/5]     │  ← expanded
│ ✅ 设计数据库 schema                             │
│ 🔄 实现用户认证模块                              │
│ ○  编写单元测试                                  │
│ ○  集成前端登录页面                              │
│ ○  部署到测试环境                                │
└─────────────────────────────────────────────────┘
```

Card styling should be visually distinct from assistant messages and ToolCallCards — subtle background, rounded corners, no avatar column.

### Behavior Details

- Each `write_todos` call produces its own card in the message flow (multiple cards is expected)
- Cards are non-editable (display only)
- On mobile: cards appear inline in the chat flow naturally (no special mobile handling needed since they're just message items)
- Right panel always shows the LATEST todo state (last write_todos call's data)

## Files to Modify

| File | Change |
|------|--------|
| `lc_agent/server/websocket.py` | Remove `write_todos` interception logic |
| `frontend/src/stores/chat.ts` | Remove `ws.on('todos', ...)` handler; add logic to update `chatStore.todos` from tool_call |
| `frontend/src/components/chat/TodoProgressCard.vue` | **New file** — inline progress card component |
| `frontend/src/components/chat/ToolCallCard.vue` (or parent) | Add routing: if tool name is `write_todos`, render TodoProgressCard instead |

## Out of Scope

- Editing todos from the frontend (stays display-only)
- Changing the right panel TodoList design
- Adding new WebSocket message types
