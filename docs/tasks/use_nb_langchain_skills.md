# 迁移计划：用 nb_langchain_agentskills 替换 langchain_agentskills

## 目标

1. 把 `langchain-agentskills` 从 lc-agent 的依赖中彻底拿掉，换成自研包 `nb-langchain-agentskills`（本地 `pip install -e`，Phase 1 不发 PyPI）。
2. 前后端、提示词、skill 内容、测试全部对齐新包的接口与工具名，不留 split-brain。
3. 顺手删掉为旧包缺陷打的补丁（`WindowsScriptExecutor`、手补 `args_schema`）。

新包源码与 API 文档：`D:\codes\nb_langchain_agentskills`（工具名、Loader 接口、middleware 参数见其 README）。

---

## 一、依赖面全清单

### 1.1 后端（6 个 import 点）

| 文件 | 位置 | 用了什么 | 处理 |
|---|---|---|---|
| [pyproject.toml](file:///d:/codes/lc-agent/pyproject.toml#L25) | L25 | `langchain-agentskills>=0.4` | 换成 `nb-langchain-agentskills` |
| [app.py](file:///d:/codes/lc-agent/lc_agent/app.py#L10-L11) | L10-11 | `SkillsToolkit`、`CompositeSkillLoader`、`DirectorySkillLoader` | 改用新包 loader；toolkit 概念消失 |
| [app.py](file:///d:/codes/lc-agent/lc_agent/app.py#L105-L113) | L105-113 | 组装 loader → toolkit → 打 Windows 补丁 | 重写：只组装 loader |
| [app.py](file:///d:/codes/lc-agent/lc_agent/app.py#L123-L125) | L123-125 | `app.state.skills_toolkit` / `filtered_loader` / `engine._skills_toolkit` | 改为挂 loader，去掉 toolkit |
| [engine.py](file:///d:/codes/lc-agent/lc_agent/core/engine.py#L344-L356) | L344-356 | `toolkit._resolved_loader`、`set_project_overlay()` | 改为直接持有 loader，overlay 接口按新类设计 |
| [engine.py](file:///d:/codes/lc-agent/lc_agent/core/engine.py#L359-L371) | L359-371 | `_LcAgentSkillMiddleware`、`toolkit._executor` | 改为传 `CommandExecutor` |
| [routes/skills.py](file:///d:/codes/lc-agent/lc_agent/server/routes/skills.py#L6) | L6, L16 | `SkillsToolkit` 类型标注 | 删除该标注 |
| [routes/skills.py](file:///d:/codes/lc-agent/lc_agent/server/routes/skills.py#L87) | L87 | `DirectorySkillLoader`（extra dirs 扫描） | 换新包同名类 |
| [skill_middleware.py](file:///d:/codes/lc-agent/lc_agent/skills/skill_middleware.py#L4) | 整文件 | 继承 `SkillMiddleware` + 手补 `args_schema` + 覆盖 description | 大幅瘦身：新包工具自带 `args_schema`（`extra="forbid"`），补丁整段删除 |
| [filtered_loader.py](file:///d:/codes/lc-agent/lc_agent/skills/filtered_loader.py#L9-L11) | 整文件 | 按旧 Loader 接口实现（`has_skill`/`read_resource`/`read_script`） | 按新 4 方法接口重写 |
| [script_executor.py](file:///d:/codes/lc-agent/lc_agent/skills/script_executor.py) | 整文件 | 旧 `ScriptExecutor` 的 Windows 补丁 | **整文件删除** |
| [routes/agents.py](file:///d:/codes/lc-agent/lc_agent/server/routes/agents.py#L617-L630) | L617-630 | `loader.disabled_skills`、`list_all_skills()` | 这两个方法必须在新 loader 里保留 |

### 1.2 测试

| 文件 | 处理 |
|---|---|
| [test_skill_script_executor.py](file:///d:/codes/lc-agent/tests/test_skill_script_executor.py) | **整文件删除**（全部在测旧包 toolkit 与 Windows 补丁） |
| [test_skills.py](file:///d:/codes/lc-agent/tests/test_skills.py#L61-L71) | `_build_skills_prompt` 断言里的工具名要改；`SkillScanner` 相关用例见决策点 D |
| [test_routes_agents.py](file:///d:/codes/lc-agent/tests/test_routes_agents.py#L245-L304) | 假 loader 的方法签名要与新 `LcAgentSkillLoader` 对齐 |

### 1.3 前端

| 文件 | 位置 | 处理 |
|---|---|---|
| [ToolGenericCard.vue](file:///d:/codes/lc-agent/frontend/src/components/chat/tools/ToolGenericCard.vue#L119) | L119 | 图标判定：`load_skill`/`read_skill_resource`/`run_skill_script` → 加 `skill__` 前缀 + 补 `skill__list_skills` |
| [ToolGenericCard.vue](file:///d:/codes/lc-agent/frontend/src/components/chat/tools/ToolGenericCard.vue#L143-L145) | L143-145 | 中文名映射表 key 改名 |
| [ToolGenericCard.vue](file:///d:/codes/lc-agent/frontend/src/components/chat/tools/ToolGenericCard.vue#L186-L196) | L186-196 | 摘要取参改名：`skill__execute_script` 取 `command`（旧是 `script_name`/`script_args`） |
| [TestSegments.vue](file:///d:/codes/lc-agent/frontend/src/views/TestSegments.vue#L117-L121) | L117-121 | 演示用例的 name/args 改名 |
| [DetailModal.vue](file:///d:/codes/lc-agent/frontend/src/components/panels/DetailModal.vue#L147-L175) | 147-175 | 只用 `path`/`description`/`body`，无需改 |
| [RightPanel.vue](file:///d:/codes/lc-agent/frontend/src/components/layout/RightPanel.vue#L384) | L384 | 用 `skill.source` 当路径显示 → 改 `skill.path`（随决策点 C） |
| [stores/tools.ts](file:///d:/codes/lc-agent/frontend/src/stores/tools.ts#L38-L45) | L38-45 | `Skill` 接口 `source?: string` → `path?: string` |
| `lc_agent/web/dist/` | — | 前端改完必须重新构建 |

`ChatInput.vue` 只用 `name`/`description`/`scope`，不依赖工具名也不依赖 `source`，无需改。

### 1.4 提示词与 skill 内容（LLM 面向文本）

| 文件 | 位置 | 现状 | 处理 |
|---|---|---|---|
| [baidu-search/SKILL.md](file:///d:/codes/lc-agent/lc_agent/skills/contrib_skills/baidu-search/SKILL.md#L18) | L18, L72, L79 | `run_skill_script`、`read_skill_resource` | 改 `skill__execute_script` / `skill__read_content`；调用形式要改成完整命令 |
| [create-skill/validate_skill.py](file:///d:/codes/lc-agent/lc_agent/skills/contrib_skills/create-skill/scripts/validate_skill.py#L103) | L103 | 提示文本提到 `load_skill` | 改 `skill__load_skill` |
| [langchain-middleware/SKILL.md](file:///d:/codes/lc-agent/.agents/skills/langchain-middleware/SKILL.md#L134) | L134 | `SkillsMiddleware` / `langchain_agentskills` / `load_skill 等` | 改新包名与工具名 |

其余 `.agents/skills/*` 与 `contrib_skills/*` 已扫过，无旧工具名残留。但**凡 SKILL.md 里写了"跑脚本"的措辞，都要按新入参（完整 shell 命令）复核**——`skill__execute_script` 不解析 `script_name`。

### 1.5 文档与配置

| 文件 | 处理 |
|---|---|
| [README.md](file:///d:/codes/lc-agent/README.md#L449) | L449 `run_skill_script` → `skill__execute_script` |
| [FEATURES.md](file:///d:/codes/lc-agent/FEATURES.md#L246-L266) | §5 Skills 系统：工具名与"脚本执行"描述按新语义复核；L446 中间件顺序表核对 |
| `D:\codes\lc-agent-bfzs\permissions.jsonc` | 不动（决策点 F：暂不放行 skill 目录） |
| `my_dir/http_req_ex/*.json`、`my_dir/testsmy/提示词抓包1.md` | 抓包样例，含旧包字样的 tool 结果，非生产代码；已按用户决定删除 |
| `langchain-agentskills` 0.4.0（py312 环境） | 代码已不 import；按用户决定暂不卸载 |

---

## 二、新旧接口对照

| 旧（langchain_agentskills） | 新（nb_langchain_agentskills） |
|---|---|
| `SkillLoader.list_skills()` | 同名 |
| `load_skill(name)` → `SkillContent(body, resources, scripts, metadata)` | `load_skill(name)` → `SkillContent(metadata, body, files, root)` |
| `read_resource(skill, resource)` | `read_content(skill, file_path)` |
| `read_script(skill, script)` → `Path` | 无（执行走 `skill__execute_script(command=...)`） |
| `has_skill(name)` | 无（用 `list_skills` 或兜 `SkillNotFoundError`） |
| — | `resolve_root(skill)` → 新增，给真实目录 |
| — | `BlacklistSkillLoader(inner, blocked=None)`：新增黑名单过滤器，`blocked` 按引用持有 |
| `SkillMiddleware` | `SkillsMiddleware(loader, *, executor, exclude_tools, prompt_builder, enable_pythonpath)` |
| `SkillsToolkit(loaders=[...])` | 概念消失，middleware 自带 tools |
| `ScriptExecutor.run(script_path, args, timeout)` | `CommandExecutor.run(command, cwd, timeout_ms, pythonpath_dirs)` |
| `SkillNotFoundError(name)` | 同名，多 `available` 参数 |
| 工具 `load_skill` / `read_skill_resource` / `run_skill_script` | `skill__load_skill` / `skill__read_content` / `skill__execute_script` / `skill__list_skills`（4 个） |
| 多来源 first wins | **last wins**（顺序必须"通用→具体"，传反会静默变成全局覆盖项目） |

---

## 三、实施步骤

### 步骤 1：装包

```
pip install -e D:\codes\nb_langchain_agentskills
```

用 `D:\ProgramData\Miniconda3\envs\py312\python.exe`。改 `pyproject.toml` L25 依赖名。

### 步骤 2：重写 loader 层（只写一个类）

新建 `LcAgentSkillLoader`（放 `lc_agent/skills/filtered_loader.py`，替换现文件），实现新包 `SkillLoader` 的 4 个方法，并保留 lc-agent 需要的扩展方法：

- 新包契约：`list_skills` / `load_skill` / `read_content` / `resolve_root`
- lc-agent 消费方：
  - `disabled_skills`（routes/skills.py、routes/agents.py 直接读写这个 set；同时作为 `BlacklistSkillLoader` 的 `blocked` 按引用传入，改它即改可见性）
  - `list_all_skills()`（含被禁用的，给 UI）
  - `list_global_skills()`（不含 overlay，给 `/api/skills` 的 global scope）
  - `list_overlay_skills()`（routes/skills.py L66 现在直接调私有的 `loader._project_skills()`，提升为公开方法）
  - `set_project_overlay(dirs)`
  - `toggle(name)`

**为什么这层不能省、也不能拆成两个类**：

1. **运行时开关跨层一致**：`disabled_skills` 必须同时作用于 `load_skill` / `read_content` / `resolve_root`，只挡 `list_skills` 是"列表看不见但能加载"的假过滤。这一层交给新包 `BlacklistSkillLoader`（4 个方法全校验），不在 lc-agent 重复实现。
2. **overlay 是每请求动态的**。`set_project_overlay` 在 engine 构建 agent 时按 preset 调用；而 `CompositeSkillLoader([a, b])` 是构造期固定列表。靠重建 composite 实现会连 `DirectorySkillLoader` 的 TTL 扫描缓存一起丢掉，变成每请求扫盘。这里必须持有持久 loader 实例、只换组合（overlay 目录按 dirs 元组缓存对应 loader 实例，重复 preset 不重扫）。
3. **UI 报表是前端口径**（含禁用项、global 不含 overlay），不是 agent 可见性，不属于新包职责。

所以：**不拆两个类**。`LcAgentSkillLoader` 只做薄壳：4 个方法转发给黑名单层，另提供 UI 报表与 `toggle()`。黑名单直接用新包 `BlacklistSkillLoader(inner, blocked=disabled_skills)`（`blocked` 按引用持有，`toggle()` 原地增删即刻生效）；白名单场景（per-preset allowed）另用 `AllowedSkillLoader` 包在最外层，三值语义：`None` 不包、`[]` 表示 `allowed=set()`（全禁），别把 `[]` 写成 `None`。

overlay 与 global 的合并顺序：`[global, overlay]`，靠新包的 last wins 实现"项目覆盖全局"。

### 步骤 3：middleware 层

`_LcAgentSkillMiddleware` 瘦身为 `SkillsMiddleware` 的薄子类：

- 构造时传 `loader`、`prompt_builder=_build_skills_prompt`、`executor=CommandExecutor()`、`exclude_tools={"skill__list_skills"}`（决策点 A）。
- **删除**：`_SKILL_TOOL_ARGS_SCHEMAS`、`_SKILL_TOOL_DESCRIPTIONS`、`original_tools` 循环改写（新包工具自带 schema 与面向 LLM 的 description）。
- 保留 `has_visible_skills`（新包已有同名 property）。
- 重写 `_build_skills_prompt`：工具名换新；`/` 斜杠命令段保留（lc-agent 特有）；JSON 清单格式保留。

### 步骤 4：接线 app / engine / routes

- `app.py`：删 toolkit 与 Windows 补丁调用；组装 `LcAgentSkillLoader` → 挂到 `app.state.skills_loader` 与 `engine._skills_loader`。`app.state.filtered_loader` 这个名字一并改掉：toolkit 概念消失、过滤已分两层，`filtered` 是最不准的命名；这些代码本来就要改，改名零额外成本。
- `engine.py`：`set_project_overlay` 改为新 loader 的同名方法；middleware 构造传 loader + `CommandExecutor`。
- `routes/skills.py`：
  - `_resolve_skill_path()` 这个"扫目录找 SKILL.md"的 hack 换成 `loader.resolve_root(name)`。
  - 列表响应：`path` 填 `resolve_root()` 的真实目录，删掉 `source` 字段（决策点 C）。
  - `GET /skills/{name}`：返回值换成 `body` + `files` + `root`，删掉 `resources` / `scripts`（决策点 B）。
  - `scope` 判定改为拿 `resolve_root` 与 global/project/extra 目录比对得出。
- `routes/agents.py`：`loader.list_all_skills()` / `disabled_skills` 保持可用。

### 步骤 5：删文件

- 删 `lc_agent/skills/script_executor.py`
- 删 `tests/test_skill_script_executor.py`
- 删 `app.py` 里对应 import 与调用
- 删 `lc_agent/skills/scanner.py`、清空 `skills/__init__.py` 导出、删 `test_skills.py` 里 4 个 `SkillScanner` 用例（决策点 D）

### 步骤 6：skill 正文与文档

按 1.4 / 1.5 表逐条改。**重点复核每个 SKILL.md 里描述脚本执行的部分**：新工具只接受完整 shell 命令字符串，这是调用形式的变化而非改名，改错会让 agent 反复失败。改完实跑一个 skill 验证。

（框架注入的系统提示 `_build_skills_prompt` 不在这里——它和 middleware 同文件，已在步骤 3 一起改，否则提示词会指向尚不存在的工具名。）

### 步骤 7：前端

按 1.3 表改名工具名与取参逻辑，然后重新构建前端产物。

### 步骤 8：测试

- 改 `test_skills.py` / `test_routes_agents.py` 对齐新接口
- 补一条 lc-agent 侧的端到端冒烟：`create_agent` + `SkillsMiddleware` → 触发 `skill__load_skill`（新包 `tests/test_e2e.py` 已有可参考写法）
- 跑全量 `pytest`

---

## 四、决策点

### 已定案

**A. 工具集**
middleware 构造时传 `exclude_tools={"skill__list_skills"}`，只注册 3 个工具，与迁移前一致。清单靠 prompt 注入。

**B. `/api/skills/{name}` 返回字段**
换成 `body` + `files`（扁平相对路径列表）+ `root`；删掉 `resources` / `scripts` 两个字段。

**C. `source` 字段**
`path` 用 `loader.resolve_root(name)` 填 skill 根目录绝对路径；API 响应删掉 `source` 字段。前端 `RightPanel.vue` / `stores/tools.ts` 同步改用 `path`。

**D. `lc_agent/skills/scanner.py`**
删除。它只被 `tests/test_skills.py` 引用，能力被新包 `DirectorySkillLoader` 完全覆盖。一起清掉 `skills/__init__.py` 的导出与 `test_skills.py` 里 4 个 `SkillScanner` 用例。

**E. `skill__execute_script` 默认超时与 `enable_pythonpath`**
保持新包默认：180s（2026-09-24 由 30s 调整）、PYTHONPATH 注入 skill 根与 `scripts/`。

**F. skill 目录写权限**
暂不放行，`permissions.jsonc` 不动。agent 能拿到 skill 真实路径但不能用 `file_write` 改其中的文件，与迁移前一致；后续需要再开。

**G. 命名**
`app.state.filtered_loader` → `app.state.skills_loader`（engine 侧 `_skills_loader`）。toolkit 概念消失、过滤已交给新包的 `BlacklistSkillLoader` / `AllowedSkillLoader` 两层过滤器，`filtered` 是最不准的叫法。

**H. 实施顺序**
后端代码（loader → middleware 含系统提示 → 接线 → 删旧文件）→ skill 正文与文档 → 前端重建 → 全量测试。
理由：系统提示与 middleware 同文件必须同改，先改提示词会让 agent 指向不存在的工具名；skill 正文的改动是调用形式变化，代码就位后单独一轮并实跑验证。

**I. 黑名单层**
`disabled_skills` 的过滤改用新包 `BlacklistSkillLoader`（本包 v0.2.0 新增），不在 lc-agent 重复实现；`blocked` 与 lc-agent 的 `disabled_skills` 共享同一个 set 对象，`toggle()` 就地生效。

---

## 五、验收清单

- [x] 全仓 `grep langchain_agentskills` 只剩本计划文档的说明文字
- [x] `pyproject.toml` 无 `langchain-agentskills`
- [x] 后端不再有 `SkillsToolkit` / `ScriptExecutor` / `WindowsScriptExecutor` 引用
- [x] `/api/skills` 列表的 `path` 是真实目录、无 `source` 字段；`/api/skills/{name}` 返回 `body`/`files`/`root`、无 `resources`/`scripts`
- [x] 前端 `stores/tools.ts` 的 `Skill` 类型与 `RightPanel.vue` 的路径显示已改用 `path`
- [x] middleware 只注册 3 个工具（`skill__list_skills` 已 exclude）
- [x] 被禁用的 skill 在 load / read / resolve 三条链路上都拿不到（不只在列表里消失）
- [x] 前端工具名映射与真实工具名逐一核对（3 个）
- [x] 所有 SKILL.md 里提到的工具名与调用形式与新入参一致
- [x] `pytest` 全绿（480 passed）
- [ ] 前端产物已重新构建（`npm run build` 已通过）；`/` 选择器、Skills 面板、详情弹层、工具卡片仍需人工开页面确认
- [ ] 实跑一次带 skill 的会话，确认清单注入、load/read/execute 三条链路可用（已用 `tests/test_skills.py::test_prompt_and_tool_chain_against_real_skills` 覆盖三条链路，未接真实大模型）