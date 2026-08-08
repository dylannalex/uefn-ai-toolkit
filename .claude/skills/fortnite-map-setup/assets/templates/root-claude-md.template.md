# CLAUDE.md — fortnite-maps workspace

This folder holds working notes and briefs for UEFN/Fortnite map projects built
with Claude Code via the `uefn-mcp` MCP server. It is **not** the source of
the maps themselves — the real map data (the `.uefnproject` file and its
binary assets) lives inside each project's own UEFN project folder, wherever
UEFN saves it. This repo is just a readable, git-friendly layer of context
that survives between sessions, since Claude has no memory of the live editor
between conversations and the binary UEFN files can't be diffed or reviewed
in a PR.

## Layout

One subfolder per UEFN project, named to match the project. Each contains:

- `CLAUDE.md` — the real `project_root` path (the folder with the
  `.uefnproject` file), the project's display name in UEFN, and any
  per-project conventions (actor naming, coordinate/grid layout).
- `brief.md` — what the map is for: goal, rough layout, planned
  devices/mechanics.
- `build-log.md` — a running log of decisions and iterations across
  sessions, including when `save_level` was called. This is the closest
  thing to version history the level gets, since the actual UEFN project
  isn't practical to track in git.
- `class-paths.md` — Fortnite Blueprint/device class paths discovered by
  running `execute_python` against the live editor. These aren't hardcoded
  anywhere in `uefn-mcp` and are tedious to rediscover every session, so
  write them down the first time they're found.

## Working conventions

- **Only one UEFN editor can be connected to at a time**, and discovery
  picks whichever editor node it finds first. Before working in a project
  subfolder, make sure that project (and only that project) is the one open
  in UEFN — otherwise commands may run against the wrong map.
- Before scaffolding or working in a project folder, resolve its real UEFN
  location with the `uefn` MCP server's `find_uefn_projects` /
  `setup_uefn_project` tools rather than guessing a path. `setup_uefn_project`
  also handles the one-time `bRemoteExecution=True` config edit a fresh UEFN
  project needs (UEFN must be restarted afterward for it to take effect).
- Keep `class-paths.md` entries even if they turn out to be reusable across
  projects — copy useful ones into a new project's file rather than making
  everyone dig through `execute_python` output again.
