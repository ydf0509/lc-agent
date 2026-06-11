import pytest

from lc_agent.skills.scanner import SkillScanner


@pytest.fixture
def skills_dir(tmp_path):
    skill1 = tmp_path / "coding" / "SKILL.md"
    skill1.parent.mkdir()
    skill1.write_text(
        "---\nname: coding-assistant\ndescription: Expert coding help\n---\n\n# Coding\n\nYou write clean code.\n",
        encoding="utf-8",
    )

    skill2 = tmp_path / "research" / "SKILL.md"
    skill2.parent.mkdir()
    skill2.write_text(
        "---\nname: researcher\ndescription: Deep research\n---\n\n# Research\n\nYou research thoroughly.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_scan_skills(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    skills = scanner.scan()
    assert len(skills) == 2
    names = [s.name for s in skills]
    assert "coding-assistant" in names
    assert "researcher" in names


def test_skill_content(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    scanner.scan()
    skill = scanner.get_by_name("coding-assistant")
    assert skill is not None
    assert "clean code" in skill.content
    assert skill.description == "Expert coding help"


def test_filter_skills(skills_dir):
    scanner = SkillScanner(str(skills_dir))
    scanner.scan()

    all_skills = scanner.get_filtered(None)
    assert len(all_skills) == 2

    no_skills = scanner.get_filtered([])
    assert len(no_skills) == 0

    some = scanner.get_filtered(["researcher"])
    assert len(some) == 1
    assert some[0].name == "researcher"


def test_empty_directory(tmp_path):
    scanner = SkillScanner(str(tmp_path / "nonexistent"))
    skills = scanner.scan()
    assert len(skills) == 0
