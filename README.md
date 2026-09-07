# lc-agent

> Open-source AI Agent workbench & framework built on LangChain / LangGraph — visual, hot-swappable, fully extensible.
>
> 基于 LangChain / LangGraph 的 AI Agent 可视化工作台 & Python 框架，运行时热切换模型/工具/MCP/技能，无需重启，lc-agent既是产品又是框架。

[![PyPI package](https://img.shields.io/badge/pypi-lc--agent--app-blue)](https://pypi.org/project/lc-agent-app/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`lc-agent` 是一套开箱即用的 AI Agent 工作台，也是一个能被业务项目直接 `import` 的 Python 框架——不用从零搭建模型调用、工具注册、会话持久化这些基础能力。

`lc-agent` 把 **模型、思考参数、Tools、MCP、Skills、子 Agent、长期记忆、知识库、人工审批、自动化任务** 统一放进一个 Web UI，运行时即可在前端切换配置，无需重启服务。

`lc-agent` 对和模型的底层交互原理可视化做的超级强，让你很清楚看到harness和model的交互，极其清楚的看到每个部分的请求内容，对调试 看清楚自己的agent帮助很大，也就是对agent开发者更好，而不是只偏向于只用agent产品完成任务而对agent自身原理毫无感兴趣的普通用户。


演示项目：[lc-agent-bfzs](https://github.com/ydf0509/lc-agent-bfzs)

## 为什么是 lc-agent

用 LangChain / LangGraph 搭 Agent，通常要写大量样板代码，把模型调用、Tools、MCP、子 Agent 一层层串起来；换模型、换工具，往往还得改代码、重启服务。

`lc-agent` 把这些能力整合进一个开箱即用的 Web 工作台：

- **运行时热切换**：模型、思考等级、工具组、MCP、Skills、Agent 预设都在前端切换，不用重启
- **统一能力编排**：Tools、MCP、Skills、子 Agent、代码型 Graph 走同一个执行入口
- **全程可观测**：思考过程、工具调用、diff 预览、HTTP 追踪、token 用量、子 Agent 执行细节、 bash命令执行过程 全部可视化
- **权限与人工审批**：工具白名单、敏感操作人工确认，人始终保留最终控制权
- **框架与产品一体**：既能直接当工作台用，也能 `import lc_agent` 嵌入业务项目

## lc-agent 核心能力

| 能力 | 说明 |
| --- | --- |
| Agent Runtime | 内置 Chat / Empty / Power 预设，支持网页创建 Agent 与代码注册 Agent |
| Hot-swappable Config | 前端运行时切换模型、LLM 参数、工具、MCP、Skills，无需重启代码 |
| Tools | `@tool` 装饰器注册 Python 工具，支持分组展示与权限控制 |
| MCP | 支持 `stdio`、`SSE`、Streamable HTTP，自动适配 MCP 工具 schema |
| Skills | 扫描 `SKILL.md` 技能目录，支持渐进式发现与运行时开关 |
| Sub-agents | 支持子 Agent / 通用子 Agent 委派，并保留独立执行过程 |
| Human Control | 支持 Human-in-the-loop 审批与 Human-in-the-top 总控式调度 |
| AskUser | Agent 在信息不足、需求有歧义或关键动作前，可以主动询问用户确认 |
| Autonomous Planning | LLM 可用 TodoWrite 自主拆解任务步骤、维护执行计划、持续更新进度 |
| Memory | 支持会话持久化、历史消息、checkpoint 与长期上下文扩展 |
| Knowledge Base | 不内置强绑定 RAG，可通过 MCP 接入 [nbrag](https://github.com/ydf0509/nbrag) 等 agentic search 知识库 |
| Observability | HTTP trace、token 面板、工具调用卡片、子 Agent 过程可视化 |
| Auth & Permission | 支持登录认证、用户隔离、管理员能力、审批白名单 |
| 联网、rag知识库 | 同时通过接入对应的mcp来给llm提供能力，例如anysearch 和 nbrag |
| ai coding | 内置工具组和第三方mcp例如serena mcp都能使lc-aegnt 实现ai coding |
| Context Management | 内置 SummarizationMiddleware，长对话自动压缩摘要，避免上下文溢出 |
| Streaming & Diff | 命令执行实时流式输出、文件编辑 diff 预览、写入预览，过程全程可视 |
| 自动化任务 | 用户可以配置定时任务，agent自动定时运行任务，并发送通知到钉钉 企业微信 飞书中 |

### 完整功能清单请阅读 [FEATURES.md](https://github.com/ydf0509/lc-agent/blob/main/FEATURES.md)

## 截图

说明：产品界面与实际有差异，实际界面更加美观，功能更加强大，截图时间太早了，后来持续增加了功能，以实际运行界面为准。

**桌面端：对话 + MCP / Skills 面板**

![桌面端对话界面](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc01.png)

**可观测性：HTTP 追踪 + Token 面板 + 工具调用**

![HTTP追踪与Token面板](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc02.png)

**智能体管理**
![智能体管理](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/agent_management.png)

**工具调用详情**

![工具调用卡片](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/pc03.png)

**移动端**

![移动端界面](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/phone01.png)

**ai coding 执行用户代码，流式打字机效果**
![ai coding 执行用户代码，流式打字机效果](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/ai_coding_run.png)

**ai coding 编辑用户代码，类似cursor codex的代码变动 diff 红绿渲染**
![ai coding 编辑用户代码，类似cursor codex的代码变动 diff 红绿渲染](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/aicoding_edit.png)

**ai coding连续完成4个脚本，使用todolist自动规划任务步骤**
![ai coding2](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/aicoding2.png)

**集中查看agent修改或git变动**
![ai coding3](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/aicoding3.png)

**子 agent 效果，可委派给子 agent 执行，并流式打字机显示和保留独立执行过程**
![子 agent 效果，可委派给子 agent 执行，并流式打字机显示和保留独立执行过程](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/subagent.png)

## 快速开始

### 安装

PyPI 包名是 **`lc-agent-app`**，不是 `lc-agent`。

```bash
pip install lc-agent-app
```

如果你是从源码开发：

```bash
git clone https://github.com/ydf0509/lc-agent.git
cd lc-agent
pip install -e ".[dev,desktop]"
```

### 启动工作台

```bash
cp config.example.jsonc config.jsonc
# 编辑 config.jsonc，至少配置 provider、models、agent.default_model
lc-agent
# 打开 http://127.0.0.1:8000
```

如果配置里启用了 `auth.secret`，首次启动会进入登录流；默认会自动创建一个管理员账号：

- 用户名：`admin`
- 密码：`123456`

首次登录后建议立即修改密码。

## 作为框架使用

### 注册 Python 工具

```python
from lc_agent import LcAgentApp, set_config_path, tool

@tool(group="my_tools", group_description="我的工具")
def my_tool(query: str) -> str:
    """工具描述，会展示给 Agent 判断何时使用。"""
    return f"result: {query}"

set_config_path("./config.jsonc")   # 注册一次，框架内全局可取
app = LcAgentApp(host="127.0.0.1", port=8001)
app.run()
```

### 注册代码型 Agent

你可以把自己写好的 LangGraph `CompiledStateGraph` 注册到 lc-agent，复用现成前端、会话、权限、审批和可观测能力。

```python
from lc_agent import LcAgentApp, get_config, set_config_path
from my_agents import build_my_agent

set_config_path("./config.jsonc")
app = LcAgentApp(host="127.0.0.1", port=8001)
app.add_agent("my_agent", build_my_agent(get_config()), description="自定义 Agent")
app.run()
```

## 配置重点

大多数用户只需要关心这几个配置块：

- `provider`：模型提供商与模型列表
- `agent.default_model`：默认模型
- `skills`：Skills 目录
- `mcpServers`：MCP 服务器配置
- `database`：会话与 checkpoint 存储
- `auth`：登录认证与管理员配置

配置文件使用 `config.jsonc`，支持：

- JSONC 注释
- `{env:VAR}` 环境变量替换
- `.env` 自动加载

## MCP、Skills 与知识库

`lc-agent` 不把知识库硬编码进框架，而是通过 MCP 解耦接入。

这意味着你可以把 [nbrag](https://github.com/ydf0509/nbrag)、文件检索、网页搜索、数据库查询、业务系统 API 等能力全部作为 MCP 或 tool 接入同一个 Agent 控制台。

推荐理解方式：

- **Tools**：Agent 的操作接口（`@tool` 注册的函数 + 内置文件/命令工具组）
- **MCP**：按标准协议（stdio / Streamable HTTP）接入的外部工具服务器，不写代码就能给 Agent 扩展联网搜索、文档检索、知识库等能力
- **Skills**：写给 Agent 看的能力说明与工作流指令（SKILL.md），AI 按需加载，可带脚本执行
- **[nbrag](https://github.com/ydf0509/nbrag) / RAG**：作为 MCP 工具接入，保持知识库与 Agent 框架低耦合

## 项目文件夹模式

为 Agent 配置 `project_root` 路径后，lc-agent 会以该目录为上下文中心运行：

| 能力 | 说明 |
| --- | --- |
| AGENTS.md 注入 | 自动读取 `{project_root}/AGENTS.md` 作为系统指令 |
| 项目 Skills | 扫描 `{project_root}/.agents/skills/`，与全局 Skills 合并，同名时项目优先 |
| 项目 MCP | 读取 `{project_root}/.agents/mcp.json`，与全局 MCP 合并，同名时项目覆盖 |
| 文件访问范围 | `file_read` / `file_write` 工具默认只能访问项目目录 |
| 命令工作目录 | `run_command` 默认 CWD 为项目根目录 |

### `.agents/mcp.json` 格式

遵循与 Cursor / Claude Desktop 兼容的 `mcpServers` 格式（`command` + `args` 分开）：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./"],
      "env": {}
    },
    "my-http-server": {
      "url": "http://localhost:3001/sse",
      "enabled": true
    },
    "disabled-server": {
      "command": "npx",
      "args": ["-y", "@my/server"],
      "enabled": false
    }
  }
}
```

字段说明：
- `command`：可执行文件名（如 `npx`、`node`、`python`）
- `args`：参数数组
- `env`：额外环境变量（可选），会与系统环境合并
- `url`：SSE/HTTP 型服务器直接填 URL，无需 `command`/`args`
- `enabled`：默认 `true`，设为 `false` 可临时禁用

### `.agents/skills/` 格式

每个子目录为一个 Skill，包含 `SKILL.md`：

```
{project_root}/
└── .agents/
    ├── mcp.json          # 项目级 MCP 配置
    └── skills/
        └── my-skill/
            └── SKILL.md  # frontmatter: name + description
```

`SKILL.md` frontmatter 支持的字段：

```yaml
---
name: my-skill           # 必填，小写字母+连字符，唯一标识
description: 一句话描述  # 必填，LLM 用于判断何时调用
license: MIT             # 可选
metadata:                # 可选，dict 格式的自定义元数据
  group: "工具类"
---

# Skill 主体内容（Markdown 格式）
```

> **注意**：`compatibility` 字段若填写，必须是 `dict` 格式（如 `{python: "3.12+"}`），不可为字符串，否则该 Skill 会被跳过。其他未知字段会被忽略。

## Human-in-the-top

`lc-agent` 支持的不只是传统 human-in-the-loop。

Human-in-the-loop 通常是 Agent 遇到危险动作时请求审批；而 lc-agent 更强调 **Human-in-the-top**：

- 人可以在运行时切换模型和思考参数
- 人可以随时打开或关闭 tool groups、MCP servers、Skills
- 人可以切换不同 Agent 默认态，避免工具能力张冠李戴
- 人可以审批危险工具，并把可信工具加入持久化白名单
- Agent 可以在信息不足、存在歧义或需要确认时主动 AskUser，而不是低质量猜测
- Agent 可以用 TodoWrite 自主拆解任务、维护计划、更新进度，让复杂任务可追踪
- 人可以查看 Agent 与子 Agent 的完整执行过程

## API 与通信方式

`lc-agent` 当前主要通过 **REST + SSE** 工作。

常用接口包括：

- `POST /api/threads/{thread_id}/runs/stream`：SSE 流式运行
- `POST /api/threads/{thread_id}/runs/cancel`：取消当前生成
- `GET /api/agents/available-subagents`：查询可选子 Agent
- `GET /api/sessions/{id}/messages`：分页读取会话消息
- `GET /api/sessions/{id}/messages/{message_id}/traces`：读取单条消息 trace
- `GET /api/permissions`、`POST /api/permissions/allow`、`POST /api/permissions/remove`：审批白名单管理
- `POST /api/auth/login`、`GET /api/auth/me`：登录与用户信息

## 和普通聊天网页的区别

普通聊天网页，你问一句，它答一句——产物是一段文字，模型不会（也没能力）去碰你的文件、跑你的命令、动你的系统。

普通网页聊天，也能算agent，只不过那个agent是只给你联网工具，没有其他工具（你用脑子想下，如果没有给你配置高昂成本的虚拟容器的前提下，豆包官网给你配有命令行和文件操作工具，那么恶意用户会指挥豆包agent执行rm -rf删除豆包服务器，指挥豆包agent在豆包服务器上执行恶意代码程序 ， 但是如果跑在你自己本地电脑，你还会故意指挥codex claude code cursor 删除你自己系统文件和执行恶意程序吗？）。

lc-agent 里的 Agent 不只会答，还会**动手做**。区别落到四个字上：

- **执行**：聊天网页止于文字，lc-agent 能真正操作你的机器和外部系统
- **可观测**：思考过程、工具调用、HTTP 请求、token 用量、子 Agent 执行——每一步都摊开给你看，不是黑盒
- **可控**：模型、工具组、MCP、Skills 运行时随时切换，危险操作要过审批
- **可扩展**：是框架，能 `@tool` 注册工具、能配置mcp和skills，注册自定义 Agent、`import` 进业务项目——聊天网页是封闭产品

简单来说：

- **普通聊天网页**：只能聊
- **lc-agent**：能聊，更能做——而且做的过程看得见、管得住、换得了

### 即使是普通联网聊天，也吊打普通大模型官网联网聊天

因为对于复杂问题，需要多轮换关键词联网，需要分解任务，需要多次打开多个详情页提取正文，普通大模型官网的联网搜索为了节约算力完全没达到这种效果。
下面截图是lc-agent调用自己写的`baidu-search`联网搜索的skill，真实使用的截图，agent会分解步骤亲自搜索查看每一天央视新闻联播报道了什么，lcagent的提问效果吊打在deepseek官网直接问 "8月份央视新闻联报，每一天报道了什么"。
![baidu_skill_search](https://raw.githubusercontent.com/ydf0509/lc-agent/main/docs_pic/baidu_skill_search.png)


## 项目关系

| 项目 | 角色 |
| --- | --- |
| [lc-agent](https://github.com/ydf0509/lc-agent) | 框架与通用 Web UI |
| [lc-agent-bfzs](https://github.com/ydf0509/lc-agent-bfzs) | 基于 lc-agent 的演示应用 |
| [nbrag](https://github.com/ydf0509/nbrag) | 可通过 MCP 接入的 agentic search 知识库 |

## 登录、部署与多人共用

### lc-agent 适合部署在哪里？

lc-agent 不是「注册就能上」的云端聊天站，而是能接本地工具、MCP、脚本和执行环境的 Agent 框架，所以它更适合跑在你自己可控的地方：单机、内网，或者你自己的服务器或工作机。

### 支持登录和多用户吗？

支持。lc-agent 自带登录认证、用户隔离和管理员能力，在配置里启用 `auth.secret` 即可使用。

### 能多人共用一个实例吗？

分情况。

如果你只拿它聊天、查资料——联网检索、RAG 知识库检索都算，只要不开 `file_write`、`command` 这类工具组——完全可以多个人共用一个实例。

但只要开了这些工具组，就必须**一人一个实例**。原因很简单：它们直接操作部署机器的文件系统，多人同时用会互相踩。这和 Claude Code / Cursor / Codex 是同一个道理：凡是能读写本机文件的工具，都得一人一套环境。

另外记住一点：无论你给 Agent 接了什么——文件系统、命令执行、自定义 MCP——它能碰到的始终只是**部署机器**允许的范围，不会超出那台机器。

### 多用户 + 文件操作隔离（沙箱）不行吗？

技术上可行（比如每个用户一个虚拟容器），但成本极高，不在 lc-agent 当前的考虑范围内。

## 开发

后端开发：

```bash
pip install -e ".[dev]"
pytest
```

前端开发：

```bash
cd frontend
npm install
npm run dev
npm run build
```

常用前端契约测试：

```bash
cd frontend
npm run test:new-chat-right-panel
npm run test:session-route
npm run test:code-agent
```

## 启动gui客户端

参考下面这个例子,可以启动一个独立的客户端，而不是在浏览器中使用lc-aegnt

```python
from lc_agent.desktop import launch_desktop

launch_desktop(host='127.0.0.1', port=8001, title="心有灵犀") # host port title 按需改动。
```

[启动gui客户端](https://github.com/ydf0509/lc-agent-bfzs/blob/6cf03fe2db265021cf82964851fb84af625744b3/bfzs/start_desktop.py)


## FAQ

### lc-agent 是否内置 RAG 知识库？

不强绑定内置知识库。

推荐通过 MCP 接入 [nbrag](https://github.com/ydf0509/nbrag) 这类 agentic search 知识库。这样知识库能力可以同时服务 lc-agent、OpenClaw、Claude Code、Codex、Trae、Cursor、WorkBuddy、Qoder 等不同 Agent 客户端，框架和知识库保持低耦合。

### lc-agent 是产品还是框架？

两者都是。

你可以直接把它当 Agent 工作台使用，也可以把它作为 Python 包导入业务项目，复用现成 Web UI、会话、审批、MCP、Skills、工具注册、可观测性和运行时配置能力。

### 切换配置需要重启吗？

大多数运行时配置不需要。

模型、思考参数、工具组、MCP、Skills、Agent 默认态都可以通过前端热切换。只有修改 Python 代码、安装新依赖或调整底层服务部署时才需要重启对应服务。

### lc-agent 能不能联网查询问题？

答： 你购买大模型apikey后，模型厂商是不会自动送你联网功能的，联网实际是通过工具调用。
所以你可以配置mcp，市面上能联网的mcp有很多

例如配置 Open Web Search MCP，你在docker里面启动mcp服务，然后配置到config.jsonc里面的mcpServers，agent可以勾选启用这个mcp，这样`agent`就能联网查询新闻了，而且可以启用web-search这个skill，引导ai何时联网，怎么高效使用这个mcp的各个工具。

除了 `openwebsearch` mcp另外推荐一个更好更稳定更适合agent联网的mcp，`anysearch`，每天免费1000次，我在联网搜索某些技术文档时候，实测比deepseek 豆包官网的联网搜索更强。

```jsonc
{
    ...其他配置...
  "mcpServers": {

    // Web 搜索 MCP
     // 实时网页搜索 MCP（SSE 方式）
      // Open Web Search（多引擎搜索 + 文章抓取，Docker 部署）
      // 启动: docker run -d --name web-search -p 3000:3000 -e ENABLE_CORS=true -e CORS_ORIGIN=* ghcr.io/aas-ee/open-web-search:latest
    "web-search": {
      "type": "http",
      "url": "http://localhost:3000/mcp",
      "enabled": true
    },
  }
}
```

除了配 MCP，框架还内置一个**零成本**的联网 skill：`baidu-search`（位于 `lc_agent/skills/contrib_skills/baidu-search`）。

它走百度接口，**免费、无限次、无需 API key、无需启动任何 MCP 服务**，开箱即用。提供两个命令，Agent 通过 `run_skill_script` 执行 `baidu_search_cli.py` 调用：

- `search`：按关键词联网检索，返回标题/链接/摘要/时间
- `extract`：抓取指定网页并提取正文，可直接吃 `search` 返回的链接

默认用 `curl_cffi` 模拟 Chrome 指纹绕反爬，稳定性远超requests。和上面的 MCP 路线相比，它胜在**零部署、零花费**，适合不想折腾 MCP 服务、又想立刻让 Agent 联网的场景；缺点是依赖百度接口，搜索稳定性那肯定不如 anysearch大公司做的商业产品，anysearch的稳定性几乎100%了， baidu-search 的稳定性95%左右。

### lc-agent 支持什么数据库？
答：lc-agent分为langchain的checkpoint数据库和业务数据库。
checkpoint数据库支持sqlite postgre
业务数据库使用的sqlmodel，所以支持所有sqlachemy支持的数据库

### lc-agent 能不能作为aicoding 工具来使用？

答：完全可以，而且编程效果和体验都很好。

方案A:
可以，你可以搭配serena mcp全套来编程。但是这个因为是第三方mcp，对于edit文件 和 执行命令，lc-agent的前端界面没有精细化适配，例如文件变更diff、执行命令的流式打字机效果等，对serena没支持。所以不推荐用serena mcp全套工具。
方案A不好，和lc-agent的前端ui没有深度融合。

方案B：
开启lc-agent 内置赠送的工具组， 用户开启`file_read` `file_write` `command` 三个工具组，大约20个工具，足以编程了。另外你还可以搭配 nbrag 或者codegraph mcp，使代码语义和符号检索更强大。
lc-agent前端对代码改动和代码执行的渲染，达到了 traework codex-gui 的体验效果。


lc-agent 既可以作为 你的private gpt纯聊天页面来使用，也可以作为 通用agent来使用，ai coding只是能力之一。

### agent 设置项目模式后有什么区别？

答：相当于 Cursor / Codex 打开某个项目的效果。绑定本地目录后，AI 自动识别并遵守该项目的 `AGENTS.md` 规则，同时加载项目专属的 Skills（技能），加载项目级mcp配置文件，无需每次手动告知 AI 当前在哪个项目。
相当于你为cursor codex创建的项目级别的 AGENTS.md 和 .agents 文件夹的skills和mcp配置，能被`lc-agent`自动复用。

### 质疑lc-agent是不是装逼重复造轮子，为什么不直接用codex traework？

lc-agent既是产品又是框架， 是给希望开发agent人员用的，或者对agent开发感兴趣，或者对ai为什么能编程写代码有兴趣的人员用的。是给希望自定义开发agent的，尤其是使用langchain开发agent的人 用的。 里面的很多功能都是对观测llm行为有巨大帮助的，看下lc-agent的前端界面就知道了，里面有大量的功能是帮助看清和llm交互的详细过程，而不是简单的像`openwebui`那样给普通非码农用的普通聊天网页。从lc-agent前端就能很清楚知道到底和llm是怎么交互的，codex traework qoder是黑盒的，不方便你看到底层交互原理。

codex是给普通码农编程用的，如果你对开发自己的agent毫无兴需求和兴趣，对和llm交互毫无兴趣，对ai原理毫无兴趣，只是希望用ai来完成写普通业务项目代码，那当然直接用codex就可以了。

## License

MIT
