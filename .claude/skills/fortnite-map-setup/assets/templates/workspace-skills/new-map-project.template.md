---
name: new-map-project
description: Scaffolds a new UEFN/Fortnite map project subfolder in this fortnite-maps workspace — CLAUDE.md, brief.md, build-log.md, class-paths.md. Use whenever the user wants to start a new Fortnite/UEFN map project in this workspace, or asks for a place to keep notes/brief/build-log for a new map.
---

# New map project

This workspace holds one subfolder per UEFN map project — see this
workspace's own `CLAUDE.md` (one level up from `.claude/`) for the layout
convention. Scaffold new subfolders with `scripts/scaffold_project.py`, not
by hand-writing markdown — the templates in `assets/templates/` are the
source of truth for structure and wording, and the script is idempotent (it
skips files that already exist unless `--force`), so it's safe to re-run
later without clobbering notes already written into `brief.md` or
`build-log.md`.

```
python scripts/scaffold_project.py <project-name> [--project-root PATH] [--project-file PATH] [--force]
```

Run this with this skill's own directory as the working directory, or
invoke via an absolute path to `scaffold_project.py` — it resolves both the
workspace root and its own templates relative to itself, independent of
where the `uefn-mcp` checkout that originally generated this skill lives.

## Resolve the real UEFN location first

Before scaffolding, try to resolve the project's *real* UEFN location so
`CLAUDE.md` can point at it immediately instead of a placeholder:

- If the user gave a path, or one is discoverable, call the `uefn` MCP
  server's `find_uefn_projects` tool (optionally scoped with `search_paths`
  to keep it fast) to get the `project_root` and `project_file`.
- If the project is brand new and has never had remote execution enabled,
  `setup_uefn_project` does that one-time config edit — mention that UEFN
  needs restarting afterward for it to take effect.
- If the project can't be resolved yet (e.g. the user just wants to start
  planning before anything exists in UEFN), that's fine — proceed without
  `--project-root`/`--project-file`. The template records that it isn't
  linked yet, without blocking on it. Use the `load-map-project` skill to
  link it later once the location is known.

## Fill in the brief

After scaffolding, if the user has described what the map is for, use that
to fill in `brief.md`'s Goal/Layout/Devices sections right away with the
`Edit` tool rather than leaving it as bare headings — the template is a
skeleton, not a form for the user to fill in themselves later.
