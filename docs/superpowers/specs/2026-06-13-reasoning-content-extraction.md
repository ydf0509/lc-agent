# Reasoning Content Extraction — 设计文档

## 问题

通过 litellm 代理访问多个 AI 供应商时，部分模型（DeepSeek、GLM 等）在流式响应的 delta 中返回 `reasoning_content` 字段，用于展示模型的推理/思考过程。但 `langchain_openai.ChatOpenAI` 只遵循官方 OpenAI API 规范，**不提取**这个非标准字段。

## 影响范围

| 模型 | 后端 | 返回 `reasoning_content` | 旧代码（ChatOpenAI）| 修复后 |
|------|------|:---:|:---:|:---:|
| `ds-deepseek-v4-flash` | DeepSeek 官方 | 始终 | 丢失 | 提取 |
| `ark-deepseek-v4-flash` | 字节方舟 Coding Plan | 始终 | 丢失 | 提取 |
| `ark-glm-5.1` | 字节方舟 Coding Plan | 复杂/工具任务时 | 丢失 | 提取 |
| 其他模型 | 各种 | 取决于供应商 | 丢失 | 提取 |

## 根因分析

```
API Response (litellm proxy)
  → delta: { "reasoning_content": "...", "content": "..." }
  
ChatOpenAI._convert_delta_to_message_chunk()  ← 只提取 content/tool_calls
  → chunk.additional_kwargs = {}  ← reasoning_content 丢失！

WebSocket._send_event()
  → (getattr(chunk, "additional_kwargs") or {}).get("reasoning_content")
  → None  ← 前端收不到思考内容
```

## 解决方案：ChatOpenAIReasoning

创建 `ChatOpenAI` 的子类，覆写 `_convert_chunk_to_generation_chunk` 方法，从 streaming delta 中提取 `reasoning_content` / `reasoning` 字段。

### 设计原则

1. **不绑定供应商** — 不 import `langchain_deepseek`、`langchain_glm` 等
2. **通用提取** — 任何返回 `reasoning_content` 的模型自动生效
3. **向前兼容** — 新供应商加入时无需改代码
4. **Drop-in 替换** — `ChatOpenAI` 子类，完全兼容

### 核心代码

```python
# lc_agent/core/chat_model.py

class ChatOpenAIReasoning(ChatOpenAI):
    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):
        generation_chunk = super()._convert_chunk_to_generation_chunk(...)
        
        # 从原始 delta dict 中提取 reasoning_content
        choices = chunk.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            reasoning = delta.get("reasoning_content") or delta.get("reasoning")
            if reasoning is not None:
                generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning
        
        return generation_chunk
```

### 数据流（修复后）

```
API Response → delta: { "reasoning_content": "thinking...", "content": "answer" }
  ↓
ChatOpenAIReasoning._convert_chunk_to_generation_chunk()
  → chunk.additional_kwargs["reasoning_content"] = "thinking..."
  ↓
WebSocket._send_event()
  → {"type": "thinking", "content": "thinking..."}  ← 前端收到！
  → {"type": "token", "content": "answer"}
```

## 测试验证

- 单元测试 94 个全部通过
- 联网集成测试（`tests_my/ai_tests/`）验证三个模型的实际行为
- 前端 UI 确认思考过程正确显示

## 关于 GLM-5.1 Thinking 模式

### 发现

| 端点 | thinking=enabled 参数 | 返回 `reasoning_content` |
|------|:---:|:---:|
| 智谱官方 (`open.bigmodel.cn`) | 支持 | 有 |
| 字节方舟 Coding Plan (`ark.cn-beijing.volces.com/api/coding/v3`) | 复杂任务自动触发 | 有（仅复杂/工具任务） |

### 结论

- 方舟 GLM-5.1 在处理简单问题时不返回 reasoning
- 在复杂任务（工具调用、多步推理）时会自动返回 reasoning_content
- `ChatOpenAIReasoning` 在两种情况下都正确处理
