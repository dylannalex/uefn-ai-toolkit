---
name: fortnite-map-setup
description: Bootstraps a "fortnite-maps" workspace for UEFN/Fortnite map projects — a separate, git-friendly folder of markdown notes (brief, build log, discovered class paths, per-project CLAUDE.md) built with the uefn-mcp MCP server. Use this whenever the user wants to start tracking Fortnite/UEFN map projects with Claude, set up or organize a workspace for one or more maps, or asks for a place to keep notes/briefs/build logs for a map — even if they don't say "skill" or name the folder explicitly. This only creates/refreshes the workspace itself; actual project creation and day-to-day work happen from a Claude Code session opened in that workspace, via the new-map-project / load-map-project skills it installs there.
---

# Fortnite map workspace setup

`uefn-mcp` (the MCP server this repo builds) drives a live UEFN editor over
Python remote execution, but it stores nothing about the maps themselves —
the real map is the `.uefnproject` file and its binary assets, wherever UEFN
saved them. Claude also has no memory of the live editor between
conversations. This skill bootstraps a separate, git-friendly workspace that
fills that gap: a `fortnite-maps` folder, with one subfolder per map project
holding a brief, a running build log, discovered device/class paths, and a
CLAUDE.md that points at the project's real location.

This skill's only job is to find-or-create that workspace root and install
two Claude Code skills into it (`new-map-project`, `load-map-project`) —
it does not scaffold individual projects itself. Those installed skills are
self-contained copies (their own script, their own templates), so a Claude
Code session opened directly in `fortnite-maps` can create and resume
projects on its own, without the `uefn-mcp` checkout being present. Because
Claude Code only discovers skills from the current session's own project
directory, a session working inside `uefn-mcp` cannot invoke skills
installed under a different folder — so after bootstrapping, tell the user
to open (or switch to) a Claude Code session with `fortnite-maps` as the
working directory to actually create or work on a map.

Do the file/skill creation with `scripts/scaffold.py`, not by hand-writing
markdown — the templates in `assets/templates/` (including
`assets/templates/workspace-skills/`, the source for the two installed
skills) are the source of truth for structure and wording.

```
python scripts/scaffold.py init-root <path> [--force]
```

Run this with the skill's own directory as the working directory, or invoke
via an absolute path to `scaffold.py` — it locates its templates relative to
itself either way.

Writing is idempotent:

- The root `CLAUDE.md` is written once and never overwritten by this script
  again (it may accumulate hand-written notes) — regardless of `--force`.
- `--force` only affects the installed skill files under
  `<root>/.claude/skills/*` (SKILL.md, scripts, templates) — pass it when
  this repo's workspace-skill templates have changed and an existing
  workspace should pick up the update. It never touches a project
  subfolder's `CLAUDE.md`/`brief.md`/`build-log.md`/`class-paths.md`.

## Find or create the workspace root

Check whether a `fortnite-maps` workspace already exists before creating a
new one — look for a `CLAUDE.md` whose first heading matches
`fortnite-maps workspace` (that's what `init-root` writes). Reasonable places
to check: a `fortnite-maps` folder next to whatever repo/cwd the user is
currently in, and any path the user has mentioned before.

If nothing is found, this is a new directory outside the current project, so
confirm the location with the user rather than silently deciding — default
suggestion is a `fortnite-maps` folder as a **sibling of the `uefn-mcp`
checkout** (i.e. `../fortnite-maps` relative to this repo), but the user may
prefer somewhere else (their general projects folder, an existing notes
repo, etc.).

Once confirmed:

```
python scripts/scaffold.py init-root "<chosen-path>"
```

This is safe to run even if the folder partially exists. Report what got
written vs. skipped, then tell the user the workspace (and its
`new-map-project` / `load-map-project` skills) are ready, and that
creating or resuming a map project happens from a Claude Code session
opened in that folder.

## MCP server registration

Both installed skills call the `uefn` MCP server's tools
(`find_uefn_projects`, `setup_uefn_project`, etc.). That server must be
registered at **user scope** (`claude mcp add uefn --scope user -- ...`,
see this repo's README) rather than the default local/project scope — user
scope is what makes it reachable from a session opened in `fortnite-maps`
instead of `uefn-mcp`. If `get_editor_status` or similar calls fail with the
server unavailable from within the workspace, check registration scope
before assuming a UEFN-side problem.
