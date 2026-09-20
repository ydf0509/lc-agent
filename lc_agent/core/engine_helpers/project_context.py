"""Project context builder — git snapshot for the agent system prompt."""


def _build_project_context_text(project_root: str) -> str:
    """Build a project context block with git snapshot.

    Runs git commands synchronously (called once at agent build time).
    OS info lives in the <user_os> block (see user_os_middleware), not here.
    """
    import subprocess

    def _git(cmd: list[str]) -> str:
        try:
            r = subprocess.run(
                cmd, cwd=project_root, capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip()
        except Exception:
            return ""

    is_git = _git(["git", "rev-parse", "--git-dir"])
    if is_git:
        branch = _git(["git", "branch", "--show-current"]) or "(detached HEAD)"
        last_commit = _git(["git", "log", "-1", "--oneline"]) or "(no commits)"
        status_out = _git(["git", "status", "--short"])
        git_section = (
            f"**Branch**: {branch}\n"
            f"**Last Commit**: {last_commit}\n"
            f"**Git Status** (snapshot at session start):\n"
            f"```\n{status_out or '(clean)'}\n```\n\n"
            f"> Git status is a snapshot. Run `run_command` to refresh if needed."
        )
    else:
        git_section = "**Git Status**: Not a git repository"

    return (
        "<project_context>\n"
        "## Project Context\n\n"
        f"**Root**: {project_root}\n"
        f"{git_section}"
        "\n</project_context>"
    )
