"""
lc-agent 内置 Agent 行为提示词
================================

这些提示词描述 AI 在使用 lc-agent 工具时应遵循的行为约束，
适用于任何使用 lc-agent 工具集的项目（不限于编程类）。

每个常量对应一个工具组，由引擎根据 preset.allowed_tool_groups 动态决定是否注入。
TOOL_GROUP_GUIDELINES 字典是引擎注入的入口，新增工具组只需在此字典中追加即可。
"""

# ---------------------------------------------------------------------------
# file_read 工具组 —— 文件读取 & 搜索规范
# ---------------------------------------------------------------------------
FILE_READ_USAGE_PROMPT = """\
<file_read_rules>
## 文件读取与搜索规范

### 读取文件
- 修改文件前必须先用 `read_file` 读取其当前内容；禁止凭记忆直接写入
- 需要同时读取多个已知路径时，用 `read_multiple_files` 批量读取，而不是逐个调用 `read_file`
- 只需知道文件元数据（大小、行数等）时，用 `get_file_info` 而不是读取全文
- 需要读取大文件的局部内容时，使用 `read_file` 的 `offset`/`length` 参数指定行范围

### 搜索代码与目录
- 查找函数、类名、字符串内容时，用 `search_files` 并指定 `search_type='content'`；
  只需按文件名查找时，指定 `search_type='files'`
- 需要列出目录结构时使用 `list_directory`
- 禁止用 `run_command` 的 `cat`/`type`/`head`/`dir`/`ls` 等命令间接读文件或列目录
</file_read_rules>"""

# ---------------------------------------------------------------------------
# file_write 工具组 —— 文件写入 & 修改规范
# ---------------------------------------------------------------------------
FILE_WRITE_USAGE_PROMPT = """\
<file_write_rules>
## 文件写入与修改规范

- 编辑文件前必须先用 `read_file` 读取其当前内容，禁止凭记忆直接写入
- 优先使用 `edit_block` 对文件进行精确的字符串替换，而不是整体重写
- 整体重写时使用 `write_file`；确保内容完整，不截断

</file_write_rules>"""

# ---------------------------------------------------------------------------
# command 工具组 —— 命令执行规范
# ---------------------------------------------------------------------------
COMMAND_USAGE_PROMPT = """\
<command_rules>
## 命令执行规范

- `run_command` 在 Windows 上使用 PowerShell，在 Linux/macOS 上使用 $SHELL，执行命令行前先看 project_context 的 OS 行，严禁在 Windows 上执行 Linux 命令
- **Windows PowerShell (5.1) 不支持 `&&` 链接命令**；需要顺序执行且依赖前一步成功时，
  使用 `cmd1; if ($?) { cmd2 }` 的 PowerShell 写法
- 运行可能挂起或耗时很长的命令（如服务器、监控进程）时，使用 `start_background_process`；
  启动后台进程后，用 `read_process_output` 读取其输出，用 `list_agent_started_processes` 查看已启动的进程
- 运行需要超时终止的命令时，使用 `run_command` 的 `max_run_ms` 参数
- 杀掉进程使用 `kill_process`；仅想查看 agent 启动的后台进程，使用 `list_agent_started_processes`；
  想查看系统全部进程，使用 `list_all_processes`
</command_rules>"""

# ---------------------------------------------------------------------------
# 声明式映射：group_id → prompt（引擎根据此字典按需注入）
# 新增工具组时，只需在此字典追加，无需修改 engine.py
# ---------------------------------------------------------------------------
TOOL_GROUP_GUIDELINES: dict[str, str] = {
    "file_read": FILE_READ_USAGE_PROMPT,
    "file_write": FILE_WRITE_USAGE_PROMPT,
    "command": COMMAND_USAGE_PROMPT,
}

# ---------------------------------------------------------------------------
# 注释约束（供有需要的 Preset 在 system_prompt 中手动引用）
# ---------------------------------------------------------------------------
_COMMENT_DISCIPLINE = """\
## 注释约束

- **不写废话注释**：禁止写只是复述代码功能的注释（如 "# 读取文件"、"# 返回结果"）；
  注释只用于解释非显然的意图、权衡取舍或外部约束
- **不解释改动**：不在注释里描述"你做了什么改动"，只描述代码的"为什么"
"""

# ---------------------------------------------------------------------------
# 组合常量（全量，可在编程类 Preset 的 system_prompt 中手动引用）
# ---------------------------------------------------------------------------
AGENT_GUIDELINES_PROMPT = f"""\
{FILE_READ_USAGE_PROMPT}

{FILE_WRITE_USAGE_PROMPT}

{COMMAND_USAGE_PROMPT}

{_COMMENT_DISCIPLINE}"""
