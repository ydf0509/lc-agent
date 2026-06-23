# Chat 气泡 HTTP 摘要查看设计文档

> 日期: 2026-06-22
> 状态: 已确认待规划
> 分支: `feat/chat-bubble-http-summary`

## 1. 概述

为聊天界面的每轮对话增加“上游模型 HTTP 摘要查看”能力，让用户可以直接在消息气泡旁查看该轮真实发生的上游模型请求/响应摘要。

本功能聚焦于**后端 ↔ 上游模型服务**这一层的 HTTP 通信，不展示前端 ↔ 本项目后端 API 的请求。

### 已确认需求

- 展示层级：后端 ↔ 上游模型服务
- 展示风格：HTTP 摘要版，不做原始报文样式
- 入口方案：A1（在现有复制按钮旁直接增加按钮）
- 按钮区分：显式区分“请求 HTTP”与“响应 HTTP”
- 轮次归属：同一轮 user + assistant 共享同一组 HTTP 记录
- 多次调用：展示全部，按时间顺序列出
- 浮层形态：popover 小浮层
- 按钮显示条件：仅在该轮实际采集到 HTTP 记录时显示
- 脱敏要求：默认脱敏敏感 header/body 字段
- 首版范围：仅覆盖 OpenAI-compatible 模型调用链

## 2. 用户体验设计

### 2.1 按钮布局

按钮放置在现有 `MessageToolbar` 中，与复制按钮并列：

- user 气泡：
  - `📋 复制`
  - `🌐 请求 HTTP`
- assistant 气泡：
  - `📋 复制全部`
  - `💭 复制思考`
  - `🔧 复制工具`
  - `📝 复制回答`
  - `🌐 响应 HTTP`

不使用模糊的统一 `HTTP` 文案，避免请求/响应语义不清。

### 2.2 弹层行为

点击按钮后打开 popover 小浮层：

- user 气泡按钮打开“请求 HTTP”视图
- assistant 气泡按钮打开“响应 HTTP”视图
- 浮层内容按时间顺序展示该轮全部上游 HTTP 调用

在移动端仍复用同一个按钮入口，但允许实现上将浮层做得更宽、更高，以保证长 body 的可读性。

### 2.3 请求视图内容

user 气泡中的 `请求 HTTP` 浮层展示每次调用的请求摘要卡片：

- 第 N 次调用
- Method
- URL
- 发起时间
- Request Headers（折叠区）
- Request Body（折叠区）

### 2.4 响应视图内容

assistant 气泡中的 `响应 HTTP` 浮层展示每次调用的响应摘要卡片：

- 第 N 次响应
- Status Code
- URL
- 耗时
- Response Headers（折叠区）
- Response Body（折叠区）
- Error（若存在）

### 2.5 文本与可读性规则

- headers / body 使用代码块样式
- JSON 尽量 pretty print
- 超长 body 限制最大高度，内部滚动
- body 为空时显示 `空`
- 字段未采集时显示 `未采集`
- 响应缺失时显示 `未返回`
- 请求失败时显示 `请求失败`

### 2.6 首版不包含的交互

首版**不新增**“复制 HTTP 摘要”按钮，避免 MessageToolbar 进一步拥挤。首版目标先聚焦“查看”，后续若需要再补充“复制 HTTP”能力。

## 3. 轮次与数据归属设计

### 3.1 一轮的定义

一轮 = 一条 user 消息 + 紧随其后对应的 assistant 响应。

若这一轮内部发生多次上游 HTTP 调用，则全部归属于该轮。

### 3.2 共享规则

同一轮中的 user 与 assistant 共享同一组 `http_traces`：

- user 气泡里的 `请求 HTTP` 展示这轮全部 request 列表
- assistant 气泡里的 `响应 HTTP` 展示这轮全部 response 列表

### 3.3 存储归属策略

后端/数据库只在 assistant 消息上持久化 `http_traces`。

原因：

- 一轮 traces 通常在 assistant 执行完成后才完整收集到
- 避免 user / assistant 双份存储重复数据
- 前端可在 `ChatView` 的 bubbleList 派生阶段，把 assistant 的 traces 映射回本轮 user 气泡

### 3.4 按钮显示条件

只有当该轮实际采集到了 HTTP 记录时，才显示：

- user 气泡上的 `请求 HTTP`
- assistant 气泡上的 `响应 HTTP`

若旧历史消息没有 `http_traces`，则正常显示消息内容，但不显示这些按钮。

## 4. 数据模型设计

### 4.1 HttpTrace 结构

建议新增一个统一结构 `HttpTrace`，用于表示一次上游 HTTP 调用：

```ts
interface HttpTrace {
  id: string
  sequence: number
  kind: 'llm_http'
  provider?: string
  model?: string
  startedAt: number
  durationMs?: number
  request: {
    method?: string
    url?: string
    headers?: Record<string, string>
    body?: string
    bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
  }
  response: {
    status?: number
    headers?: Record<string, string>
    body?: string
    bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
    ok?: boolean
  }
  error?: string
}
```

### 4.2 脱敏策略

持久化与前端展示的数据应为**脱敏后版本**，不保存明文敏感值。

默认脱敏字段包括但不限于：

- `authorization`
- `api-key`
- `x-api-key`
- `cookie`
- `set-cookie`
- body 中明显的 `api_key` / `token` / `password` / `secret`

示例：

- `Authorization: Bearer ***`
- `api_key: ***`

### 4.3 前端派生字段

在前端消息视图层派生：

- `httpTraces?: HttpTrace[]`
- `hasHttpRequest?: boolean`
- `hasHttpResponse?: boolean`

用于控制按钮显隐与 popover 内容。

## 5. 后端采集方案

### 5.1 总体策略

必须采集**真实 HTTP 摘要**，不能仅从 LangChain 事件拼“伪 HTTP”。

原因：

- `astream_events` 默认不提供完整 request/response headers/body
- 若只基于消息输入输出和 metadata 拼装，会缺失状态码、真实 headers、原始 body 等关键字段
- 用户明确要看“原始 HTTP 协议的完整请求和响应”的摘要版

因此首版采用：

- 在模型实际发起上游 HTTP 请求的客户端层做 tracing
- 收集真实 request / response 摘要
- 与当前聊天轮次绑定

### 5.2 首版覆盖范围

首版只覆盖 **OpenAI-compatible 模型调用链**。

理由：

- 当前项目最明确可控的模型路径是 `ChatOpenAIReasoning` / OpenAI-compatible 路径
- 可以较低成本拿到真实请求/响应摘要
- 避免为了首版覆盖所有 provider 而引入过大实现复杂度

首版明确**不覆盖**：

- MCP HTTP 通信
- 工具自身对外 HTTP 调用
- 其他尚未接入 tracing 的 provider SDK 路径

### 5.3 轮次级 trace collector

每轮聊天创建一个 trace collector：

1. user 发送消息时初始化 collector
2. 模型每发出一次 HTTP 请求，就 append 一条 `HttpTrace`
3. assistant 完成时，从 collector 取出全部 traces
4. 将 traces 持久化到本轮 assistant 消息
5. 必要时同步回传给前端实时状态 / history

### 5.4 流式响应规则

一次上游流式 HTTP 请求视为一条 trace，不按 chunk 拆分。

- request 保留发起参数摘要
- response body 保存聚合后的最终文本摘要
- durationMs 记录整体耗时

### 5.5 错误请求规则

若请求失败、超时或上游异常：

- 仍保留该条 trace
- request 信息正常保留
- response 可为空或不完整
- `error` 填写错误摘要

这样 assistant 侧仍可展示失败响应记录，而不是完全丢失上下文。

## 6. 前端组件与页面设计

### 6.1 `MessageToolbar.vue`

职责：

- 继续负责复制按钮
- 增加 `请求 HTTP` / `响应 HTTP` 按钮入口
- 控制 popover 打开关闭
- 不承担大段 HTTP 内容渲染逻辑

### 6.2 新增 `HttpTracePopover.vue`

建议新增专用组件，例如：

- `frontend/src/components/chat/HttpTracePopover.vue`

职责：

- 接收 `httpTraces`
- 根据 `mode: 'request' | 'response'` 渲染不同摘要内容
- 处理 pretty print、空值文案、长内容滚动、badge 显示

避免把复杂渲染逻辑全部塞进 `MessageToolbar.vue`。

### 6.3 `ChatView.vue`

职责：

- 在 bubbleList 计算阶段做“同轮 traces 映射”
- assistant 消息直接读取自己的 `httpTraces`
- user 消息读取本轮对应 assistant 的 `httpTraces`
- 派生 `hasHttpRequest` / `hasHttpResponse`
- 传给 `MessageToolbar`

## 7. 后端/前端改动文件范围

### 7.1 后端

预期涉及：

- `lc_agent/core/chat_model.py`
- `lc_agent/core/engine.py`
- `lc_agent/server/websocket.py`
- `lc_agent/server/routes/sessions.py`
- `lc_agent/db/models.py`
- `lc_agent/db/repository.py`

### 7.2 前端

预期涉及：

- `frontend/src/stores/chat.ts`
- `frontend/src/views/ChatView.vue`
- `frontend/src/components/chat/MessageToolbar.vue`
- `frontend/src/components/chat/HttpTracePopover.vue`（新增）

## 8. 测试范围

### 8.1 后端

- assistant 消息可保存 `http_traces`
- session history 能返回 `http_traces`
- 无 traces 时不报错
- 失败请求也能保留 trace
- 多次调用顺序正确
- 流式调用聚合为单条 trace

### 8.2 前端

- user 气泡仅在有 traces 时显示 `请求 HTTP`
- assistant 气泡仅在有 traces 时显示 `响应 HTTP`
- popover 正确区分 request / response 视图
- 多次调用按时间顺序展示
- JSON body 格式化显示
- 长 body 可滚动
- 缺字段时文案正确

## 9. 不做事项

首版明确不做：

- 原始 HTTP 报文视图（`HTTP/1.1` 样式）
- MCP / 工具外部 HTTP 追踪
- 所有 provider 的一口气全覆盖
- 额外的“复制 HTTP 摘要”功能
- 对旧历史消息补采集/补迁移

## 10. 结论

本设计在现有聊天复制按钮基础上，新增“请求 HTTP / 响应 HTTP”两类 popover 入口，依赖后端真实采集 OpenAI-compatible 模型调用链的 HTTP 摘要，并将同一轮 traces 统一存储在 assistant 消息上，由前端在视图层映射给 user / assistant 两侧使用。

该设计能满足：

- 语义清晰地区分请求与响应
- 展示一轮内全部上游调用
- 支持历史回放
- 对敏感信息默认脱敏
- 在项目当前早期阶段控制实现范围，避免过度扩张
