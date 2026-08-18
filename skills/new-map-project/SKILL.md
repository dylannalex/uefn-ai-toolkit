---
name: new-map-project
description: Scaffolds a UEFN/Fortnite map project folder in a content workspace — CLAUDE.md, docs/ (design), state/ (current truth), pending_work/, build-log/, knowledge/, verse/, and a generated INDEX.md in each. Use whenever the user wants to start a new Fortnite/UEFN map, or asks for somewhere to keep the brief, build log and notes for one.
---

# New map project

A map's notes live in a **content workspace** — a plain git repository, one
folder per map, holding no framework files at all. This plugin supplies the
skills, scripts and knowledge base; nothing is copied into the workspace.

## 1. Find or create the workspace

Look for an existing content workspace before creating one: a directory whose
`CLAUDE.md` first heading matches `CLAUDE.md — <name>` and which describes
itself as content rather than framework. Check next to the current working
directory and anywhere the user has mentioned before.

If there is none, this is a new directory outside the current project — ask
the user where it should go rather than deciding silently.

## 2. Resolve the real UEFN location first

So the map's `CLAUDE.md` points at the project immediately instead of a
placeholder:

- Call `find_uefn_projects` (scope it with `search_paths` to keep it fast) to
  get `project_root` and `project_file`.
- If the project has never had remote execution enabled, `setup_uefn_project`
  does that one-time config edit — say that UEFN must be restarted afterward.
- If nothing exists in UEFN yet, scaffold anyway without those flags. The
  template records that it isn't linked, and the path can be filled in later
  by editing `CLAUDE.md` directly — never by re-running the scaffold, which
  would discard notes already written.

## 3. Scaffold

```
python scripts/scaffold_project.py <workspace-dir> <map-name> [--project-root PATH] [--project-file PATH] [--force]
```

Invoke it by absolute path; it locates its templates and the plugin's
`reindex.py` relative to itself. It is idempotent — existing files are left
alone unless `--force` — and it regenerates every `INDEX.md` when it finishes.

## 4. Fill in the design

If the user has described what the map is for, write `docs/overview.md` now
with the `Edit` tool rather than leaving the skeleton — the templates are a
starting shape, not a form for the user to fill in later. Leave `layout.md`,
`loot-and-resources.md` and `mechanics.md` skeletal until there is real
content for them.

## While working on a map

- **`state/` is rewritten, `build-log/` is appended, `pending_work/` is
  deleted from.** When a piece of pending work is finished, delete its file
  and record what happened in a `build-log/` entry. A finished item left in
  `pending_work/` is the failure mode this structure exists to prevent.
- **Never hand-edit an `INDEX.md`** — run `scripts/reindex.py` on the
  workspace instead. Every markdown file needs a `description:` in its
  frontmatter or it will index as `—`.
- **Fortnite facts go in `knowledge/`, not the map's notes.** The test: would
  this still be true if the map were deleted? Validated asset paths, platform
  walls and ruled-out dead ends are framework knowledge staged for migration
  into this plugin. Actor labels, coordinates and taste are the map's.
