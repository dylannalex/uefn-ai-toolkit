---
name: fortnite-map-setup
description: Scaffolds and maintains a "fortnite-maps" workspace of markdown notes (brief, build log, discovered class paths, per-project CLAUDE.md) for UEFN/Fortnite map projects built with the uefn-mcp MCP server. Use this whenever the user wants to start a new Fortnite/UEFN map project, set up or organize a workspace for tracking multiple maps, asks for a place to keep notes/briefs/build logs for a map, or asks about best practices for organizing UEFN projects with Claude — even if they don't say "skill" or name the folder explicitly. Also use it to link an already-scaffolded project folder to its real UEFN project_root once that's known.
---

# Fortnite map workspace setup

`uefn-mcp` (the MCP server this repo builds) drives a live UEFN editor over
Python remote execution, but it stores nothing about the maps themselves —
the real map is the `.uefnproject` file and its binary assets, wherever UEFN
saved them. Claude also has no memory of the live editor between
conversations. This skill scaffolds a separate, git-friendly workspace of
markdown files that fills that gap: one folder per map project, holding the
brief, a running build log, discovered device/class paths, and a CLAUDE.md
that points at the project's real location.

Do the file creation with `scripts/scaffold.py`, not by hand-writing the
markdown — the templates in `assets/templates/` are the source of truth for
structure and wording, and the script's idempotency (it skips files that
already exist unless `--force`) is what makes it safe to re-run later
without clobbering notes someone already wrote into `brief.md` or
`build-log.md`.

```
python scripts/scaffold.py init-root <path>
python scripts/scaffold.py new-project <root> <name> [--project-root PATH] [--project-file PATH] [--force]
```

Run these with the skill's own directory as the working directory, or invoke
via an absolute path to `scaffold.py` — it locates its templates relative to
itself either way.

## Step 1 — find or create the workspace root

Check whether a `fortnite-maps` workspace already exists before creating a
new one — look for a `CLAUDE.md` whose first heading matches
`fortnite-maps workspace` (that's what `init-root` writes). Reasonable places
to check: a `fortnite-maps` folder next to whatever repo/cwd the user is
currently in, and any path the user has mentioned before.

If nothing is found, this is a new directory outside the current project, so
confirm the location with the user rather than silently deciding — default
suggestion is a `fortnite-maps` folder as a **sibling of the `uefn-mcp`
checkout** (i.e. `../fortnite-maps` relative to this repo), but the user may
prefer somewhere else (their general projects folder, a existing notes repo,
etc.).

Once confirmed:

```
python scripts/scaffold.py init-root "<chosen-path>"
```

This is safe to run even if the folder partially exists — it only touches
`CLAUDE.md` there, and skips it if already present.

## Step 2 — scaffold a project subfolder

Before creating the subfolder, try to resolve the project's *real* UEFN
location so `CLAUDE.md` can point at it immediately instead of a placeholder:

- If the user gave a path, or one is discoverable, call the `uefn` MCP
  server's `find_uefn_projects` tool (optionally scoped with `search_paths`
  to keep it fast) to get the `project_root` and `project_file`.
- If the project is brand new and has never had remote execution enabled,
  `setup_uefn_project` does that one-time config edit — mention that UEFN
  needs restarting afterward for it to take effect.
- If the project can't be resolved yet (e.g. the user just wants to start
  planning before anything exists in UEFN), that's fine — proceed without
  `--project-root`/`--project-file` and the template records that it isn't
  linked yet, without blocking on it.

Then scaffold:

```
python scripts/scaffold.py new-project "<root>" "<project-name>" --project-root "<path>" --project-file "<path>"
```

Omit the two `--project-*` flags if the location isn't known yet. This
creates `<root>/<project-name>/` with `CLAUDE.md`, `brief.md`,
`build-log.md`, and `class-paths.md`.

After scaffolding, if the user has described what the map is for, use that
to fill in `brief.md`'s Goal/Layout/Devices sections right away with the
`Edit` tool rather than leaving it as bare headings — the template is a
skeleton, not a form for the user to fill in themselves later.

## Linking a project after the fact

If a project was scaffolded before its UEFN location was known (both
`--project-*` flags omitted), link it once that's resolved by editing
`<project>/CLAUDE.md` directly with the `Edit` tool — replace the
`**project_root**` and `**.uefnproject file**` placeholder lines with the
real paths. Don't re-run `new-project --force` for this: force rewrites all
four files from their templates, which would discard anything already
written into `brief.md`, `build-log.md`, or `class-paths.md`.

## Ongoing use (not just initial setup)

Once a project folder exists, treat it as living documentation, not a
one-time scaffold:

- Append to `build-log.md` (newest entry on top) after making meaningful
  changes in the editor, noting whether `save_level` was called — this is
  the only real history the level gets, since the binary UEFN project isn't
  practical to track in git.
- Add a row to `class-paths.md` the first time a device/Blueprint class path
  is discovered via `execute_python`, so it doesn't need rediscovering next
  session.
- Before running any `uefn` MCP tool against a project folder, remember only
  one UEFN editor can be connected to at a time — confirm the project open
  in the editor actually matches the folder being worked in.
