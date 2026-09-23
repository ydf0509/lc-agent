# lc_agent/core/model_resolve.py
"""独立的模型别名解析：model_id（前端别名）→ ModelInfo（含渠道真实参数）。

不依赖 AgentEngine。用户自定义 Agent 想复用 config.jsonc 里配好的
provider/模型时，调 resolve_model 即可；不想复用配置时直接手写 LLM 参数。
"""

from lc_agent.core.models import ModelInfo


def parse_models(config: dict) -> list[ModelInfo]:
    """从配置解析 ModelInfo 列表。

    Fail fast: collect ALL problems (missing model_id/raw_model_id, duplicate
    model_id) and raise once with the full list, instead of failing one at a time.
    允许同一 provider 下多个 model_id 指向同一 raw_model_id（例如同一底层模型
    用不同 context_limit 暴露多个入口）。
    """
    problems: list[str] = []
    parsed: list[tuple[str, dict, dict]] = []  # (provider_name, provider_conf, model_conf)
    seen_model_ids: dict[str, str] = {}        # model_id -> provider（全局唯一，跨 provider 也算）
    for provider_name, provider_conf in config.get("provider", {}).items():
        if not isinstance(provider_conf, dict):
            continue
        for model_conf in provider_conf.get("models", []):
            model_id = model_conf.get("model_id", "")
            raw_model_id = model_conf.get("raw_model_id", "")
            if not model_id:
                problems.append(f"provider={provider_name} 的模型条目缺少 model_id：{model_conf}")
            if not raw_model_id:
                problems.append(f"provider={provider_name} 的模型 {model_id or model_conf} 缺少 raw_model_id")
            if model_id:
                if model_id in seen_model_ids:
                    problems.append(
                        f"model_id 重复：{model_id!r} 同时被 provider={seen_model_ids[model_id]} "
                        f"和 provider={provider_name} 使用（model_id 必须全局唯一，跨 provider 也算）"
                    )
                else:
                    seen_model_ids[model_id] = provider_name
            parsed.append((provider_name, provider_conf, model_conf))
    if problems:
        raise ValueError(
            "模型配置校验失败（共 %d 处）：\n  - " % len(problems) + "\n  - ".join(problems)
        )
    return [
        ModelInfo(
            model_id=model_conf["model_id"],
            raw_model_id=model_conf["raw_model_id"],
            provider=provider_name,
            base_url=provider_conf.get("base_url", ""),
            context_limit=model_conf.get("context_limit", 200000),
            max_output_tokens=model_conf.get("max_output_tokens", 0),
            api_key=provider_conf.get("api_key", ""),
        )
        for provider_name, provider_conf, model_conf in parsed
    ]


def find_model(model_id: str, config: dict) -> ModelInfo | None:
    """按 model_id（前端别名）查 ModelInfo，找不到返回 None。"""
    if not model_id:
        return None
    for m in parse_models(config):
        if m.model_id == model_id:
            return m
    return None


def resolve_model(model_id: str, config: dict | None = None) -> ModelInfo | None:
    """model_id → ModelInfo（含 raw_model_id / base_url / api_key / provider）。

    config 为 None 时自动用全局配置（入口 set_config_path 注册的那份）。
    不想复用配置时不用调它——直接手写 LLM 参数即可。
    """
    if config is None:
        from lc_agent.config import get_config
        config = get_config()
    return find_model(model_id, config)


def resolve_request_model(model_id: str, config: dict | None = None) -> str:
    """Alias → 渠道真实模型名：请求一律发 raw_model_id，model_id 只做前端别名。"""
    info = resolve_model(model_id, config) if model_id else None
    if info and info.raw_model_id:
        return info.raw_model_id
    return model_id
