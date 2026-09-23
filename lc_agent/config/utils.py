from typing import Any

_MISSING = object()

# 统一的配置默认值，全项目唯一来源
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./lc_agent_data.db"
DEFAULT_CHECKPOINT_PATH = "./lc_agent_checkpoints.db"
DEFAULT_APP_NAME = "lc-agent"
# MCP 工具单次调用超时（秒），对应配置键 mcp.tool_timeout
DEFAULT_MCP_TOOL_TIMEOUT = 300
# LangGraph 超级步上限，对应配置键 agent.recursion_limit
DEFAULT_RECURSION_LIMIT = 9999
# 子 Agent 最大嵌套深度（0 表示禁用子 Agent），对应配置键 agent.max_subagent_depth
DEFAULT_MAX_SUBAGENT_DEPTH = 2
# 模型调用重试次数（openai SDK 层内置重试，只覆盖 429/5xx/超时/连接错误这类
# "响应开始前"的失败；流式吐字中途断流不会重试），对应配置键 agent.model_retry.max_retries
DEFAULT_MODEL_MAX_RETRIES = 3

# set_config_path 注册配置路径所用的环境变量名
ENV_CONFIG_PATH = "LC_AGENT_CONFIG_PATH"


def get_config_value(config: Any, path: str, default: Any = None) -> Any:
    """按点路径读取嵌套配置，例如 get_config_value(config, "database.url", DEFAULT_DATABASE_URL)。

    config 支持 dict（按键读取）和任意对象（按属性读取，如 pydantic 模型）。
    路径中任意一层缺失、为 None 或类型不支持时，直接返回 default；
    键存在但值为 None 时返回 None（与 dict.get 语义一致）。
    """
    current = config
    for key in path.split("."):
        if current is None:
            return default
        if isinstance(current, dict):
            if key not in current:
                return default
            current = current[key]
        else:
            current = getattr(current, key, _MISSING)
            if current is _MISSING:
                return default
    return current
