#!/usr/bin/env python3
"""Create or refresh a fortnite-maps workspace root.

  init-root <path> [--force]
      Create the workspace root folder (if needed), its CLAUDE.md, and
      install the two per-workspace Claude Code skills (new-map-project,
      load-map-project) into <path>/.claude/skills/. Those skills are
      self-contained copies — once installed, project scaffolding happens
      from a Claude Code session opened directly in the workspace, not
      from this repo.

Writing is idempotent: existing files are left untouched by default.
--force only affects the installed skill files (SKILL.md, scripts,
templates under .claude/skills/*) so they can be refreshed after this
repo's source templates change; it never touches the root CLAUDE.md or
anything inside a project subfolder, since those may already hold notes
written by hand.
"""

import argparse
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"
WORKSPACE_SKILLS_SRC = TEMPLATES_DIR / "workspace-skills"

PROJECT_TEMPLATE_NAMES = [
    "project-claude-md.template.md",
    "brief.template.md",
    "build-log.template.md",
    "class-paths.template.md",
]


def render(template_name: str, substitutions: dict) -> str:
    text = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"skipped (already exists): {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"wrote: {path}"


def copy_file(src: Path, dest: Path, force: bool) -> str:
    if dest.exists() and not force:
        return f"skipped (already exists): {dest}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return f"wrote: {dest}"


def install_workspace_skills(root: Path, force: bool) -> None:
    skills_dir = root / ".claude" / "skills"

    new_project_dir = skills_dir / "new-map-project"
    print(write_file(
        new_project_dir / "SKILL.md",
        (WORKSPACE_SKILLS_SRC / "new-map-project.template.md").read_text(encoding="utf-8"),
        force,
    ))
    print(copy_file(
        WORKSPACE_SKILLS_SRC / "scaffold_project.py",
        new_project_dir / "scripts" / "scaffold_project.py",
        force,
    ))
    for name in PROJECT_TEMPLATE_NAMES:
        print(copy_file(TEMPLATES_DIR / name, new_project_dir / "assets" / "templates" / name, force))

    load_project_dir = skills_dir / "load-map-project"
    print(write_file(
        load_project_dir / "SKILL.md",
        (WORKSPACE_SKILLS_SRC / "load-map-project.template.md").read_text(encoding="utf-8"),
        force,
    ))


def init_root(args: argparse.Namespace) -> None:
    root = Path(args.path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    content = render("root-claude-md.template.md", {})
    print(write_file(root / "CLAUDE.md", content, force=False))

    install_workspace_skills(root, args.force)

    print(f"workspace root ready: {root}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_root = sub.add_parser("init-root", help="Create or refresh the fortnite-maps workspace root")
    p_root.add_argument("path", help="Path to the workspace root folder (created if missing)")
    p_root.add_argument("--force", action="store_true", help="Overwrite installed skill files if they already exist")
    p_root.set_defaults(func=init_root)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
