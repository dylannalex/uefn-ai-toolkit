#!/usr/bin/env python3
"""Scaffold a new project subfolder in this fortnite-maps workspace.

Usage:
  python scripts/scaffold_project.py <name> [--project-root PATH] [--project-file PATH] [--force]

Writing is idempotent: existing files are left untouched unless --force is
passed, so re-running this after linking a project's real UEFN path won't
clobber notes already written into brief.md or build-log.md.
"""

import argparse
import datetime
import sys
from pathlib import Path

# scripts/scaffold_project.py -> new-map-project -> skills -> .claude -> workspace root
ROOT = Path(__file__).resolve().parents[4]
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"

UNLINKED_PLACEHOLDER = "(not yet linked — run find_uefn_projects / setup_uefn_project)"


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="Project subfolder name")
    parser.add_argument("--project-root", help="Real UEFN project_root path, if already known")
    parser.add_argument("--project-file", help="Real .uefnproject file path, if already known")
    parser.add_argument("--force", action="store_true", help="Overwrite files that already exist")
    args = parser.parse_args()

    if not ROOT.is_dir():
        print(f"error: workspace root does not exist: {ROOT}", file=sys.stderr)
        sys.exit(1)

    project_dir = ROOT / args.name
    subs = {
        "PROJECT_NAME": args.name,
        "DATE_CREATED": datetime.date.today().isoformat(),
        "PROJECT_ROOT": args.project_root or UNLINKED_PLACEHOLDER,
        "PROJECT_FILE": args.project_file or UNLINKED_PLACEHOLDER,
    }

    for template_name, out_name in [
        ("project-claude-md.template.md", "CLAUDE.md"),
        ("brief.template.md", "brief.md"),
        ("build-log.template.md", "build-log.md"),
        ("class-paths.template.md", "class-paths.md"),
    ]:
        content = render(template_name, subs)
        print(write_file(project_dir / out_name, content, args.force))

    print(f"project ready: {project_dir}")


if __name__ == "__main__":
    main()
