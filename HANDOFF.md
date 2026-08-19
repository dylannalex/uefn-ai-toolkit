# Handoff — the plugin migration

For a session picking this up with no memory of the conversation that produced
it. Written 2026-08-18, immediately after the restructure.

**Delete this file once the "Do this first" list is done.** It describes a
migration, not a permanent state of the repository.

---

## The one-line status

The consolidation is **written, committed, pushed, installed, and exercised
against a live editor.** Every item on the "Do this first" list is done: all
nine tools pass against SkyWars (0b), `set_actor_transform` survived a real
UEFN restart, and two concurrent bridges against one editor work, which
retires fix 2 (0c).

**One check is left, and it needs a fresh session:** that the `uefn` MCP tools
appear in the tool list and the two skills are offered. 0b was run by calling
the tool functions directly, which is where the untested code was — the MCP
transport itself is generic and has never been the thing in doubt.

Since this was written: both repos were pushed on 2026-08-19, this repository
was renamed **`uefn-mcp` -> `uefn-ai-toolkit`** (repo, folder, plugin and
marketplace entry), and the plugin was installed at user scope from the GitHub
remote. The MCP server inside it is deliberately still `uefn-mcp` — see
CLAUDE.md. The commit table below still says `uefn-mcp`; same repo.

The two repositories live at `Root/repos/uefn-ai-toolkit` and
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

### 0a. Push, install, and find out what breaks — done 2026-08-19

The plugin is **installed and loading**. It was first installed at user scope
from the GitHub remote, which is how the failure below surfaced; it has since
been moved to the `fortnite-maps` workspace only — see 0a-bis. It did break
once, exactly as this list hoped: `claude plugin list` reported
`✘ failed to load` because `plugin.json` declared `"hooks": "./hooks/hooks.json"`,
a path the loader already picks up by convention — the manifest may only name
*additional* hook files. Dropping that one key fixed it; the plugin now reports
`✔ enabled`. **`claude plugin validate` does not catch this** — it passed clean
both before and after. `claude plugin list` is the check that matters.

1. ~~`git push` both repositories.~~ Done (`de9f141..6df0923`, `63dd01d..a2219fc`).
2. ~~`/plugin marketplace add dylannalex/uefn-ai-toolkit`~~ Done via
   `claude plugin marketplace add` — cloned over SSH, marketplace validated.
   `"source": "./"` (a repo acting as its own marketplace) **works against a
   real install**; that suspicion is closed.
3. ~~`/plugin install uefn-ai-toolkit@dylannalex-uefn`~~ Done (at the time, user
   scope; now project scope in `fortnite-maps`). Installing
   is not loading: it reported success while the plugin was still failing to
   load. Always follow an install with `claude plugin list`.
4. Verified directly against the installed cache, without waiting for a session:
   - `uv --directory <cache> run uefn-mcp` **resolves and bootstraps** — uv built
     the package and installed 39 deps into a `.venv` inside the plugin cache;
     `uefn-mcp.exe` exists, starts on stdio and exits 0 on EOF;
     `import uefn_mcp.server` succeeds; `tests/test_bridge.py` passes 4/4 there.
   - all 15 `../../docs/...` routes in `uefn-knowledge/SKILL.md` **resolve from
     the installed skill directory**. The mechanism the whole knowledge base
     depends on is sound.
   - `claude plugin validate .` passes clean (the missing
     `metadata.description` it warned about was added), and `claude plugin list`
     now reports the plugin `✔ enabled`.
5. ~~Workspace hook.~~ Run from the **installed** plugin path: the guard no-ops
   in an unrelated repo, and against `fortnite-maps` it mirrored 4 Verse files
   out of the UEFN project and regenerated the indexes with 0 changes —
   idempotent, `git status` clean afterwards.

**Left for a fresh session — the only two things a restart can show:** that the
`uefn` MCP tools appear in the tool list, and that
`/uefn-ai-toolkit:uefn-knowledge` and `/uefn-ai-toolkit:new-map-project` are
offered. Both are now low-risk: the plugin loads, the server runs and the
skill's paths resolve. One thing to glance at: `plugin.json` still declares
`mcpServers` and `skills`, both also conventional locations. They provoke no
error, but if the `uefn` tools ever show up **twice**, that is the first place
to look.

### 0a-bis. How this is installed while it is being developed

Not at user scope. The plugin is declared **only in the `fortnite-maps`
workspace**, and it reads **straight out of this working tree** — no copy, no
reinstall step, no push.

Three pieces, and the third is the one that is easy to lose:

1. `fortnite-maps/.claude/settings.json` (tracked) enables
   `uefn-ai-toolkit@dylannalex-uefn` from the **github** source. That is the
   portable declaration: it is what a fresh clone gets, and it is what will be
   right once this repo is pushed.
2. `fortnite-maps/.claude/settings.local.json` (gitignored) overrides the same
   marketplace name with `{"source": "directory", "path": "…/uefn-ai-toolkit"}`.
   Machine-specific, so it must never reach the tracked file — that is the whole
   reason the override lives in local scope.
3. `~/.claude/plugins/cache/dylannalex-uefn/uefn-ai-toolkit/0.2.0` is a
   **Windows junction to this repository**, not a directory:

   ```powershell
   $link = "$env:USERPROFILE\.claude\plugins\cache\dylannalex-uefn\uefn-ai-toolkit\0.2.0"
   Remove-Item -Recurse -Force $link
   New-Item -ItemType Junction -Path $link -Target "C:\Users\tinte\Root\repos\uefn-ai-toolkit"
   ```

**Why the junction, rather than a hook that re-syncs on every edit.** A
`directory` marketplace still *copies* into the cache, and neither
`claude plugin update` nor `claude plugin marketplace update` re-copies it —
both compare `version` in `plugin.json`, see 0.2.0 on each side and decline.
The only real re-sync is uninstall + install, which cannot run during a
session anyway: `uefn-mcp.exe` lives in the cache's `.venv` and a running
server holds it (`EACCES … rm`). The junction removes the copy, so there is
nothing to keep in sync and no hook to write.

**How an edit reaches a session.** Nothing on disk is ever stale, so the only
question is when Claude Code re-reads it. `docs/` is immediate and needs no
restart — the knowledge skill opens the file at the moment it routes there.
`skills/`, `hooks/hooks.json` and `.mcp.json` are read at session start.
`src/uefn_mcp/` is also just a restart: the venv holds the package
**editable** (a `.pth` pointing at `src/`), and `uv run` rebuilds by itself
when it needs to — it silently repaired a `.pth` still aimed at the
pre-rename `repos/uefn-mcp/src`. Restarting the session is the whole update
mechanism; there is no install step.

**What breaks it:** any `claude plugin install` / `update` for this plugin
replaces the junction with a fresh copy. Symptom — edits stop showing up in a
new session. Fix — re-run the two lines above.

Note the trap that leads there: **bumping `version` in `plugin.json` is what
arms `claude plugin update`.** The bump alone is harmless — the loader
resolves by `installPath`, so `claude plugin list` keeps reporting 0.2.0 and
keeps loading. But a later `update` then sees a genuinely newer version,
reinstalls, and the junction is gone.

**Before publishing:** push, delete `settings.local.json`, and reinstall
normally. The tracked `settings.json` is already in the published shape.

### 0b. Every tool exercised against a live editor — done 2026-08-19

All nine ran against SkyWars (598 actors) and all nine pass. The warning this
section carried — "expect at least one wrong property name" — **did not come
true**; no tool needed a fix.

| Tool | Result |
| --- | --- |
| `save_level` | ✓ and against a genuinely dirty level: 1 → 0, not just 0 → 0 |
| `validate_level` | ✓ **4.5 s for 598 actors, 0 invalid.** The timeout fear was unfounded; no batching needed |
| `screenshot_level` | ✓ real PNG (`89 50 4e 47`), correct exposure — the image was looked at, not just its header |
| `list_verse_editables` | ✓ 10 `__verse_0x…` fields on `PersonalDripManager` |
| `set_verse_editable` | ✓ `DripInterval` written and read back |
| `set_item_spawner_content` | ✓ on a duplicate |
| `spawn_verse_device` | ✓ `script_class` came back `/SkyWars/_Verse.personal_drip_manager` |
| `add_verse_tag` | ✓ and **idempotent** — re-applying the same tag does not duplicate it |
| `set_actor_transform` | ✓ **survived a UEFN restart exactly** (`x=1234, y=-5678, z=21000, yaw=42`) |

`set_actor_transform` is the one that mattered, and it is the one now actually
proven: the values were written, saved, UEFN was closed and reopened, and they
came back unchanged. That is the test a same-session readback cannot give.

Two calls failed on the way and neither was the tool's fault — a `Vec3` passed
as a list rather than a `{"x","y","z"}` dict, and an attempt to spawn
`skywars_tags`, which holds `tag` classes and not a `creative_device`. Both
errors said precisely that. Worth knowing that the error messages are good
enough to debug from.

The `handles[0]` assumption in `add_verse_tag`, flagged below as unverified,
held on a `Device_ItemSpawner_V3_C` — a different actor class from the recipe
it came from. Evidence, not proof.

Both probe actors were deleted and the level saved; `get_editor_status` reads
598 again.

### 0c. The bridge fix measured — fix 2 is not needed

**One UEFN editor accepts two command connections at once.** Two independent
processes, each with its own `UEFNBridge` on its own reserved port — which is
what two Claude Code sessions are — ran three interleaved `get_editor_status`
calls each, concurrently, and all six succeeded.

By this section's own rule, that settles it: **fix 1 alone gives full
multi-session support, and fix 2 (open/close the command connection per call)
is waste.** Do not implement it.

The port-collision fix is what made this work: Epic's client defaults every
process to 6776 with `SO_REUSEADDR`, so before it, two sessions fought over
one port until both died. Each bridge now reserves its own.

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
- **`add_verse_tag` assumes `handles[0]` is the root subobject** — held on a
  second actor class (`Device_ItemSpawner_V3_C`) in 0b, so no longer a guess,
  but still not established as a general rule.
- **`validate_level` has no batching, and does not need it** — 4.5 s for 598
  actors. Revisit only if a level gets far larger.
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
