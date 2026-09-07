from pathlib import Path


PACKAGE_ROOT = Path("lc_agent")


def _is_skill_cli_script(relative_path: Path) -> bool:
    """Skill CLI scripts live under `skills/**/scripts/`.

    They print on purpose: stdout IS the tool's return value, consumed by the
    agent through `run_skill_script`. Routing that through a logger would break
    the skill, so these are exempt from the no-print rule.
    """
    parts = relative_path.parts
    return "skills" in parts and "scripts" in parts


def test_lc_agent_package_does_not_use_print_for_logging():
    violations = []
    repo_root = Path(__file__).resolve().parents[1]

    for path in (repo_root / PACKAGE_ROOT).rglob("*.py"):
        relative_path = path.relative_to(repo_root)
        if _is_skill_cli_script(relative_path):
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "print(" in stripped:
                violations.append(f"{relative_path}:{line_number}: {stripped}")

    assert violations == []
