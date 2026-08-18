#!/usr/bin/env python3
"""Scaffold a map project folder inside a fortnite-maps content workspace.

Usage:
  python scaffold_project.py <workspace-dir> <map-name> [--project-root PATH]
                             [--project-file PATH] [--force]

Creates the workspace's own CLAUDE.md if it doesn't have one yet, then the
map folder. Writing is idempotent: existing files are left alone unless
--force, so re-running after linking a real UEFN path won't clobber notes.
INDEX.md files are not written here — run the plugin's scripts/reindex.py,
which generates them from each file's frontmatter.
"""

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
REINDEX = Path(__file__).resolve().parents[3] / "scripts" / "reindex.py"
UNLINKED = "(not yet linked — run find_uefn_projects / setup_uefn_project)"

# Directories whose contract is documented in the map's CLAUDE.md and that
# start empty; .gitkeep so git tracks them before anything is written.
EMPTY_DIRS = ["pending_work", "build-log", "knowledge", "verse"]

FILES = [
    ("map-claude-md.template.md", "CLAUDE.md"),
    ("docs/overview.template.md", "docs/overview.md"),
    ("docs/layout.template.md", "docs/layout.md"),
    ("docs/loot-and-resources.template.md", "docs/loot-and-resources.md"),
    ("docs/mechanics.template.md", "docs/mechanics.md"),
    ("state/level-stats.template.md", "state/level-stats.md"),
    ("state/standing-lessons.template.md", "state/standing-lessons.md"),
    ("state/verification.template.md", "state/verification.md"),
]


def render(template: str, subs: dict) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"skipped (already exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("workspace", help="The content workspace directory")
    parser.add_argument("name", help="Map project folder name")
    parser.add_argument("--project-root", help="Real UEFN project_root, if known")
    parser.add_argument("--project-file", help="Real .uefnproject path, if known")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    subs = {
        "WORKSPACE_NAME": workspace.name,
        "PROJECT_NAME": args.name,
        "DATE_CREATED": datetime.date.today().isoformat(),
        "PROJECT_ROOT": args.project_root or UNLINKED,
        "PROJECT_FILE": args.project_file or UNLINKED,
    }

    # The workspace CLAUDE.md is written once and never overwritten, even with
    # --force: it accumulates hand-written notes that no template knows about.
    root_claude = workspace / "CLAUDE.md"
    write(root_claude, render("workspace-claude-md.template.md", subs), force=False)

    project = workspace / args.name
    for template, out in FILES:
        write(project / out, render(template, subs), args.force)
    for name in EMPTY_DIRS:
        keep = project / name / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch()

    sys.stdout.flush()  # so the subprocess's output lands after ours
    if REINDEX.is_file():
        subprocess.run([sys.executable, str(REINDEX), str(workspace)], check=False)
    else:
        print(f"warning: reindex.py not found at {REINDEX}; INDEX.md not generated")

    print(f"map ready: {project}")


if __name__ == "__main__":
    main()
