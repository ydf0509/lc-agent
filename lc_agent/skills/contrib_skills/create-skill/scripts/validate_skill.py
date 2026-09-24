#!/usr/bin/env python3
"""Validate an Agent Skill directory: encoding, frontmatter, naming, and structure."""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _error(msg: str) -> str:
    return f"  ERROR: {msg}"


def _warn(msg: str) -> str:
    return f"  WARN:  {msg}"


def _ok(msg: str) -> str:
    return f"  OK:    {msg}"


NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def validate(skill_dir: Path) -> list[str]:
    results: list[str] = []
    errors = 0

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        results.append(_error("SKILL.md not found"))
        return results

    raw = skill_file.read_bytes()

    # --- Encoding ---
    if raw[:3] == b"\xef\xbb\xbf":
        results.append(_warn("SKILL.md has UTF-8 BOM — some parsers may choke on it"))
        raw = raw[3:]

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        results.append(_error(f"SKILL.md is not valid UTF-8: {e}"))
        return results

    results.append(_ok("Encoding: UTF-8"))

    if "\x00" in text:
        results.append(_error("SKILL.md contains null bytes — likely a binary file"))
        return results

    # --- Frontmatter ---
    m = FRONTMATTER_RE.match(text.strip())
    if not m:
        results.append(_error("Missing or malformed YAML frontmatter (must start and end with ---)"))
        return results

    yaml_str, body = m.group(1), m.group(2)

    if yaml is None:
        results.append(_warn("PyYAML not installed — skipping frontmatter field validation"))
        fm: dict = {}
    else:
        try:
            fm = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            results.append(_error(f"Invalid YAML: {e}"))
            return results

        if not isinstance(fm, dict):
            results.append(_error("Frontmatter must be a YAML mapping"))
            return results

    results.append(_ok("Frontmatter: valid YAML"))

    # --- Required fields ---
    name = fm.get("name")
    desc = fm.get("description")

    if not name:
        results.append(_error("Missing required field: name"))
        errors += 1
    else:
        if len(name) > 64:
            results.append(_error(f"name too long: {len(name)} chars (max 64)"))
            errors += 1
        if not NAME_RE.match(name):
            if re.match(r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$", name):
                results.append(_warn(f"name '{name}' uses underscores — works on some platforms but violates the Agent Skills spec (hyphens only)"))
            else:
                results.append(_error(f"name '{name}' violates format: lowercase letters, digits, hyphens only; no leading/trailing/consecutive hyphens"))
                errors += 1
        if "--" in name:
            results.append(_error(f"name '{name}' contains consecutive hyphens"))
            errors += 1
        if name != skill_dir.name:
            results.append(_warn(f"name '{name}' does not match directory '{skill_dir.name}' — skill__load_skill may fail"))
        else:
            results.append(_ok(f"Name: '{name}' matches directory"))

    if not desc:
        results.append(_error("Missing required field: description"))
        errors += 1
    else:
        if len(desc) > 1024:
            results.append(_error(f"description too long: {len(desc)} chars (max 1024)"))
            errors += 1
        elif len(desc) < 20:
            results.append(_warn(f"description very short ({len(desc)} chars) — may not trigger reliably"))
        else:
            results.append(_ok(f"Description: {len(desc)} chars"))

    # --- Body ---
    lines = body.strip().split("\n")
    line_count = len(lines)
    if line_count > 500:
        results.append(_warn(f"Body is {line_count} lines (recommended < 500)"))
    else:
        results.append(_ok(f"Body: {line_count} lines"))

    # --- Structure ---
    known_dirs = {"scripts", "references", "assets", "agents"}
    for child in sorted(skill_dir.iterdir()):
        if child.is_file() and child.name == "SKILL.md":
            continue
        if child.is_dir() and child.name in known_dirs:
            file_count = sum(1 for _ in child.rglob("*") if _.is_file())
            results.append(_ok(f"{child.name}/: {file_count} file(s)"))
        elif child.is_file() and child.name in ("license.txt", "LICENSE"):
            results.append(_ok(f"{child.name}: present"))
        elif child.is_file() and child.suffix == ".md" and child.name != "SKILL.md":
            results.append(_warn(f"Extra markdown file '{child.name}' — consider moving to references/"))

    # --- Common anti-patterns ---
    bad_files = {"README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"}
    for bf in bad_files:
        if (skill_dir / bf).exists():
            results.append(_warn(f"'{bf}' should not be in a skill — remove it"))

    return results


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <skill-directory>")
        return 1

    skill_dir = Path(sys.argv[1]).resolve()
    if not skill_dir.is_dir():
        print(f"Not a directory: {skill_dir}")
        return 1

    print(f"Validating: {skill_dir}\n")
    results = validate(skill_dir)
    for r in results:
        print(r)

    has_errors = any("ERROR:" in r for r in results)
    has_warns = any("WARN:" in r for r in results)

    print()
    if has_errors:
        print("FAILED — fix errors above")
        return 1
    elif has_warns:
        print("PASSED with warnings")
        return 0
    else:
        print("PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
