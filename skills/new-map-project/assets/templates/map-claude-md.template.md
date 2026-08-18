# CLAUDE.md — {{PROJECT_NAME}}

Scaffolded {{DATE_CREATED}}.

## UEFN project location

- **project_root**: `{{PROJECT_ROOT}}`
- **.uefnproject file**: `{{PROJECT_FILE}}`

## Before running any `uefn` tool against this map

Confirm the editor currently open in UEFN is *this* project — only one editor
can be connected at a time, and discovery connects to whichever one it finds.
Compare `get_editor_status`'s reported project against `project_root` above.
Working here while a different project is open runs commands against the
wrong map.

## What goes where

| Directory | Contract |
| --- | --- |
| `docs/` | **Permanent.** What this map is: goal, design, layout, mechanics. Changes rarely. |
| `state/` | **Current truth.** Rewritten in place, never grows. What is built, what is verified, what judgements stand. |
| `pending_work/` | **Ephemeral.** One file per unfinished piece of work, including session handoffs. **Delete the file when the work is done** and record it in `build-log/`. |
| `build-log/` | **Append-only.** One file per session. Never read start to finish — go through `INDEX.md` and open only what's relevant. |
| `knowledge/` | **Buffer.** Fortnite facts discovered here that belong in the `uefn-mcp` plugin, staged for migration. |
| `verse/` | **Generated mirror** of the Verse source in the UEFN project. Read-only — edit the original, never this copy. |

Nothing belongs in two of them. If something feels like it fits in both
`state/` and `pending_work/`, it is current truth with an unfinished piece:
state it once in `state/` and put the work in `pending_work/`.

## Conventions for this map

<!-- Fill in as they're established, e.g.: -->
<!-- - Actor naming: prefix gameplay actors with the area they belong to (`Spawn_`, `Boss_`). -->
<!-- - Grid/coordinate convention: 100uu = one build grid square; origin is the spawn pad. -->
