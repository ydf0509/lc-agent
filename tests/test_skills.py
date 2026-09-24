from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from nb_langchain_agentskills import SkillNotFoundError

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import init_db, reset_engine
from lc_agent.skills.filtered_loader import LcAgentSkillLoader
from lc_agent.skills.skill_middleware import (
    MAX_DESCRIPTION_CHARS,
    _build_skills_prompt,
    _LcAgentSkillMiddleware,
)
from tests.conftest import setup_test_auth

@pytest.fixture
def skills_dir(tmp_path):
    root = tmp_path / "skills"
    skill1 = root / "coding" / "SKILL.md"
    skill1.parent.mkdir(parents=True)
    skill1.write_text(
        "---\nname: coding-assistant\ndescription: Expert coding help\n---\n\n# Coding\n\nYou write clean code.\n",
        encoding="utf-8",
    )

    skill2 = root / "research" / "SKILL.md"
    skill2.parent.mkdir()
    skill2.write_text(
        "---\nname: researcher\ndescription: Deep research\n---\n\n# Research\n\nYou research thoroughly.\n",
        encoding="utf-8",
    )

    ref = root / "coding" / "references" / "guide.md"
    ref.parent.mkdir()
    ref.write_text("# Guide\n\nReference body.\n", encoding="utf-8")
    return root


def test_loader_lists_skills(skills_dir):
    loader = LcAgentSkillLoader([str(skills_dir)])
    names = [s.name for s in loader.list_skills()]
    assert names == ["coding-assistant", "researcher"]


def test_disabled_skill_is_hidden_on_every_path(skills_dir):
    loader = LcAgentSkillLoader([str(skills_dir)])

    assert loader.toggle("coding-assistant") is False

    assert "coding-assistant" not in {s.name for s in loader.list_skills()}
    with pytest.raises(SkillNotFoundError):
        loader.load_skill("coding-assistant")
    with pytest.raises(SkillNotFoundError):
        loader.read_content("coding-assistant", "SKILL.md")
    with pytest.raises(SkillNotFoundError):
        loader.resolve_root("coding-assistant")

    # The UI report still sees the skill, and can still resolve its real directory
    assert "coding-assistant" in {s.name for s in loader.list_all_skills()}
    assert loader.resolve_root_any("coding-assistant") == skills_dir / "coding"

    assert loader.toggle("coding-assistant") is True
    assert [s.name for s in loader.list_skills()] == ["coding-assistant", "researcher"]


def test_overlay_overrides_global(skills_dir, tmp_path):
    overlay = tmp_path / "overlay" / "coding"
    overlay.mkdir(parents=True)
    (overlay / "SKILL.md").write_text(
        "---\nname: coding-assistant\ndescription: Project coding help\n---\n\n# Project\n",
        encoding="utf-8",
    )

    loader = LcAgentSkillLoader([str(skills_dir)])
    loader.set_project_overlay(str(overlay.parent))

    visible = {s.name: s for s in loader.list_skills()}
    assert visible["coding-assistant"].description == "Project coding help"
    assert loader.resolve_root("coding-assistant") == overlay

    # The global report never sees the overlay
    global_skills = {s.name: s for s in loader.list_global_skills()}
    assert global_skills["coding-assistant"].description == "Expert coding help"

    loader.set_project_overlay(None)
    assert loader.resolve_root("coding-assistant") == skills_dir / "coding"


def test_skill_prompt_supports_direct_slash_commands():
    skill = type("Skill", (), {
        "name": "coding-assistant",
        "description": "Expert coding help",
    })()

    prompt = _build_skills_prompt([skill])

    assert "standalone `/`" in prompt
    assert "/coding-assistant" in prompt
    assert "call `skill__load_skill`" in prompt


def test_skill_prompt_keeps_full_multiline_description():
    description = "First line summary.\nUse when the user asks for a thing."
    skill = type("Skill", (), {"name": "multi", "description": description})()

    prompt = _build_skills_prompt([skill])

    assert "Use when the user asks for a thing." in prompt


def test_skill_prompt_caps_very_long_description():
    skill = type("Skill", (), {"name": "long", "description": "x" * 5000})()

    prompt = _build_skills_prompt([skill])

    assert "x" * MAX_DESCRIPTION_CHARS in prompt
    assert "x" * (MAX_DESCRIPTION_CHARS + 1) not in prompt


def test_middleware_registers_three_tools(skills_dir):
    loader = LcAgentSkillLoader([str(skills_dir)])

    middleware = _LcAgentSkillMiddleware(loader)

    assert {tool.name for tool in middleware.tools} == {
        "skill__load_skill",
        "skill__read_content",
        "skill__execute_script",
    }
    assert middleware.has_visible_skills is True


def test_middleware_with_empty_allowed_list_has_no_visible_skills(skills_dir):
    loader = LcAgentSkillLoader([str(skills_dir)])

    middleware = _LcAgentSkillMiddleware(loader, allowed_skills=[])

    assert middleware.has_visible_skills is False


CONTRIB_SKILLS = Path(__file__).resolve().parents[1] / "lc_agent" / "skills" / "contrib_skills"


def test_prompt_and_tool_chain_against_real_skills():
    """Smoke test over the shipped contrib skills: prompt + load/read/execute."""
    loader = LcAgentSkillLoader([str(CONTRIB_SKILLS)])

    prompt = _build_skills_prompt(loader.list_skills())
    assert "baidu-search" in prompt

    middleware = _LcAgentSkillMiddleware(loader)
    assert middleware.has_visible_skills is True
    tools = {tool.name: tool for tool in middleware.tools}

    loaded = tools["skill__load_skill"].invoke({"skill_name": "baidu-search"})
    assert "skill__execute_script" in loaded
    assert "references/zhihu-browser-access.md" in loaded

    content = tools["skill__read_content"].invoke(
        {"skill_name": "baidu-search", "file_path": "references/zhihu-browser-access.md"}
    )
    assert content.strip()

    result = tools["skill__execute_script"].invoke(
        {"skill_name": "baidu-search", "command": "echo skill-ok"}
    )
    assert "exit_code: 0" in result
    assert "skill-ok" in result


@pytest.fixture
async def app_with_skills(skills_dir, tmp_path):
    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}"
    await init_db(db_url)

    config = {
        "provider": {
            "openai": {
                "base_url": "http://fake",
                "api_key": "sk-fake",
                "models": [{"model_id": "gpt-4", "raw_model_id": "gpt-4"}],
            }
        },
        "agent": {"default_model": "gpt-4", "system_prompt": "You are helpful."},
        "skills": [str(skills_dir)],
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app = LcAgentApp(config)
    headers = await setup_test_auth(app.fastapi_app)
    yield app, headers
    reset_engine()

@pytest.mark.asyncio
async def test_toggle_skill_increments_mcp_generation(app_with_skills):
    app, headers = app_with_skills
    transport = ASGITransport(app=app.fastapi_app)
    gen_before = app.engine._mcp_generation

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/skills/coding-assistant/toggle", headers=headers)

    assert resp.status_code == 200
    assert app.engine._mcp_generation == gen_before + 1


@pytest.mark.asyncio
async def test_skill_detail_returns_body_files_and_root(app_with_skills):
    app, headers = app_with_skills
    transport = ASGITransport(app=app.fastapi_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/skills/coding-assistant", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "You write clean code." in data["body"]
    assert any("references/guide.md" in f for f in data["files"])
    assert data["root"].replace("\\", "/").endswith("/skills/coding")
    assert "resources" not in data and "scripts" not in data

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/skills/coding-assistant/files/references/guide.md", headers=headers
        )

    assert resp.status_code == 200
    assert resp.json()["file"] == "references/guide.md"
    assert "Reference body." in resp.json()["content"]