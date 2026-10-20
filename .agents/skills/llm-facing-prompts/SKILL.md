---
name: llm-facing-prompts
description: >-
  编写 lc-agent 中任何面向 LLM 的提示文本时必须遵循的规范，
  包括工具的 docstring、参数 Annotation、description 字段、系统提示词等。
  触发场景：编写或修改工具描述、系统提示、Agent 配置提示词时使用。
---

# lc-agent 面向 LLM 的提示文本规范

**lc-agent的系统提示词，工具描述，工具入参描述，针对的都是llm，不是人类。**

## 不要把用户指导校正你怎么写代码的内心交流，直接此地无银三百两解释写到lc-agent的提示词工程里面
例如用户是指导你纠正你怎么修改代码本身，你不要弄错了角色定位，直接写到lc-agent的提示词工程里面。

## 工具 description、函数入参的 Annotated 描述、系统提示词，均禁止出现框架内部实现词汇

因为：LLM 根本不知道用户在使用 lc-agent，更不知道框架细节。LLM 只有 messages 数组和 function schema（含工具描述和参数描述）。这三类文本全部面向 LLM，各自有明确目的：

- **工具 description / docstring** — 告知 LLM 什么情况下需要调用该工具
- **函数入参的 Annotated 描述** — 解释参数的含义，帮助 LLM 传递正确合适的入参
- **系统提示词** — 设定 LLM 的角色定位、能力范围和行为准则

框架内部的执行机制（LangGraph、interrupt、checkpoint 等）对以上三类目的毫无帮助，写进去只是噪声。

```python
# 错误：把框架执行机制（暂停/阻塞）写进了 docstring，LLM 不关心这些
@tool(name="ask_user")
def ask_user(...) -> str:
    """向用户提问并阻塞等待回答。调用后当前执行将暂停，用户提交答案后自动继续。"""

# 正确：描述触发时机——什么情况下该调用此工具
@tool(name="ask_user")
def ask_user(...) -> str:
    """向用户提问并获取回答。当关键信息缺失且无法从上下文推断时调用，或需用户确认不可逆操作时调用。"""
```

**禁止词**：LangGraph、interrupt、checkpoint、lc-agent、AgentState、engine、middleware 等框架词汇。

## 工具描述的核心目的
**重要：** 工具描述的最核心目的是让 LLM 能知道**什么情况下该调用此工具**（触发时机），其次才是说明功能细节。触发时机让 LLM 决定要不要调用，功能描述帮助理解但不足以让 LLM 判断调用时机。

---

## 工具 docstring / description 如何写

工具的 `docstring`（函数文档字符串）或 `@tool(description=...)` 字段是工具描述的载体，这些文字会直接传递给调用该工具的 LLM。描述内容和详细程度按工具实际需要来定，没有固定模板。以下以 deepagents 实际代码为风格参考：

**简单工具** — 首句说清做什么，必要时加约束或示例，无需分节：

```python
# deepagents glob 工具的 description
"""Find files matching a glob pattern.

Supports standard glob patterns: `*` (any characters), `**` (any directories), `?` (single character).
Returns a list of absolute file paths that match the pattern.

Examples:
- `**/*.py` - Find all Python files
- `*.txt` - Find all text files"""
```

**复杂工具** — 有易错点、多种使用模式时，用 `Usage:` 分节详述：

```python
# deepagents read_file 工具的 description（节选）
"""Reads a file from the filesystem.

Usage:
- By default, it reads up to 100 lines starting from the beginning of the file
- **IMPORTANT for large files and codebase exploration**: Use pagination with offset and limit
    - First scan: read_file(file_path="...", limit=100)
    - Read more sections: read_file(file_path="...", offset=100, limit=200)
- You should ALWAYS make sure a file has been read before editing it."""
```

**参数的 `Annotated` 描述**（lc-agent 项目的实际写法）— 说明「怎么填」；有格式要求时给具体示例：

```python
# lc-agent 工具参数的写法（来自 ask_user_tool.py）
question: Annotated[
    str,
    (
        "向用户展示的问题文本。应清晰简洁，直接表达你需要用户提供的信息或做出的决定。"
        "示例：'您希望报告覆盖哪个时间段？' / '确认要删除这条记录吗？'"
    ),
]
```

**lc-agent 完整工具参考**：读 `lc_agent/tools/contrib_tools/get_time.py`，它展示了 `@tool(description=...)` 写法和 `Annotated` 参数描述的标准组合，是典型的简单工具范例。
介绍工具何时调用、工具用途、工具参数的含义。

---

## 系统提示词写法

参考 deepagents Anthropic 风格，用 XML 标签组织行为准则：

```
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between the tool calls,
make all of the independent tool calls in parallel. Prioritize calling tools simultaneously
whenever the actions can be done in parallel rather than sequentially.
</use_parallel_tool_calls>

<investigate_before_answering>
Never speculate about code you have not opened. If the user references a specific file, you
MUST read the file before answering. Make sure to investigate relevant files BEFORE answering.
</investigate_before_answering>

<tool_result_reflection>
After receiving tool results, carefully reflect on their quality and determine optimal next steps
before proceeding.
</tool_result_reflection>
```

只描述 Agent 的角色、能力、行为准则，用 XML 标签分块便于模型解析。

使用xml标签和空行，能让llm更能无幻觉掌握某段提示词的边界

不要用普通的\n换行来拼接多个意义作用域的段落，而要使用xml标签分隔。