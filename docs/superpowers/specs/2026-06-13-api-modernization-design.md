# LangChain/LangGraph API Modernization Design Spec

## Background

项目当前使用 langchain 1.3.4 + langgraph 1.2.4 生态。经审计，主要的过时 API 已修复（`create_react_agent` → `create_agent`），但仍有以下需要现代化的部分。

## Environment

| Package | Version |
|---------|---------|
| langchain | 1.3.4 |
| langchain-core | 1.4.3 |
| langchain-openai | 1.3.0 |
| langgraph | 1.2.4 |
| langgraph-checkpoint | 4.1.1 |
| langgraph-checkpoint-sqlite | 3.1.0 |

---

## 1. 已修复（本次会话）

| 文件 | 旧 API | 新 API |
|------|--------|--------|
| `lc_agent/core/engine.py` | `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| 同上 | `create_react_agent(..., prompt=...)` | `create_agent(..., system_prompt=...)` |
| docs 多个文件 | 同上引用 | 已全部更新 |

---

## 2. 需要现代化的 API

### 2.1 模型初始化：引入 `init_chat_model`

**当前（可工作但不够灵活）：**
```python
# lc_agent/core/engine.py:133-145
from langchain_openai import ChatOpenAI
return ChatOpenAI(model=model_info.id, base_url=..., api_key=..., temperature=0.7, stream_usage=True)
```

**问题：**
- 硬编码使用 `ChatOpenAI`，不支持 Anthropic、Gemini 等其他提供商
- 项目声明了 `langchain-deepseek` 依赖但从未使用
- 无法利用新的字符串标识符语法如 `"openai:gpt-4o"`

**新方式：**
```python
from langchain.chat_models import init_chat_model
model = init_chat_model("openai:gpt-4o", base_url=..., api_key=..., temperature=0.7)
```

**决策：** 引入 `init_chat_model` 作为模型工厂，但保留对 `ChatOpenAI` 的直接支持作为 fallback。在 config 中增加 `provider_type` 字段以支持多提供商。

### 2.2 HITL 中间件模式

**当前：**
```python
# lc_agent/core/engine.py:120-121
if preset.dangerous_tools:
    kwargs["interrupt_before"] = ["tools"]
```

**分析：** `interrupt_before=["tools"]` 在 `create_agent` 中仍被支持（未废弃）。但新的 `HumanInTheLoopMiddleware` 提供了更细粒度的控制：
- 按工具名过滤（当前实现会中断所有工具调用，然后在 websocket 层判断）
- 更好的错误处理

**决策：** 暂不迁移到 middleware 模式。`interrupt_before` 仍受支持且当前实现工作正常。标记为 future enhancement。

### 2.3 `astream_events` 版本

**当前：** `version="v2"` — 仍受支持

**新增：** `version="v3"` — 实验性，返回 `AsyncGraphRunStream`，支持并发 cursor

**决策：** 保持 v2 直到 v3 稳定。无需变更。

### 2.4 清理未使用依赖

**当前 `pyproject.toml`：**
```toml
"langchain-deepseek",  # 声明但从未 import
```

**决策：** 保留但添加注释说明用途。如果后续添加 DeepSeek 提供商支持（通过 `init_chat_model`），这个依赖会被用到。

### 2.5 `StructuredTool.from_function` → 验证是否有更好方式

**当前：**
```python
# lc_agent/tools/registry.py:99-103
StructuredTool.from_function(func=func, name=name, description=description)

# lc_agent/mcp/tool_adapter.py:70-76
StructuredTool.from_function(func=None, coroutine=_invoke, name=..., description=..., args_schema=...)
```

**分析：** `StructuredTool.from_function` 未被废弃，仍是创建工具的标准方式。`@tool` 装饰器内部也是用它。

**决策：** 无需变更。

---

## 3. 实际需要实施的变更

综合以上分析，本次迁移范围：

### 3.1 引入 `init_chat_model` 支持多提供商（主要变更）

**目标：** 让 `_create_llm` 方法支持通过配置切换不同 LLM 提供商，不再硬编码 `ChatOpenAI`。

**影响文件：**
- `lc_agent/core/engine.py` — `_create_llm` 方法
- `lc_agent/core/models.py` — `ModelInfo` 增加 `provider_type` 字段（可选）
- `config.jsonc` — 文档化新的配置格式

**设计：**
```python
def _create_llm(self, model_info: ModelInfo | None, model_id: str):
    from langchain.chat_models import init_chat_model

    if model_info and model_info.base_url:
        # 有自定义 base_url 的场景（OpenAI 兼容 API）
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_info.id,
            base_url=model_info.base_url,
            api_key=model_info.api_key or "not-set",
            temperature=0.7,
            stream_usage=True,
        )

    # 标准提供商场景：使用 init_chat_model
    provider = model_info.provider if model_info else ""
    model_name = model_info.id if model_info else model_id
    model_str = f"{provider}:{model_name}" if provider else model_name

    kwargs = {"temperature": 0.7, "stream_usage": True}
    if model_info and model_info.api_key:
        kwargs["api_key"] = model_info.api_key

    return init_chat_model(model_str, **kwargs)
```

### 3.2 `stream_usage=True` 一致性

**当前问题：** fallback 路径 `ChatOpenAI(model=model_id, api_key="not-set", stream_usage=True)` 已有 `stream_usage=True`，这是正确的。

**验证：** `init_chat_model` 也支持透传 `stream_usage` 参数。无需额外处理。

### 3.3 文档同步

更新以下文档以反映多提供商支持：
- `docs/superpowers/specs/2026-06-11-lc-agent-project-design.md`
- `docs/superpowers/specs/2026-06-11-phase5-agent-runtime-design.md`
- `README.md`（如果相关）

---

## 4. 不在本次范围

| 项目 | 原因 |
|------|------|
| 迁移到 `HumanInTheLoopMiddleware` | `interrupt_before` 仍受支持，当前方案工作正常 |
| 升级 `astream_events` 到 v3 | v3 实验性，不稳定 |
| 添加 `PostgresSaver` | 不在早期开发阶段需求内 |
| 迁移 `StructuredTool.from_function` | 未废弃 |
| 移除 `langchain-deepseek` 依赖 | 后续多提供商支持会用到 |

---

## 5. 测试策略

- 单元测试：`_create_llm` 的不同配置场景
- 集成测试：`build_agent` 完整流程
- 验证 `init_chat_model` 在有/无 `base_url` 场景下的行为
- 确保现有测试不受影响

## 6. 风险评估

| 风险 | 级别 | 缓解 |
|------|------|------|
| `init_chat_model` 不支持某些 kwargs | 低 | 保留 ChatOpenAI fallback 路径 |
| 字符串解析错误 | 低 | 有明确的 provider:model 格式 |
| 现有测试 mock 失效 | 中 | 先运行现有测试确认基线 |
