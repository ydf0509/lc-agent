"""Skills middleware for the agent engine."""

from nb_langchain_agentskills import (
    AllowedSkillLoader,
    CommandExecutor,
    SkillLoader,
    SkillMetadata,
    SkillsMiddleware,
)


MAX_DESCRIPTION_CHARS = 2000


def _description_for_prompt(description: str) -> str:
    """Return the full skill description, capped at ``MAX_DESCRIPTION_CHARS``."""
    text = description.strip()
    if len(text) <= MAX_DESCRIPTION_CHARS:
        return text
    return text[:MAX_DESCRIPTION_CHARS].rstrip() + "…"


def _build_skills_prompt(skills: list[SkillMetadata]) -> str:
    """Build the JSON-format skills system-prompt block. Returns empty string when skills list is empty."""
    if not skills:
        return ""
    import json as _json
    skill_entries = [
        {"skill_name": s.name, "description": _description_for_prompt(s.description)}
        for s in skills
    ]
    lines = [
        "<available_skills>",
        "## Available Skills",
        "",
        "The descriptions below are **triggers** — they tell you WHEN a skill applies.",
        "The actual step-by-step instructions, required tools, and constraints are INSIDE the skill.",
        "",
        "**MANDATORY RULE**: When the user's request matches a skill's description,",
        "you MUST call `skill__load_skill(skill_name=\"<skill_name>\")` FIRST to retrieve",
        "the full instructions, then follow them exactly.",
        "Do NOT skip this step and proceed with your default approach.",
        "",
        "**DIRECT SKILL COMMAND**: If the user's message contains a standalone `/`",
        "followed immediately by a listed skill name (for example `/coding-assistant`),",
        "treat it as an explicit request to use that skill. You MUST call `skill__load_skill`",
        "for that exact skill name FIRST, then treat the remaining text as the user's task.",
        "",
        "```json",
        _json.dumps(skill_entries, ensure_ascii=False, indent=2),
        "```",
        "",
        "After loading a skill, you may also call `skill__read_content` to fetch",
        "its reference files or `skill__execute_script` to run a shell command",
        "inside the skill directory.",
        "</available_skills>",
    ]
    return "\n".join(lines)


class _LcAgentSkillMiddleware(SkillsMiddleware):
    """SkillsMiddleware with the lc-agent prompt format and per-preset allow-list.

    Wraps the shared loader with ``AllowedSkillLoader`` so only the permitted
    skills for this preset appear in the system prompt and can be loaded by
    the agent. The skill list is injected into the prompt, so the
    ``skill__list_skills`` tool is not registered.
    """

    def __init__(
        self,
        loader: SkillLoader,
        *,
        allowed_skills: list[str] | None = None,
        executor: CommandExecutor | None = None,
    ) -> None:
        effective_loader = (
            AllowedSkillLoader(loader, set(allowed_skills))
            if allowed_skills is not None
            else loader
        )
        super().__init__(
            effective_loader,
            executor=executor or CommandExecutor(),
            exclude_tools={"skill__list_skills"},
            prompt_builder=_build_skills_prompt,
        )