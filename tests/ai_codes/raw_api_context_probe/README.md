# Raw API context probe

独立诊断脚本：**不经过 LangChain / lc-agent**，直接用 `httpx` 请求 OpenAI-compatible
`/chat/completions`，用 `tiktoken` 构造大上下文，观察是否复现 `httpx.ReadError`。

## 目的

把“模型/网关断流”和“LangChain / lc-agent 封装”分开：

- 如果这个脚本在大上下文下也报 `ReadError` → 问题在 provider/网关/网络，不在 LangChain。
- 如果脚本正常、lc-agent 才报 → 差异在 lc-agent 的系统提示词、工具 schema、流式处理或 agent 循环。
- 如果返回 `400/413 context_length_exceeded` → 上下文限制，不是断流。

## 依赖

项目已有：`httpx`、`tiktoken`、`python-dotenv`。脚本不导入 LangChain。

## 用法

### 1. 只构造 prompt，不发请求

```powershell
& 'D:\ProgramData\Miniconda3\envs\py312\python.exe' `
  tests/ai_codes/raw_api_context_probe/probe.py `
  --dry-run --target-tokens 255000
```

### 2. 小请求冒烟（先确认 key / URL / model 正确）

```powershell
& 'D:\ProgramData\Miniconda3\envs\py312\python.exe' `
  tests/ai_codes/raw_api_context_probe/probe.py `
  --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" `
  --model deepseek/deepseek-v4.1-flash `
  --target-tokens 1000 --max-tokens 8
```

### 3. 大上下文复现（实际失败模型）

```powershell
& 'D:\ProgramData\Miniconda3\envs\py312\python.exe' `
  tests/ai_codes/raw_api_context_probe/probe.py `
  --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" `
  --model deepseek/deepseek-v4.1-flash `
  --target-tokens 340000 --max-tokens 8 --timeout 180
```

### 4. 长输出复现（更接近 lc-agent 的真实调用）

```powershell
& 'D:\ProgramData\Miniconda3\envs\py312\python.exe' `
  tests/ai_codes/raw_api_context_probe/probe.py `
  --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" `
  --model deepseek/deepseek-v4.1-flash `
  --target-tokens 340000 --max-tokens 2000 --long-output --timeout 300
```

### 5. 对照实验

```powershell
# 非流式请求：看是否只有 stream 断
... --target-tokens 340000 --no-stream

# CommandCode 内部另一个模型（例如 Mimo）
... --model xiaomi/mimo-v2.6-pro --target-tokens 255000

# 预留 system 消息（总 target 不变，模拟 agent 的 system prompt 占用）
... --target-tokens 340000 --system-tokens 20000
```

### 6. 工具调用流（agent 的真实路径）

```powershell
& 'D:\ProgramData\Miniconda3\envs\py312\python.exe' `
  tests/ai_codes/raw_api_context_probe/probe.py `
  --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" `
  --model deepseek/deepseek-v4.1-flash `
  --target-tokens 340000 --max-tokens 100 --tool-call --timeout 180
```

## 关键参数

| 参数 | 说明 |
|---|---|
| `--target-tokens` | 目标上下文 token 数（`cl100k_base` 估算，实际以 API 计费为准） |
| `--system-tokens` | 从总 target 中划给 system message 的 token 数，默认 0 |
| `--long-output` | 把最后指令改成要求长文输出，配合较大的 `--max-tokens` |
| `--tool-call` | 发送一个简单 tool schema，要求模型调用工具，观察 tool-call 流 |
| `--instruction` | 自定义最后一段指令（覆盖默认的“只回复 OK”） |
| `--max-tokens` | 输出上限，默认 8，避免浪费 |
| `--timeout` | 客户端 read timeout，默认 180s |
| `--no-stream` | 改成非流式请求，用于对照 |
| `--no-proxy` | 不读取 `HTTP(S)_PROXY` 环境变量 |
| `--include-usage` | 流式请求加 `stream_options.include_usage`（部分 provider 不支持） |
| `--dry-run` | 只构造 prompt，不发请求 |
| `--request-file` | 直接重放一个完整的 chat-completions JSON body（例如从会话 `http_traces` 的 `request.body` 导出） |
| `--override-max-tokens` | 覆盖请求 body 里的 `max_tokens` / `max_completion_tokens`，用于控制输出成本 |
| `--override-model` | 覆盖请求 body 里的 model（例如用 ark 的真实上下文去重放 CommandCode） |

### 7. 用 http_traces 里的真实 request body 重放

`chat_ui_messages.http_traces` 的 `request.body` 就是 lc-agent 当时发出的完整
OpenAI-compatible JSON body（敏感 header 已打码；body 里不含 API key）。把它导出成
JSON 文件后，可以直接原样重放，不再用填充文本估算：

```powershell
# 原样重放（body 里已有 max_completion_tokens）
... --request-file .tmp/raw_api_context_probe/real_request_06_25_0.json --timeout 300

# 想把输出压到 8 tokens 做便宜重放
... --request-file .tmp/raw_api_context_probe/real_request_06_25_0.json `
    --override-max-tokens 8 --timeout 180

# 用 ark 的真实上下文，改 model 后在 CommandCode 上重放
... --request-file .tmp/raw_api_context_probe/real_request_36.json `
    --override-model deepseek/deepseek-v4.1-flash `
    --override-max-tokens 64000 --timeout 300
```

## 输出怎么看

- `first_data_at: 13.42s`：多久收到第一个 SSE data。
- `RESULT: READ_ERROR` + `httpx.ReadError` / `httpcore.ReadError` 链：读 body 时连接被对端关闭/重置。
- `RESULT: READ_TIMEOUT`：客户端等数据超过 `--timeout`，和 `ReadError` 不是一回事。
- `status: 400` / `413` + body：上下文或参数被服务端拒绝，通常会带 `context_length_exceeded` 等信息。
- `RESULT: OK`：原始接口在这组参数下正常；差异化排查 lc-agent 的请求内容/流处理。

## 注意

- CommandCode 的 `--model` 要填 **raw_model_id**（例如 `deepseek/deepseek-v4.1-flash`），
  不要填 lc-agent 的 `cm-*` 别名。
- 不要把 API key 写在命令行或提交到仓库；用 `--env-file` 或环境变量。
- 大上下文会消耗真实 token；先用 `--dry-run` 和小请求确认参数。
