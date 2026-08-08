---
name: load-map-project
description: Loads context for an existing UEFN/Fortnite map project subfolder in this fortnite-maps workspace — reads its CLAUDE.md/brief/build-log/class-paths, confirms the live UEFN editor matches, and links project_root/project_file if it wasn't known at scaffold time. Use whenever the user wants to resume work on an existing map, asks about a map's status, or wants to continue a previously scaffolded project.
---

# Load an existing map project

## Find the project

List this workspace's subfolders and match one to what the user asked for
(by name, or by asking if ambiguous). Each project subfolder has
`CLAUDE.md`, `brief.md`, `build-log.md`, and `class-paths.md`.

## Load context

Read, in order:

1. `<project>/CLAUDE.md` — the real `project_root`/`.uefnproject` location
   and any per-project conventions.
2. `<project>/brief.md` — what the map is for.
3. `<project>/build-log.md` — skim from the top (newest first) for the most
   recent decisions and whether the last session called `save_level`.
4. `<project>/class-paths.md` — device/Blueprint class paths already
   discovered, so they don't need rediscovering via `execute_python`.

## Confirm the editor matches

Only one UEFN editor can be connected to at a time, and discovery connects
to whichever node it finds first. Before running any `uefn` MCP tool
against this project, confirm the editor actually open in UEFN is *this*
project and not a different one from the workspace — e.g. compare
`get_editor_status`'s reported project against `CLAUDE.md`'s
`project_root`.

## Link it, if it isn't yet

If `CLAUDE.md`'s `project_root` / `.uefnproject file` still show the "not
yet linked" placeholder, resolve the real path with `find_uefn_projects`
(and `setup_uefn_project` if remote execution has never been enabled for
it), then edit `CLAUDE.md` directly with the `Edit` tool to replace the
placeholder lines. Don't regenerate the file from a template for this —
that would discard anything already written into `brief.md` or
`build-log.md`.

## While working

- Append to `build-log.md` (newest entry on top) after making meaningful
  changes in the editor, noting whether `save_level` was called — this is
  the only real history the level gets, since the binary UEFN project isn't
  practical to track in git.
- Add a row to `class-paths.md` the first time a new device/Blueprint class
  path is discovered.
