# A2A 协议实现规范（v1.0）

> 目标：在 lc-agent 上实现 A2A（Agent2Agent）协议服务端，让 lc-agent 能被其它 agent / 编排系统按官方标准调用。
> 本文档所有字段、方法名、错误码均对照 **A2A 官方仓库 v1.0 原始规范** 编写，避免凭印象实现导致不标准。

**权威资料（2026-09-02 抓取）**

| 来源 | 内容 | 地址 |
|---|---|---|
| `specification/a2a.proto`（812 行，`package lf.a2a.v1`） | 全部消息/枚举/service 的**最终权威字段定义** | `github.com/a2aproject/A2A` |
| `docs/specification.md` | v1.0 文本规范（方法映射、JSON 约定、错误映射、SSE） | 同上 |
| `src/a2a/types/__init__.py` | Python SDK 类型导出清单 | `github.com/a2aproject/a2a-python` |
| `src/a2a/utils/errors.py` | Python SDK 错误码表 | 同上 |
| `a2a-sdk`（**PyPI，实测 1.1.2**） | 官方 Python SDK，**自带完整 A2A server**（见 §11），非仅类型 | `pip install "a2a-sdk[jsonrpc]"` |

> **落地方式重大更新（2026-09-02）**：已实际安装 `a2a-sdk 1.1.2` 验证——**lc-agent 不需要手搓 §1–§8 描述的协议层**。官方 SDK 把路由、任务状态机、持久化、SSE 全部做好了，lc-agent 只需实现一个 `AgentExecutor` 适配器把 `engine.chat()` 翻译成事件流。§1–§8 仍保留作为字段/约定对照基准；**真正动手时按 §11 走**。

---

## 0. 先说清最容易搞错的三件事

### 0.1 方法名是 PascalCase，不是斜杠式

- **JSON-RPC 层**（我们主要做的）：方法名是 `SendMessage`、`GetTask`、`CancelTask` 这种 **PascalCase**。
- **REST 层**（gRPC 的 http 注释）：才用 `POST /message:send`、`POST /tasks/{id}:cancel` 这种带冒号的路径。

⚠️ 网上很多教程和早期实现写的是斜杠式 `message/send`，那是 **HTTP+REST 绑定**，不是 JSON-RPC 绑定。两者别混。

### 0.2 JSON 字段是 camelCase，枚举是 SCREAMING_SNAKE_CASE

proto 里字段名是 snake_case（如 `context_id`），但 **JSON 序列化必须转 camelCase**：

| proto 字段 | JSON 字段 |
|---|---|
| `context_id` | `contextId` |
| `protocol_version` | `protocolVersion` |
| `default_input_modes` | `defaultInputModes` |
| `artifact_id` | `artifactId` |

枚举值序列化为大写字符串：

| proto 枚举 | JSON 值 |
|---|---|
| `TASK_STATE_INPUT_REQUIRED` | `"TASK_STATE_INPUT_REQUIRED"` |
| `ROLE_USER` | `"ROLE_USER"` |
| `ROLE_AGENT` | `"ROLE_AGENT"` |

### 0.3 需要传版本头 `A2A-Version`

- 客户端**每个请求都带** `A2A-Version: 1.0` 头（HTTP 或 query 参数均可）。
- 服务端不支持则返回 `VersionNotSupportedError`（JSON-RPC code `-32009`）。
- 空值按 `0.3` 处理。

---

## 1. 接口总清单（JSON-RPC 绑定）

A2A 协议共定义 **11 个 JSON-RPC 方法**。除此之外还有一个 **Agent Card 发现端点**（不算 RPC 方法）。

> 之前讨论里我说"规范 12 个 / 实写 2 个"，那是不完整口径。严格按 v1.0：**服务端要实现的 RPC = 11 个方法 + 1 个静态发现端点**。其中对 lc-agent 真正核心的是前 4 个，push notification 4 个 + extended card 1 个可暂缓。

| # | JSON-RPC method | 请求 | 成功响应 | 用途 | lc-agent 工作量 |
|---|---|---|---|---|---|
| 1 | `SendMessage` | `SendMessageRequest` | `SendMessageResponse` | 发消息，同步等到终态 | 薄封装 `engine.chat()` |
| 2 | `SendStreamingMessage` | `SendMessageRequest` | `stream StreamResponse` | 流式版 | 复用 SSE |
| 3 | `GetTask` | `GetTaskRequest` | `Task` | 查单任务状态 | 薄封装 |
| 4 | `ListTasks` | `ListTasksRequest` | `ListTasksResponse` | 列任务（过滤/分页） | 薄封装 |
| 5 | `CancelTask` | `CancelTaskRequest` | `Task` | 取消任务 | **直接映射**已有 cancel |
| 6 | `SubscribeToTask` | `SubscribeToTaskRequest` | `stream StreamResponse` | 断线重连订阅 | **新写**（维护连接表） |
| 7 | `CreateTaskPushNotificationConfig` | `TaskPushNotificationConfig` | `TaskPushNotificationConfig` | 建 webhook 通知 | 跳过/可缓 |
| 8 | `GetTaskPushNotificationConfig` | `GetTaskPushNotificationConfigRequest` | `TaskPushNotificationConfig` | 查通知配置 | 跳过/可缓 |
| 9 | `ListTaskPushNotificationConfigs` | `ListTaskPushNotificationConfigsRequest` | `ListTaskPushNotificationConfigsResponse` | 列通知配置 | 跳过/可缓 |
| 10 | `DeleteTaskPushNotificationConfig` | `DeleteTaskPushNotificationConfigRequest` | `google.protobuf.Empty` | 删通知配置 | 跳过/可缓 |
| 11 | `GetExtendedAgentCard` | `GetExtendedAgentCardRequest` | `AgentCard` | 认证后拿扩展卡 | 跳过/可缓 |

**Agent Card 发现端点**（非 RPC）：`GET /.well-known/agent-card.json` → `AgentCard`（静态 JSON）。

---

## 2. JSON-RPC 传输封装

lc-agent 用 FastAPI，**一个 POST 路由 + 一个 method dispatcher** 即可。JSON-RPC over HTTP。

### 2.1 传输绑定选择

v1.0 支持三种绑定，我们只做 **JSON-RPC**：

| 绑定 | 说明 | 用不用 |
|---|---|---|
| JSONRPC | JSON-RPC 2.0 over HTTP | ✅ 用这个 |
| GRPC | 走 `A2AService` proto service | 暂不做 |
| HTTP+JSON | REST（`/message:send` 等） | 暂不做 |

### 2.2 HTTP 端点 URL

规范**不强制统一路径**，由 Agent Card 的 `supportedInterfaces[].url` 声明。
社区通行做法是 `POST /a2a`（如 LangGraph 也支持类似形态）。建议 lc-agent 用：

```
POST /.well-known/agent-card.json   # Agent Card 发现
POST /a2a                           # JSON-RPC 入口（所有 11 个方法）
```

### 2.3 JSON-RPC 2.0 请求

```http
POST /a2a HTTP/1.1
Host: agent.example.com
Content-Type: application/json
A2A-Version: 1.0
```

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [{ "text": "分析这个仓库的依赖" }],
      "messageId": "msg-uuid-1"
    }
  }
}
```

### 2.4 JSON-RPC 2.0 成功响应

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "task": {
      "id": "task-uuid-9f2c",
      "contextId": "ctx-uuid",
      "status": {
        "state": "TASK_STATE_COMPLETED",
        "timestamp": "2026-09-02T08:00:00Z"
      },
      "artifacts": [
        {
          "artifactId": "art-uuid",
          "name": "依赖分析结果",
          "parts": [{ "text": "共发现 47 个直接依赖……" }]
        }
      ]
    }
  }
}
```

注意 `result` 字段直接是 `SendMessageResponse` 对象，含 `task` / `message` 二选一（见 §7）。

### 2.5 JSON-RPC 2.0 错误响应

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "error": {
    "code": -32001,
    "message": "Task not found"
  }
}
```

错误对象**只有** `code` + `message`，没有 A2A 的 data 字段（与部分早期实现不同，v1.0 Python SDK 即如此）。

---

## 3. 核心类型定义（全部字段，来源 `a2a.proto`）

### 3.1 `Task`（核心单位）

```jsonc
{
  "id": "task-uuid",          // REQUIRED, server 生成
  "contextId": "ctx-uuid",    // 一组交互的上下文 ID（对应 lc-agent 的会话/thread）
  "status": { ... },          // REQUIRED, TaskStatus
  "artifacts": [ ... ],       // 任务产物 Artifact[]
  "history": [ ... ],         // 交互历史 Message[]（可省略以减负）
  "metadata": { }             // 自定义 KV
}
```

### 3.2 `TaskStatus`

```jsonc
{
  "state": "TASK_STATE_WORKING",  // REQUIRED
  "message": null,                // 可选 Message（如请求输入时填）
  "timestamp": "2026-09-02T08:00:00Z"  // ISO8601 UTC
}
```

### 3.3 `TaskState` 枚举（9 个值）

| 值 | 含义 | 类别 |
|---|---|---|
| `TASK_STATE_UNSPECIFIED` | 未知 | — |
| `TASK_STATE_SUBMITTED` | 已提交待处理 | 进行中 |
| `TASK_STATE_WORKING` | 处理中 | 进行中 |
| `TASK_STATE_COMPLETED` | 成功完成 | **终态** |
| `TASK_STATE_FAILED` | 出错结束 | **终态** |
| `TASK_STATE_CANCELED` | 被取消 | **终态** |
| `TASK_STATE_INPUT_REQUIRED` | 需用户输入 | **中断态**（interrupted） |
| `TASK_STATE_REJECTED` | agent 拒绝执行 | **终态** |
| `TASK_STATE_AUTH_REQUIRED` | 需认证 | **中断态** |

> **→ lc-agent 映射**（关键！）：
> `INPUT_REQUIRED` = 你的 HITL 审批 / AskUser interrupt。
> `AUTH_REQUIRED` = 你可不用（你有自己的 JWT）。
> `REJECTED` = 你可在权限拦截/任务被拒时使用。

### 3.4 `Message`

```jsonc
{
  "messageId": "msg-uuid",   // REQUIRED, 由发送方生成
  "contextId": "ctx-uuid",   // 可选
  "taskId": "task-uuid",     // 可选
  "role": "ROLE_USER",       // REQUIRED: ROLE_USER | ROLE_AGENT
  "parts": [ ... ],          // REQUIRED, Part[]
  "metadata": {},
  "extensions": [],
  "referenceTaskIds": []     // 引用其它任务作上下文
}
```

### 3.5 `Part`（oneof content：text | raw | url | data）

```jsonc
// 纯文本
{ "text": "……" }

// 文件 base64（raw）
{ "raw": "<base64>", "filename": "doc.pdf", "mediaType": "application/pdf" }

// 文件 URL
{ "url": "https://…", "filename": "doc.pdf", "mediaType": "application/pdf" }

// 结构化数据（JSON）
{ "data": { "foo": 1 } }
```

公共字段：`metadata`、`filename`、`mediaType`（mediaType 对所有类型都可用）。

### 3.6 `Artifact`（任务产物）

```jsonc
{
  "artifactId": "art-uuid",   // REQUIRED, task 内唯一
  "name": "分析结果",
  "description": "…",
  "parts": [ ... ],           // REQUIRED, 至少一个
  "metadata": {},
  "extensions": []
}
```

> **→ lc-agent 映射**：`Artifact` 对应 `file_changes` 表 / 产出的 diff / 最终回答文本。

### 3.7 `Role` 枚举

- `ROLE_USER`（客户端 → 服务端）
- `ROLE_AGENT`（服务端 → 客户端）

---

## 4. 各方法的请求/响应结构（精确字段）

### 4.1 `SendMessage` / `SendStreamingMessage`

**请求 `SendMessageRequest`**

```jsonc
{
  "tenant": "…",             // 可选，多 agent 路由
  "message": { ... },        // REQUIRED, Message
  "configuration": {         // SendMessageConfiguration
    "acceptedOutputModes": ["text/plain"],
    "historyLength": 10,     // 限制返回历史条数
    "returnImmediately": false  // true=提交即返回；false=等终态
  },
  "metadata": {}
}
```

**`SendMessageConfiguration` 关键字段**

- `returnImmediately`：`true` 则马上返回（不等执行完）；`false`（默认）**必须等到终态或中断态**才返回。
- `historyLength`：`0` = 不带历史；缺省 = 不限制。

**成功响应 `SendMessageResponse`**（`task` / `message` 二选一 oneof）：

```jsonc
{ "task": { ... } }      // 或
{ "message": { ... } }
```

> `SendMessage` 和 `SendStreamingMessage` 用**同一个请求类型**，只是后者走流式返回。

### 4.2 `GetTask`

**请求 `GetTaskRequest`**

```jsonc
{ "tenant": "…", "id": "task-uuid", "historyLength": 10 }  // id REQUIRED
```

**响应**：`Task`。

### 4.3 `ListTasks`

**请求 `ListTasksRequest`**

```jsonc
{
  "tenant": "…",
  "contextId": "ctx-uuid",        // 过滤：某会话的任务
  "status": "TASK_STATE_WORKING", // 过滤：按状态
  "pageSize": 50,                 // 1~100，缺省 50
  "pageToken": "…",
  "historyLength": 5,
  "statusTimestampAfter": "…",    // ISO8601 过滤
  "includeArtifacts": false
}
```

**响应 `ListTasksResponse`**

```jsonc
{
  "tasks": [ ... ],        // REQUIRED
  "nextPageToken": "",     // REQUIRED, 无更多则空
  "pageSize": 50,          // REQUIRED
  "totalSize": 3           // REQUIRED, 分页前总数
}
```

### 4.4 `CancelTask`

**请求 `CancelTaskRequest`**

```jsonc
{ "tenant": "…", "id": "task-uuid", "metadata": {} }  // id REQUIRED
```

**响应**：更新后的 `Task`（state 应为 `TASK_STATE_CANCELED`）。

> lc-agent 已有 `POST /api/threads/{id}/runs/cancel`，直接映射，改响应格式即可。

### 4.5 `SubscribeToTask`

**请求 `SubscribeToTaskRequest`**

```jsonc
{ "tenant": "…", "id": "task-uuid" }  // id REQUIRED
```

**响应**：`stream StreamResponse`。

> ⚠️ 若任务已在终态，须返回 `UnsupportedOperationError`（-32004）。
> 用途：SSE 断线后重连，补收错过的更新。

### 4.6 push notification 四件套（可暂缓）

- `CreateTaskPushNotificationConfig`：请求直接是 `TaskPushNotificationConfig`
- `GetTaskPushNotificationConfig`：请求 `GetTaskPushNotificationConfigRequest`（`taskId`,`id`）
- `ListTaskPushNotificationConfigs`：请求 `ListTaskPushNotificationConfigsRequest`（`taskId`）
- `DeleteTaskPushNotificationConfig`：请求 `DeleteTaskPushNotificationConfigRequest`（`taskId`,`id`），成功返回空

> **建议暂缓**。这是给"客户端无法保持长连接"场景用的 webhook 回调。lc-agent 自己有 SSE + 钉钉/企微/飞书推送，功能重叠。Agent Card 里把 `capabilities.pushNotifications` 声明为 `false` 即可合规跳过。

### 4.7 `GetExtendedAgentCard`

- 请求 `GetExtendedAgentCardRequest`（`tenant`）
- 成功返回 `AgentCard`，认证后给更详细信息
- **建议暂缓**，Agent Card 里 `capabilities.extendedAgentCard: false`。

---

## 5. `TaskPushNotificationConfig` 结构

```jsonc
{
  "tenant": "…",
  "id": "config-uuid",     // server 分配
  "taskId": "task-uuid",
  "url": "https://…",      // REQUIRED, 通知回调地址
  "token": "…",            // 本次会话专属 token
  "authentication": {      // AuthenticationInfo
    "scheme": "Bearer",    // REQUIRED, IANA HTTP auth scheme
    "credentials": "…"
  }
}
```

---

## 6. Agent Card（能力声明 + 发现）

### 6.1 发现机制

服务端需在 `GET /.well-known/agent-card.json` 暴露 Agent Card。客户端（其它 agent）先拉这个卡，才知道"你是谁、会什么、怎么连、要什么认证"。

### 6.2 `AgentCard` 全部字段

```jsonc
{
  "name": "lc-agent BFZS 业务agent",        // REQUIRED
  "description": "能读文件、改代码、跑命令的 coding agent",  // REQUIRED
  "supportedInterfaces": [ {                // REQUIRED, 首个为优先
    "url": "https://host/a2a",              // REQUIRED
    "protocolBinding": "JSONRPC",           // REQUIRED: JSONRPC|GRPC|HTTP+JSON
    "tenant": "…",                          // 可选多 agent 路由
    "protocolVersion": "1.0"                // REQUIRED
  } ],
  "provider": {                             // 可选
    "url": "https://lc-agent…",
    "organization": "…"
  },
  "version": "1.0.0",                       // REQUIRED, agent 自身版本
  "documentationUrl": null,
  "capabilities": {                         // REQUIRED
    "streaming": true,
    "pushNotifications": false,
    "extensions": [],
    "extendedAgentCard": false
  },
  "securitySchemes": {},                    // map<string, SecurityScheme>
  "securityRequirements": [],
  "defaultInputModes": ["text/plain"],      // REQUIRED, media types
  "defaultOutputModes": ["text/plain"],     // REQUIRED
  "skills": [ {                             // REQUIRED
    "id": "code-agent",
    "name": "代码代理",
    "description": "读改文件、执行命令",
    "tags": ["coding", "python"],
    "examples": [],
    "inputModes": [],
    "outputModes": []
  } ],
  "signatures": [],
  "iconUrl": null
}
```

> **→ lc-agent 映射**：每个 `AgentSkill` = 一个 agent 预设（工具组 / MCP / Skills / 系统提示）。`supportedInterfaces.url` = 你实际的 `/a2a` 地址。

### 6.3 `AgentCapabilities` 字段

```jsonc
{
  "streaming": true,          // 是否支持流式
  "pushNotifications": false, // 是否支持 webhook 推送
  "extensions": [],           // 协议扩展声明
  "extendedAgentCard": false  // 是否支持认证后的扩展卡
}
```

### 6.4 `SecurityScheme`（OpenAPI 3.2 Security Scheme 风格）

discriminated union，五选一：`apiKeySecurityScheme` / `httpAuthSecurityScheme` / `oauth2SecurityScheme` / `openIdConnectSecurityScheme` / `mtlsSecurityScheme`。最常见的简化用法：

```jsonc
{
  "authScheme": {
    "httpAuthSecurityScheme": { "scheme": "Bearer" }
  }
}
```

> 若 lc-agent 有自己的 JWT / API key 鉴权，在 Agent Card 里如实声明；没有则 security 相关字段留空即可。

---

## 7. 流式事件（`StreamResponse`）

`SendStreamingMessage` 与 `SubscribeToTask` 返回流。每个事件是 `StreamResponse`（oneof，四选一）：

```jsonc
{ "task": { ... } }                       // 初始任务态
{ "message": { ... } }                    // agent 直接回的消息
{ "statusUpdate": {                       // 任务状态变化
    "taskId": "…", "contextId": "…",
    "status": { "state": "TASK_STATE_WORKING" }
} }
{ "artifactUpdate": {                     // 产物增量
    "taskId": "…", "contextId": "…",
    "artifact": { ... },
    "append": false,          // true=追加到同名产物
    "lastChunk": false        // true=该产物最后一个 chunk
} }
```

### 7.1 SSE over HTTP 示例

```
Content-Type: text/event-stream

data: {"task": {"id":"task-uuid","contextId":"ctx","status":{"state":"TASK_STATE_WORKING"}}}

data: {"artifactUpdate": {"taskId":"task-uuid","contextId":"ctx","artifact":{"artifactId":"a1","parts":[{"text":"# 报告\n\n"}]}}}

data: {"artifactUpdate": {"taskId":"task-uuid","contextId":"ctx","artifact":{"artifactId":"a1","parts":[{"text":"更多内容"}]},"append":true,"lastChunk":true}}

data: {"statusUpdate": {"taskId":"task-uuid","contextId":"ctx","status":{"state":"TASK_STATE_COMPLETED"}}}
```

> **→ lc-agent**：已有 SSE 基础设施。只需把 agent 运行时的 tool-call / 文本增量 / 状态流转，翻译成 `StreamResponse` 的四种事件帧。

---

## 8. 错误码（JSON-RPC code）全表

来源：Python SDK `utils/errors.py` 的 `JSON_RPC_ERROR_CODE_MAP`。

### 8.1 A2A 专属错误（负数业务码）

| Error | JSON-RPC code | HTTP | gRPC | 何时抛 |
|---|---|---|---|---|
| `TaskNotFoundError` | **-32001** | 404 | NOT_FOUND | task 不存在 |
| `TaskNotCancelableError` | **-32002** | 400 | FAILED_PRECONDITION | 任务不可取消 |
| `PushNotificationNotSupportedError` | **-32003** | 400 | FAILED_PRECONDITION | 不支持推送却收到配置请求 |
| `UnsupportedOperationError` | **-32004** | 400 | FAILED_PRECONDITION | 操作不支持（如订阅终态任务） |
| `ContentTypeNotSupportedError` | **-32005** | 400 | INVALID_ARGUMENT | media type 不支持 |
| `InvalidAgentResponseError` | **-32006** | 500 | INTERNAL | agent 返回不合规范 |
| `ExtendedAgentCardNotConfiguredError` | **-32007** | 400 | FAILED_PRECONDITION | 未配置扩展卡却请求 |
| `ExtensionSupportRequiredError` | **-32008** | 400 | FAILED_PRECONDITION | 需要扩展而客户端没声明 |
| `VersionNotSupportedError` | **-32009** | 400 | FAILED_PRECONDITION | 版本不支持 |

### 8.2 标准 JSON-RPC 错误

| Error | JSON-RPC code |
|---|---|
| `JSONParseError` | -32700 |
| `InvalidRequestError` | -32600 |
| `MethodNotFoundError` | -32601 |
| `InvalidParamsError` | -32602 |
| `InternalError` | -32603 |

---

## 9. lc-agent 落地要点

> ⚠️ **本节是"手搓方案"视角的旧评估（保留作理解各方法工作量）。**
> 决定用官方 SDK（§11）后，**§9.1 那几张工作量表不再成立**——路由/状态机/存储都由 SDK 承担，
> 真正要写的只有一个 `AgentExecutor` 适配器。§9.2 状态映射、§9.3 模型映射、§9.4 易错点在 SDK 方案下依然有效（决定了你适配器里怎么写）。

### 9.1 工作量分档

| 档位 | 方法 | 说明 |
|---|---|---|
| **直接映射** | `CancelTask` | 已有 cancel 路由，改响应格式 |
| **薄封装** | `SendMessage` / `SendStreamingMessage` / `GetTask` / `ListTasks` | 都调 `engine.chat()` 或查会话状态 |
| **新写** | `SubscribeToTask` | 需维护 SSE 连接注册表 |
| **跳过（声明 false）** | 4 个 push notification + `GetExtendedAgentCard` | Agent Card 声明不支持即可合规 |

### 9.2 状态映射表（最容易做错，务必按此）

| A2A `TaskState` | lc-agent 对应 |
|---|---|
| `SUBMITTED` | 消息入库、任务刚建 |
| `WORKING` | agent 执行中（LLM 调用 / 工具调用） |
| `COMPLETED` | 正常结束 |
| `FAILED` | 异常结束 |
| `CANCELED` | 用户取消 |
| **`INPUT_REQUIRED`** | **HITL 审批 / AskUser interrupt**（你有基础，见 FEATURES 的 interrupt 检测） |
| `REJECTED` | 权限拦截 / 任务被拒（可选用） |
| `AUTH_REQUIRED` | 不用（有自己的 JWT） |

### 9.3 模型映射

- `Task` ≈ thread + checkpoint
- `Task.contextId` ≈ 你的会话/thread id
- `Artifact` ≈ `file_changes` 表 / 产出 diff / 最终回答
- `AgentSkill` ≈ agent 预设
- `role=ROLE_USER` ≈ 用户消息；`ROLE_AGENT` ≈ agent 消息

### 9.4 一个易错点（提前处理）

**方法名大小写/风格不统一的历史包袱**：官方 v1.0 用 PascalCase JSON-RPC，但社区早期实现（Atlassian 迁移文档、部分框架）混用过 PascalCase 兼容别名、斜杠式 REST。**建议 dispatcher 做一层规范化**：收到方法名先匹配 `SendMessage`/`sendMessage`/`message/send` 等变体。否则对接别的 agent 时容易在"方法找不到"上浪费半天。

### 9.5 与 langgraph 的 A2A 能力对齐

lc-agent 是 LangGraph 生态项目。**动工前先翻 langgraph 自带 / LangSmith Agent Server 的 A2A 实现**（Task 状态管理 + 事件流设计），能复用就复用，别自造轮子。官方 MCP 工具 `docs-langchain` / `nbrag`（知识库含 langgraph 源码）可查最新用法。

---

## 10. 推荐的实现顺序（每步可独立验证）

1. **Agent Card 发现端点** `GET /.well-known/agent-card.json`（静态 JSON，先做——做完整世界就能发现你）
2. **`SendMessage` + `GetTask`**（最小闭环：同步调用跑通，`returnImmediately=false` 等到终态）
3. **`SendStreamingMessage`**（复用现有 SSE，事件包一层 `StreamResponse`）
4. **`CancelTask`**（映射已有 cancel，半小时）
5. **`ListTasks`**（过滤 + 分页）
6. **`SubscribeToTask`**（最后做，需维护连接注册表）

做完 1–4 的同步+取消闭环，lc-agent 就能被别的 agent 调用了；流式是第二步。

> 🔄 **若采用 §11 的官方 SDK 方案，本节的 1–6 全由 SDK 承担，无需手写。** 保留本节仅为理解协议演进脉络。

---

## 11. 推荐落地：直接复用官方 SDK（实测验证 2026-09-02）

> **这是现在真正推荐的实现方式。** 已实际安装 `a2a-sdk 1.1.2` 于 py312 环境并逐一翻源码验证，结论：**官方 SDK 自带完整 A2A server，lc-agent 只需写一个 AgentExecutor 适配器**。§1–§8 的字段/约定/错误码是适配时的对照基准。

### 11.1 SDK 提供了什么（实测目录结构）

安装：`pip install "a2a-sdk[jsonrpc]"`（实测得到 1.1.2，连带 `json-rpc 1.15.0` / `aiologic` / `culsans`）。

| 模块 | 提供了 | lc-agent 还用写吗 |
|---|---|---|
| `a2a.server.routes` | `add_a2a_routes_to_fastapi(app,…)` 一键挂载全部端点；`create_agent_card_routes` / `create_jsonrpc_routes` / `create_rest_routes`；版本头校验 + OpenAPI `/docs` 标注 | **不用** |
| `a2a.server.request_handlers.default_request_handler_v2` → `DefaultRequestHandlerV2` | **已实现全部 11 个 RPC 方法**：任务状态机 / 持久化 / 流式 / 订阅 / push 配置 / GetExtendedAgentCard | **不用** |
| `a2a.server.tasks.TaskStore` | 会话/任务持久化（自带 alembic 迁移），无参可建 | **不用**（可复用，不必接 lc-agent sessions 表） |
| `a2a.types` | 全部 proto 生成类型 + pydantic 模型（`AgentCard`/`Task`/`Message`/`Part`/`StreamResponse`…） | **不用** |
| `a2a.server.agent_execution.agent_executor.AgentExecutor` | **用户唯一扩展点，抽象类** | ✅ **只实现这个** |

### 11.2 唯一的扩展点：`AgentExecutor`（只 2 个抽象方法）

```python
class AgentExecutor(ABC):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None: ...
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None: ...
```

**关键语义（决定适配器怎么写）：**

1. **事件驱动，不是返回**：`execute()` 里**不要 return 消息**，而是读 `context` 里的用户 `Message`，跑 `engine.chat()`，再把结果**发布到 `event_queue`**（`Task` / `Message` / `TaskStatusUpdateEvent` / `TaskArtifactUpdateEvent`）。框架负责状态机与落库。
2. **中断 = 发状态后 return**：HITL/AskUser 中断 → 发布 `TaskState.TASK_STATE_INPUT_REQUIRED` 的状态事件后 `return`，任务进入中断态；用户回复后框架会再次调 `execute()` 续跑。
3. **取消**：客户端 CancelTask → 框架 cancel 正在跑的 `execute()`（抛 `asyncio.CancelledError`）+ 显式调 `cancel()`；`cancel()` 里发布 `TASK_STATE_CANCELED` 状态事件即可。
4. **终态**：正常跑完前应发布 `TASK_STATE_COMPLETED` 状态事件（或 `TASK_STATE_FAILED`）；未处理异常会被框架捕获并转 `TASK_STATE_ERROR`。
5. **单飞保证**：框架保证同一请求不会并发调 `execute()`；`execute()` 返回后不能再碰 `context`/`event_queue`。

### 11.3 lc-agent 适配器骨架（≈30 行接线 + 一个执行器）

```python
from a2a.types import AgentCard, AgentSkill
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.request_handlers.default_request_handler_v2 import DefaultRequestHandlerV2
from a2a.server.tasks import TaskStore
from a2a.server.routes import (
    add_a2a_routes_to_fastapi, create_agent_card_routes,
    create_jsonrpc_routes, create_rest_routes,
)

class LcAgentExecutor(AgentExecutor):
    """把 engine.chat() 翻译成 A2A 事件流。难点在 event 与 checkpoint/interrupt 对齐。"""
    def __init__(self, engine): self._engine = engine
    async def execute(self, context, event_queue):
        # 1. 读 context 的输入 message 与 task/context id
        # 2. 映射到 lc-agent：task id ~ thread；context id ~ session
        # 3. 发 TASK_STATE_WORKING → 跑 engine.chat()（或 chat_stream）
        # 4. 把文本增量发 artifactUpdate / 终态消息；HITL 中断发 INPUT_REQUIRED 后 return
        # 5. 结束发 TASK_STATE_COMPLETED
    async def cancel(self, context, event_queue):
        # 调 engine 对应 cancel → 发 TASK_STATE_CANCELED
        ...

def mount_a2a(app, engine, *, card, rpc_url="/"):
    executor = LcAgentExecutor(engine)
    handler = DefaultRequestHandlerV2(
        agent_executor=executor, task_store=TaskStore(), agent_card=card)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url=rpc_url),
        rest_routes=create_rest_routes(handler),
    )
```

接线本身不到 30 行。**真正的工作量在 `execute()` 内部的事件语义对齐**（见 §11.4），不在协议层。

### 11.4 适配器里要做的事（决定 `execute()` 怎么写）

| # | 事项 | 说明 |
|---|---|---|
| 1 | **Task/context id ↔ thread/session** | SDK 的任务持久化用 `TaskStore`；lc-agent 侧决定是否把 A2A task id 直接当 `thread_id` 复用现有 checkpoint，还是独立维护一份映射。**建议先独立**（A2A task 生命周期 ≠ lc-agent 会话生命周期，避免污染现有会话模型） |
| 2 | **文本流 → artifactUpdate/statusUpdate** | 把 `engine.chat_stream()` 的增量包成 `StreamResponse` 事件帧（对照 §7） |
| 3 | **HITL/AskUser → INPUT_REQUIRED** | lc-agent 已有 interrupt 检测，把它翻译成发 `INPUT_REQUIRED` 状态 + return，等框架再调 execute |
| 4 | **文件产物 → Artifact** | 工具产生的 diff / `file_changes` 可发布为 `TaskArtifactUpdateEvent`（对照 §3.6） |
| 5 | **取消 → 发 CANCELED** | `engine` 若有正在跑的任务，调其 cancel 再发终态 |
| 6 | **tool-call 过程** | A2A 协议本身**没有**"工具调用过程"这一层的流式事件，只有 Message/Artifact。想在外部 agent 侧展示过程，需把中间 tool 信息塞进 artifact 文本或扩展字段 |

### 11.5 需要注意 / 决策点

- **`a2a-sdk[fastapi]` 额外依赖**：`add_a2a_routes_to_fastapi` 需要 fastapi 才能导入（SDK 里是惰性 import，装 core 也可，跑路由前需装 fastapi）。lc-agent 本身用 FastAPI，无额外负担。
- **版本协商**：SDK 的 `require_version_header=True` 已处理 `A2A-Version` 头校验（对照 §0.3），无需手写。
- **方法名规范化（§9.4）**：用 SDK 后该方法名兼容由官方 dispatcher 处理，不必自己再写一层变体匹配。
- **push notification / GetExtendedAgentCard**：SDK 已实现，是否对外暴露由 Agent Card 的 `capabilities` 声明控制（§6.3）。默认关即可。
- **langgraph 对齐**：官方 SDK 已封装完整 server，比 LangSmith Agent Server 的 A2A 更通用、无 LangGraph 绑定——lc-agent 用它即可，不必再翻 langgraph 的 A2A。

### 11.6 最小可行接入（MVP 边界）

1. 实现 `LcAgentExecutor.execute` 的**同步最小版**：读输入 → 发 WORKING → `engine.chat()` → 发 COMPLETED
2. Agent Card 声明 `streaming:true`、`pushNotifications:false`
3. 挂上 `/a2a` JSON-RPC + `/.well-known/agent-card.json`（SDK 一条命令完成）
4. 用官方 SDK 的 client 或 `curl` 发一条 `SendMessage` 验证闭环
5. 再迭代：流式 → HITL(INPUT_REQUIRED) → CancelTask → 工具 Artifact

---

## 附：验证标准是否走样

写代码时自检：

- [ ] JSON-RPC `method` 是 PascalCase（`SendMessage`），不是 `message/send`
- [ ] JSON 字段 camelCase（`contextId` 不是 `context_id`）
- [ ] 枚举是大写字符串（`"TASK_STATE_WORKING"` 不是小写）
- [ ] 每个响应带 `"jsonrpc":"2.0"` 和正确 `id`
- [ ] 错误对象 `{code, message}`，code 用上表
- [ ] `SendMessage` 的 `returnImmediately=false` 时会等到终态/中断态
- [ ] 流事件是 `StreamResponse` 四选一（task/message/statusUpdate/artifactUpdate）
- [ ] Agent Card 在 `/.well-known/agent-card.json` 可达，`protocolBinding` 为 `JSONRPC`
