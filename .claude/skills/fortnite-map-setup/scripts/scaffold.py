#!/usr/bin/env python3
"""Scaffold a fortnite-maps workspace or a project subfolder within one.

Two subcommands:

  init-root <path>
      Create the workspace root folder (if needed) and its CLAUDE.md.

  new-project <root> <name> [--project-root PATH] [--project-file PATH]
      Create a project subfolder under an existing workspace root, with
      CLAUDE.md, brief.md, build-log.md, and class-paths.md filled in from
      templates.

Writing is idempotent: existing files are left untouched unless --force is
passed, so re-running this after linking a project's real UEFN path (via
new-project --project-root/--project-file) won't clobber notes already
written into brief.md or build-log.md.
"""

import argparse
import datetime
import sys
from pathlib import Path

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


def init_root(args: argparse.Namespace) -> None:
    root = Path(args.path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    content = render("root-claude-md.template.md", {})
    print(write_file(root / "CLAUDE.md", content, args.force))
    print(f"workspace root ready: {root}")


def new_project(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: workspace root does not exist: {root}", file=sys.stderr)
        print("run 'init-root' first", file=sys.stderr)
        sys.exit(1)

    project_dir = root / args.name
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_root = sub.add_parser("init-root", help="Create the fortnite-maps workspace root")
    p_root.add_argument("path", help="Path to the workspace root folder (created if missing)")
    p_root.add_argument("--force", action="store_true", help="Overwrite CLAUDE.md if it already exists")
    p_root.set_defaults(func=init_root)

    p_new = sub.add_parser("new-project", help="Scaffold a project subfolder under a workspace root")
    p_new.add_argument("root", help="Path to the workspace root (must already exist)")
    p_new.add_argument("name", help="Subfolder / project name")
    p_new.add_argument("--project-root", help="Real UEFN project_root path, if already known")
    p_new.add_argument("--project-file", help="Real .uefnproject file path, if already known")
    p_new.add_argument("--force", action="store_true", help="Overwrite files that already exist")
    p_new.set_defaults(func=new_project)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
