from typing import Any

from langchain_core.messages import SystemMessage

from lc_agent.middlewares.system_prompt import SystemPromptMiddleware


def _get_user_os_text() -> str:
    """Build the <user_os> block: server OS + shell + syntax guidance.

    Commands run on the deployed service, so the OS here is authoritative
    for run_command / start_background_process syntax choice.
    """
    import os
    import platform

    os_name = platform.system()
    # Mirror run_command's shell selection logic for consistency:
    # Windows defaults to powershell; Linux/macOS reads $SHELL.
    # Check config.jsonc's system_tools.command.default_shell first.
    try:
        from lc_agent.tools.system_tools._config import get_command_config
        _cmd_cfg = get_command_config()
        _configured_shell = _cmd_cfg.get("default_shell", "")
    except Exception:
        _configured_shell = ""
    if _configured_shell:
        shell = _configured_shell.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    elif os_name == "Windows":
        shell = "powershell"
    else:
        shell = os.environ.get("SHELL", "bash").rsplit("/", 1)[-1]
    try:
        os_version = platform.version() if os_name == "Linux" else platform.release()
        os_info = f"{os_name} {os_version} ({shell})"
    except Exception:
        os_info = f"{os_name} ({shell})"

    shell_lower = shell.lower()
    if "powershell" in shell_lower or "pwsh" in shell_lower or os_name == "Windows":
        guidance = (
            "Commands MUST use PowerShell syntax. "
            "NEVER use Linux commands (head/cat/grep/ls/tail). "
            "Use Select-Object instead of head, Select-String instead of grep. "
            "Chain dependent commands with `; if ($?) { ... }`, NOT `&&`."
        )
    elif "cmd" in shell_lower:
        guidance = (
            "Commands MUST use cmd.exe syntax. "
            "NEVER use Linux commands (head/cat/grep/ls/tail)."
        )
    else:
        guidance = "Commands MUST use bash/sh syntax."
    return f"<user_os>\n**OS**: {os_info}\n{guidance}\n</user_os>"


class UserOsMiddleware(SystemPromptMiddleware):  # type: ignore[misc]
    """Appends the <user_os> block as the final system-message content block."""

    def __init__(self, text: str, middleware_name: str, *, prepend: bool = False):
        super().__init__(text, middleware_name, prepend=prepend)

    def _patched_system(self, existing: Any) -> Any:
        if self._prepend:
            new_block = {"type": "text", "text": _get_user_os_text()}
            new_content = [new_block, *(existing.content_blocks if existing is not None else [])]
        else:
            new_block = {"type": "text", "text": f"\n\n{_get_user_os_text()}"}
            new_content = [*(existing.content_blocks if existing is not None else []), new_block]
        return SystemMessage(content_blocks=new_content)  # type: ignore[call-arg]


user_os_middleware = UserOsMiddleware(text="", middleware_name="UserOsMiddleware", prepend=False)
