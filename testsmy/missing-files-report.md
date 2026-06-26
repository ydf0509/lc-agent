# lc_agent 缺失文件报告

## 问题概述

commit `074311c`（消息 "1"，2026-06-25 21:47）删除了 `lc_agent/` 下的 25 个源文件（及 frontend 等其他文件共计 96 个文件）。
后续 commit 没有恢复这些文件，导致 **源码缺失但 `__pycache__` 编译缓存还在**，程序暂时能跑但极不稳定。

---

## 缺失文件清单（17 个 .py 文件）

| 文件路径 | 作用 | 被哪些文件 import |
|---|---|---|
| `lc_agent/__main__.py` | `python -m lc_agent` 入口 | - |
| `lc_agent/main.py` | 启动脚本 | - |
| `lc_agent/config/__init__.py` | config 包初始化 | 所有 `from lc_agent.config.xxx` |
| `lc_agent/core/__init__.py` | core 包初始化 | 所有 `from lc_agent.core.xxx` |
| `lc_agent/db/__init__.py` | db 包初始化 | 所有 `from lc_agent.db.xxx` |
| `lc_agent/db/engine.py` | 数据库初始化 `init_db()` | `lc_agent/app.py` |
| `lc_agent/mcp/__init__.py` | mcp 包初始化 | 所有 `from lc_agent.mcp.xxx` |
| `lc_agent/mcp/manager.py` | MCP 服务管理 `McpManager` | `lc_agent/app.py` |
| `lc_agent/mcp/tool_adapter.py` | MCP 工具适配器 | `mcp/manager.py` |
| `lc_agent/server/__init__.py` | server 包初始化 | 所有 `from lc_agent.server.xxx` |
| `lc_agent/server/app.py` | FastAPI app 创建 `create_app()` | `lc_agent/app.py` |
| `lc_agent/server/dependencies.py` | FastAPI 依赖注入 `get_engine, get_registry, get_db_session` | `routes/tools.py`, `routes/sessions.py` |
| `lc_agent/server/routes/__init__.py` | routes 包初始化 | - |
| `lc_agent/server/routes/agents.py` | Agent preset CRUD API | `server/app.py` |
| `lc_agent/server/routes/health.py` | 健康检查 API | `server/app.py` |
| `lc_agent/server/routes/models.py` | 模型列表 API | `server/app.py` |
| `lc_agent/skills/__init__.py` | skills 包初始化 | 所有 `from lc_agent.skills.xxx` |
| `lc_agent/tools/__init__.py` | tools 包初始化 | 所有 `from lc_agent.tools.xxx` |
| `lc_agent/tools/registry.py` | `ToolRegistry` 类 + `@tool` 装饰器 | `__init__.py`, `engine.py`, `routes/tools.py` |
| `lc_agent/tools/builtin.py` | 内置工具定义 | `tools/__init__.py` |
| `lc_agent/utils/loggers.py` | 日志工具 | 未知 |

---

## 为什么程序暂时还能跑

每个被删的目录下都有 `__pycache__/` 保留了 `.pyc` 编译缓存：

```
config/__pycache__/__init__.cpython-312.pyc
core/__pycache__/__init__.cpython-312.pyc
db/__pycache__/__init__.cpython-312.pyc, engine.cpython-312.pyc
mcp/__pycache__/__init__.cpython-312.pyc, manager.cpython-312.pyc, tool_adapter.cpython-312.pyc
server/__pycache__/__init__.cpython-312.pyc, app.cpython-312.pyc, dependencies.cpython-312.pyc
server/routes/__pycache__/__init__.cpython-312.pyc, agents.cpython-312.pyc, health.cpython-312.pyc, models.cpython-312.pyc
skills/__pycache__/__init__.cpython-312.pyc
tools/__pycache__/__init__.cpython-312.pyc, registry.cpython-312.pyc
```

Python 的 import 机制会优先使用 `.pyc`，所以在 `.pyc` 被清除前程序不会报错。

**风险**：一旦删除 `__pycache__`、升级 Python、或修改任何被删文件的代码（触发重编译），程序立即崩溃。

---

## 处理方案

### 方案 A：从 git 历史恢复（推荐）

从 `074311c` 的父 commit 恢复所有被删文件：

```powershell
cd D:\codes\lc-agent
git checkout 074311c^ -- lc_agent/__main__.py lc_agent/config/__init__.py lc_agent/core/__init__.py lc_agent/db/__init__.py lc_agent/db/engine.py lc_agent/main.py lc_agent/mcp/__init__.py lc_agent/mcp/manager.py lc_agent/mcp/tool_adapter.py lc_agent/server/__init__.py lc_agent/server/app.py lc_agent/server/dependencies.py lc_agent/server/routes/__init__.py lc_agent/server/routes/agents.py lc_agent/server/routes/health.py lc_agent/server/routes/models.py lc_agent/skills/__init__.py lc_agent/tools/__init__.py lc_agent/tools/builtin.py lc_agent/tools/registry.py lc_agent/utils/loggers.py
```

恢复后验证：
```powershell
# 确认文件恢复
Get-ChildItem lc_agent/tools/ -Name
# 应输出: __init__.py, builtin.py, registry.py

# 测试 import
D:\ProgramData\Miniconda3\envs\py312\python.exe -c "from lc_agent.tools.registry import ToolRegistry; print('OK')"
```

然后提交：
```powershell
git add lc_agent/
git commit -m "restore: 恢复被误删的 lc_agent 源文件"
```

### 方案 B：只恢复被 import 引用的关键文件

如果不确定所有文件是否还需要，最低限度恢复当前代码有 import 的文件：

```powershell
git checkout 074311c^ -- lc_agent/config/__init__.py lc_agent/core/__init__.py lc_agent/db/__init__.py lc_agent/db/engine.py lc_agent/mcp/__init__.py lc_agent/mcp/manager.py lc_agent/mcp/tool_adapter.py lc_agent/server/__init__.py lc_agent/server/app.py lc_agent/server/dependencies.py lc_agent/server/routes/__init__.py lc_agent/skills/__init__.py lc_agent/tools/__init__.py lc_agent/tools/registry.py
```

### 方案 C：不恢复，依赖 __pycache__

不做任何操作，但需注意：
- 不能删 `__pycache__`
- 不能升级 Python 小版本（如 3.12.x → 3.12.y 一般没事，但 3.12 → 3.13 会失效）
- 修改这些模块的代码时无法生效（因为源文件不存在，`.pyc` 不会更新）

**强烈不建议此方案。**

---

## 前端缺失文件（28 个源文件）

同一个 commit `074311c` 删除了 41 个前端文件（不含 node_modules/.vite），磁盘上也不存在。

关键缺失：

| 文件 | 作用 |
|---|---|
| `frontend/index.html` | 前端入口 HTML |
| `frontend/vite.config.ts` | Vite 构建配置 |
| `frontend/tsconfig.json` | TypeScript 配置 |
| `frontend/package-lock.json` | 依赖锁文件 |
| `frontend/.gitignore` | git 忽略规则 |
| `frontend/src/main.ts` | 应用入口 |
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/router/index.ts` | 路由配置 |
| `frontend/src/stores/agents.ts` | Agent 状态管理 |
| `frontend/src/stores/sessions.ts` | 会话状态管理 |
| `frontend/src/components/chat/ChatBubble.vue` | 聊天气泡组件 |
| `frontend/src/components/chat/ToolCallCard.vue` | 工具调用卡片 |
| `frontend/src/components/chat/TokenUsagePanel.vue` | Token 用量面板 |
| `frontend/src/components/chat/MessageToolbar.vue` | 消息工具栏 |
| `frontend/src/components/chat/InterruptDialog.vue` | 中断确认对话框 |
| `frontend/src/components/chat/CopyRoundsButton.vue` | 复制轮次按钮 |
| `frontend/src/components/layout/AppHeader.vue` | 顶部导航栏 |
| `frontend/src/components/layout/LeftSidebar.vue` | 左侧边栏 |
| `frontend/src/components/dialogs/AgentEditorDialog.vue` | Agent 编辑对话框 |
| `frontend/src/components/panels/ModelSelector.vue` | 模型选择器 |
| `frontend/src/composables/useTheme.ts` | 主题切换 |
| `frontend/src/utils/client-id.ts` | 客户端 ID |
| `frontend/src/utils/markdown.ts` | Markdown 渲染 |
| `frontend/src/style.css` | 全局样式 |
| `frontend/src/views/TestSegments.vue` | 测试视图 |
| `frontend/env.d.ts` | 环境类型声明 |
| `frontend/auto-imports.d.ts` | 自动导入声明 |
| `frontend/public/favicon.svg` | 网站图标 |

**前端为什么还能用**：`lc_agent/web/dist/` 里的编译产物还在，服务端直接托管。但源码没了就无法 `npm run build` 重新编译。

### 前端恢复命令

```powershell
cd D:\codes\lc-agent
git checkout 074311c^ -- frontend/.gitignore frontend/auto-imports.d.ts frontend/env.d.ts frontend/index.html frontend/package-lock.json frontend/public/favicon.svg frontend/src/App.vue frontend/src/components/chat/ChatBubble.vue frontend/src/components/chat/CopyRoundsButton.vue frontend/src/components/chat/InterruptDialog.vue frontend/src/components/chat/MessageToolbar.vue frontend/src/components/chat/TokenUsagePanel.vue frontend/src/components/chat/ToolCallCard.vue frontend/src/components/dialogs/AgentEditorDialog.vue frontend/src/components/layout/AppHeader.vue frontend/src/components/layout/LeftSidebar.vue frontend/src/components/panels/ModelSelector.vue frontend/src/composables/useTheme.ts frontend/src/main.ts frontend/src/router/index.ts frontend/src/stores/agents.ts frontend/src/stores/sessions.ts frontend/src/style.css frontend/src/utils/client-id.ts frontend/src/utils/markdown.ts frontend/src/views/TestSegments.vue frontend/tsconfig.json frontend/vite.config.ts
```

---

## 额外信息

- 删除发生在：commit `074311c` (2026-06-25 21:47)
- 该 commit 同时删除了整个 `frontend/` 目录（但 HEAD commit `60ce9f8` 重新加入了 `frontend/node_modules/`）
- `lc_agent/db/migrations/` 相关文件（`README`, `env.py`, `script.py.mako`, `a342dc61a740_initial_schema.py`）也被删除
