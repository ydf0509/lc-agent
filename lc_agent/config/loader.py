import os
import re
from pathlib import Path
from typing import Any

import commentjson
from dotenv import load_dotenv

ENV_PATTERN = re.compile(r"\{env:([^}]+)\}")


def substitute_env_vars(data: Any) -> Any:
    """Recursively replace {env:VAR_NAME} patterns with environment variable values."""
    if isinstance(data, str):
        match = ENV_PATTERN.fullmatch(data)
        if match:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        def replacer(m):
            var_name = m.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        return ENV_PATTERN.sub(replacer, data)
    elif isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    return data


def load_config_from_file(path: str) -> dict:
    """Load a JSONC configuration file and apply env substitution."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = commentjson.load(f)

    return substitute_env_vars(raw)


def load_config(
    config_path: str | None = None,
    dotenv_path: str | None = None,
) -> dict:
    """Load configuration with priority: explicit path > ./config.jsonc > ~/.lc_agent/config.jsonc > defaults."""
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        load_dotenv()

    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.append(Path.cwd() / "config.jsonc")
    search_paths.append(Path.home() / ".lc_agent" / "config.jsonc")

    for p in search_paths:
        if p.exists():
            config = load_config_from_file(str(p))
            config["_config_path"] = str(p)
            config["_project_root"] = str(p.parent)
            return config

    return {
        "provider": {},
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ""},
        "_config_path": None,
        "_project_root": str(Path.cwd()),
    }
