# Handoff — the plugin migration

For a session picking this up with no memory of the conversation that produced
it. Written 2026-08-18, immediately after the restructure.

**Delete this file once the "Do this first" list is done.** It describes a
migration, not a permanent state of the repository.

---

## The one-line status

The consolidation is **written, committed and pushed in both repositories,
and verified only as far as it can be without a running UEFN editor and an
installed plugin.** Nothing is installed. No new tool has ever executed
against a live editor.

Since this was written: both repos were pushed on 2026-08-19, and this
repository was renamed **`uefn-mcp` -> `uefn-ai-toolkit`** (repo, plugin and
marketplace entry). The MCP server inside it is deliberately still `uefn-mcp`
— see CLAUDE.md. The commit table below still says `uefn-mcp`; same repo.

The two repositories live at `Root/repos/uefn-mcp` (the local folder still
carries the old name; the remote is `dylannalex/uefn-ai-toolkit`) and
`Root/repos/personal/fortnite-maps` — not side by side.

## What changed, and why

Two repositories that were one tangle are now framework and content.

**`uefn-mcp`** became a Claude Code plugin: MCP server + skills + knowledge
base, installed once at user scope, **copied into nothing**. Previously a
`fortnite-map-setup` skill copied its skills and templates into each notes
workspace, and every copy was a fork — the installed ones had already drifted
from their templates after a single project.

**`fortnite-maps`** is now content only. Five notes files that had each
drifted from their declared contract were replaced by directories that each
answer one question: `docs/` (what the map is), `state/` (what is true now,
rewritten), `pending_work/` (unfinished, deleted from when it finishes),
`build-log/` (append-only, one file per session), `verse/` (generated mirror),
`knowledge/` (Fortnite facts staged for migration into the plugin).

Commits, newest last:

| Repo | Commit | What |
| --- | --- | --- |
| uefn-mcp | `ea2666f` | `line_trace_multi` gotchas (pre-existing, uncommitted) |
| uefn-mcp | `19f2263` | Plugin + marketplace manifests |
| uefn-mcp | `8bad26b` | docs/ reorganised; INDEX.md generated from frontmatter |
| uefn-mcp | `314d65d` | `fortnite-map-setup` replaced by `new-map-project` |
| uefn-mcp | `92b5953` | **Bridge: one command port per process** |
| uefn-mcp | `a36ebea` | **8 tools added or fixed** |
| uefn-mcp | `6f640ac` | CLAUDE.md / README / internals rewritten for the plugin |
| uefn-mcp | `854e298` | Asset roster migrated out of SkyWars |
| uefn-mcp | `83c282b` | reindex heading fix |
| uefn-mcp | `12e3fec` | Verse mirror + workspace hook |
| fortnite-maps | `a2219fc` | The whole content restructure |

---

## 0. Do this first

### 0a. Push, install, and find out what breaks

Nothing here has been exercised by Claude Code itself. The manifests are
schema-valid JSON and that is **all** that has been checked.

1. ~~`git push` both repositories.~~ Done 2026-08-19 (`de9f141..6df0923`,
   `63dd01d..a2219fc`).
2. `/plugin marketplace add dylannalex/uefn-ai-toolkit`
3. `/plugin install uefn-ai-toolkit@dylannalex-uefn`
4. Start a **new session** (MCP servers only connect at session start) and
   confirm, in order:
   - the `uefn` tools are listed — i.e. `.mcp.json`'s
     `uv --directory ${CLAUDE_PLUGIN_ROOT} run uefn-mcp` actually resolves and
     `uv run` bootstraps its dependencies inside the plugin cache;
   - `/uefn-ai-toolkit:uefn-knowledge` loads, **and the relative paths in its body
     resolve** — it routes with `../../docs/...` from the skill's own
     directory, which is the mechanism the whole knowledge base depends on and
     has never been tried;
   - `/uefn-ai-toolkit:new-map-project` is offered.
5. Open a session in `fortnite-maps`, edit any markdown file, and check the
   `PostToolUse` hook fired: `scripts/workspace_hook.py` should re-mirror the
   Verse source and regenerate the indexes. It has only ever been run by hand
   with `CLAUDE_PROJECT_DIR` set manually.

If the plugin does not load, suspect `.claude-plugin/marketplace.json`'s
`"source": "./"` first — a repository acting as both marketplace and plugin is
documented but was not verified against a real install.

### 0b. Exercise every new tool against a live editor — none has ever run

This is the largest untested surface. All eight were written from the recipes
in `docs/`, which are themselves grounded in real sessions, but **the tool code
itself has executed exactly zero times.** Expect at least one wrong property
name.

Open UEFN with SkyWars loaded and run them in this order, cheapest first:

| Tool | What to check |
| --- | --- |
| `save_level` | Returns `dirty_packages_before` / `_after`; after should be 0 |
| `validate_level` | On 598 actors. **Watch for a timeout** — it loops every actor calling `is_object_valid`, and nobody has measured how long that takes. If it hangs, that is the first thing to fix |
| `screenshot_level` | Writes a real PNG (first bytes `89 50 4e 47`, not OpenEXR's `76 2f 31 01`) |
| `list_verse_editables` | Against `PersonalDripManager`; should return `__verse_0x…` names |
| `set_verse_editable` | A scalar, e.g. the drip interval; read it back |
| `set_item_spawner_content` | Against **one duplicate**, never a live chest |
| `spawn_verse_device` | Spawn, confirm the `Script` sub-object's class, then delete |
| `add_verse_tag` | On a throwaway actor first — it mutates a component list |
| `set_actor_transform` | **Last, and on a throwaway actor.** Then restart UEFN and confirm the move survived. That is the only real test of the fix |

`set_actor_transform` is the one that matters: it was the broken tool, its
whole point is surviving a restart, and a readback in the same session proves
nothing — that is exactly the trap that lost 19 island moves originally.

### 0c. Measure the bridge fix, then decide about fix 2

The port collision was fixed (each bridge reserves its own free port). **Fix 2
— opening and closing the command connection per call — was deliberately not
done**, because it depends on a fact nobody has: whether the UEFN editor
accepts more than one command connection at a time. That cannot be seen from
this side of the socket.

The measurement is ten minutes: open two Claude Code sessions against one
editor and run `get_editor_status` in both.

- Both work → fix 1 alone gives full multi-session support; fix 2 is waste.
- One fails → implement fix 2 (`open_command_connection` / `run_command` /
  `close_command_connection` per call, keeping UDP discovery open, which is
  not contended — its socket sets `SO_REUSEADDR` on a multicast group
  legitimately).

---

## Decisions already settled — do not re-litigate

These came out of a long design interview. Reopening them wastes a session.

| Decision | Settled as |
| --- | --- |
| Audience | **Public distribution.** Framework and content separated structurally for that reason |
| Repo topology | **One repo = the plugin.** Not a separate pip package for the server; that only helps non-Claude-Code MCP clients, which is a one-day migration if anyone asks |
| Content granularity | **One repo, N maps** — chosen for convenience, not reuse. The consequence is that the "is the right project open in UEFN?" check is mandatory, and lives in each map's `CLAUDE.md` |
| Concurrency | **One map, one session** as the declared policy; `state/` partitioned by topic so sessions touching different topics don't collide. **No `.lock` file** — it would block the benign case (one building, one planning) and not the harmful one |
| Knowledge format | **Markdown tables partitioned by category**, not YAML + a query tool. Revisit only if the roster gets big enough that reading hurts |
| Invalid assets | **Same table as the valid ones**, with a verdict column. Knowing a route is dead is worth what it cost to establish |
| INDEX.md | **Generated, never hand-written.** File → description only. Every markdown file needs `description:` frontmatter or it indexes as `—` |
| `.verse` | **One-way mirror**, UEFN project → repo. Never written back |
| Recipes → tools | **Yes, for anything with one correct form.** If a doc says "always remember to X", X belongs in the tool |

---

## Known sharp edges

- **`scripts/reindex.py` will happily index anything you point it at.** Run it
  on the plugin root and it generates junk `INDEX.md` files under `skills/` and
  the templates — this happened once during the migration. In the plugin, only
  ever run it on `docs/`. The *hook* is guarded (it no-ops unless the project
  root already holds a generated `INDEX.md`); manual runs are not.
- **The `verse/INDEX.md` is written by `sync_verse.py`, not `reindex.py`.**
  Two generators, two files, both claiming to be generated. They don't
  currently collide (reindex skips directories with no non-INDEX `.md`), but
  it is a thin margin.
- **`add_verse_tag` assumes `handles[0]` is the root subobject** — true in the
  recipe it came from, unverified as a general rule.
- **`validate_level` has no batching.** See the timeout note above.
- **CRLF warnings on every commit.** Cosmetic; no `.gitattributes` was added
  because that is a change to how every file in both repositories is stored
  and was not part of this work.

## Still open on SkyWars itself

Untouched by this migration, and already in the right place —
`fortnite-maps/SkyWars/pending_work/`: the starter kit's 36 devices, the storm
that never shrinks, the wood cap, four systems that have never executed in a
match, and the island undersides nobody has seen in a live session.

The one thing to know before touching any of it: **the map's Verse fix for
`PlayerAddedEvent` is written into the source and has never been compiled.**
Compiling is a manual click in UEFN with no scriptable trigger.
