# Handoff — 2026-08-19

For a session picking this up with no memory of the one that produced it.
Replaces the migration handoff, whose "do this first" list is done.

**Delete this file once its "Do this first" list is done.** It is a handoff,
not a permanent description of the repository.

---

## Status

The plugin migration is finished and **verified against a live editor**. All
23 tools work, the plugin loads, and SkyWars gained its 36 starter-kit
spawners. Nothing is half-applied; both repos are pushed and clean.

Two repositories, not side by side:

- `Root/repos/uefn-ai-toolkit` — the plugin (`main`, pushed through `b87f813`)
- `Root/repos/personal/fortnite-maps` — the content (`master`, pushed through
  `e40264d`; note the branch is `master`, not `main`)

---

## 0. Do this first

### 0a. Confirm the plugin actually loads in this session

One check never got made, because it needs a session that started *after* the
install. Everything else was verified directly.

- Are the `uefn` MCP tools in your tool list?
- Are `/uefn-ai-toolkit:uefn-knowledge` and `/uefn-ai-toolkit:new-map-project`
  offered?

`claude plugin list` from inside `fortnite-maps` reports it **enabled, project
scope, 0.2.0** (checked 2026-08-19 from the toolkit repo). That proves the
install, not the load: a session started in `fortnite-maps` still has to see
the tools and skills, because this one runs in the toolkit repo, where the
plugin is deliberately not declared and correctly absent.

If either is missing, run `claude plugin list` from inside `fortnite-maps`.
**That is the only command that reveals whether a plugin loads.** `claude
plugin validate` passed cleanly on a manifest that was failing to load, and
the install reported success at the same time.

Everything else about the install is proven: the marketplace clones and
validates, `uv` bootstraps the server inside the plugin cache, the console
script starts, the self-check passes there, and all 15 `../../docs/...` routes
in `uefn-knowledge/SKILL.md` resolve from the installed skill directory.

### 0b. The bridge's eleven-minute silence — fixed, needs one live check

The silence was Epic's client setting **no receive timeout at all**: a GPU
crash leaves UEFN.exe alive holding the socket, so `recv()` blocked for as long
as that process lingered. `bridge.py` now sets `COMMAND_TIMEOUT` (120 s,
`UEFN_MCP_COMMAND_TIMEOUT` to override) on the channel socket after the
handshake, and on expiry raises `UEFNConnectionError` **without retrying the
command** — it may already have taken effect, and re-running a create or a
transform duplicates work. Resume from the per-step log instead.
`tests/test_bridge.py` covers both halves; `python tests/test_bridge.py` passes.

**Not yet exercised against a live editor** — UEFN was not running. Two things
to watch when it next is:

- a normal call still returns (the `settimeout` reaches the real socket — the
  test only proves the two vendored attribute names still exist);
- `build_verse_code` still compiles. The editor stops answering during a
  compile, which now surfaces as a timeout after 120 s instead of a long block.
  Its poll loop swallows that and reconnects, but if a compile on this machine
  outlasts 120 s the cost is a needless reconnect per poll — raise the env var.

### 0c. Then: SkyWars needs a real match

Everything left on the map is blocked on the same thing — **four systems have
never executed in a live session.** `pending_work/verify-in-a-match.md` is the
file; it lists what to look for.

`PersonalDripManager`'s `PlayerAddedEvent` fix is now **compiled** (it was not
before), so that one is finally testable. `GlobalSpawnAlternator` is suspected
dead for a related reason — it subscribes to the Timer's `SuccessEvent` but
never calls `Start()`.

The other three fronts in `pending_work/` (the storm that never shrinks, the
island undersides, the loose threads) do not depend on a match.

---

## How this is installed — do not break it by accident

The plugin is declared **only in `fortnite-maps`**, at project scope, and it
reads **straight out of this working tree**. Three pieces:

1. `fortnite-maps/.claude/settings.json` (tracked) enables the plugin from its
   **github** source. That is the portable declaration a fresh clone gets.
2. `fortnite-maps/.claude/settings.local.json` (gitignored) overrides the same
   marketplace with a `directory` source pointing here. Machine-specific — it
   must never reach the tracked file.
3. `~/.claude/plugins/cache/dylannalex-uefn/uefn-ai-toolkit/0.2.0` is a
   **Windows junction to this repository**, not a directory:

   ```powershell
   $link = "$env:USERPROFILE\.claude\plugins\cache\dylannalex-uefn\uefn-ai-toolkit\0.2.0"
   Remove-Item -Recurse -Force $link
   New-Item -ItemType Junction -Path $link -Target "C:\Users\tinte\Root\repos\uefn-ai-toolkit"
   ```

**Why a junction rather than a hook that re-syncs.** A `directory` marketplace
still *copies* into the cache, and neither `claude plugin update` nor
`claude plugin marketplace update` re-copies it — both compare `version` in
`plugin.json`, see the same number on each side and decline. The only real
re-sync is uninstall + install, which cannot run during a session anyway:
`uefn-mcp.exe` lives in the cache's `.venv` and a running server holds it
(`EACCES … rm`). Removing the copy removes the problem.

**How an edit reaches a session.** `docs/` is immediate — the knowledge skill
opens the file when it routes there. `skills/`, `hooks/hooks.json`, `.mcp.json`
and `src/uefn_mcp/` are all read at session start; the venv holds the package
editable, so a restart is the whole update mechanism. There is no install step.

**What breaks it:** any `claude plugin install` / `update` for this plugin
replaces the junction with a copy, and edits silently stop arriving. Note the
trap that leads there — **bumping `version` in `plugin.json` is what arms
`claude plugin update`.** The bump alone is harmless (the loader resolves by
`installPath`), but a later update then has something newer to install.

**Before publishing:** push, delete `settings.local.json`, reinstall normally.

---

## What this session established — do not re-derive it

| Question | Answer, and how it was established |
| --- | --- |
| Does one editor accept two command connections? | **Yes.** Two processes, own ports, interleaved calls, all succeeded. So the port-per-process fix alone gives multi-session support and "fix 2" (open/close per call) is waste — do not implement it |
| Is `validate_level` too slow to use? | **No.** 4.5 s over 598 actors, 0 invalid |
| Can Verse be compiled without a person? | **Yes**, via `build_verse_code`. The API really has no build trigger, but the keyboard shortcut is a public gesture. Proven both ways: a class appeared after a build and disappeared after its declaration was removed and the build re-run |
| What is a call's latency? | **~330 ms, flat** regardless of payload. The actor lookup's linear scan over 598 actors is irrelevant. The cost of a big job is model turns, not editor time |
| Are namespaced device options writable? | **No known path.** ~74 of `IslandSettings0`'s ~298 keys are `Mutator:Property`, live on a sub-object, and `get_editor_property` cannot see them. Their values are readable from the bulk map; `set_device_options` reports them `settable: false` |

---

## Standing hazards

- **Bulk actor creation crashes this map's editor.** Three occurrences now
  (session 11, twice on 2026-08-19). `GPU Crash dump Triggered`, callstack pure
  `ntdll` — the GPU going down, not a script fault, so no care with `unreal.*`
  avoids it. **Finish and save one actor at a time**, ordering the calls so the
  saving one is last: with `set_actor_transform(save=True)` at the end of an
  actor's pipeline, the save covers the content and tag set just before it.
  Batching saves is the obvious optimisation and the wrong trade here.
- **Log before each step of a long run, not after**, and flush. A crash
  mid-call leaves the bridge retrying in silence (0b), and a line already
  written is the only way to know where it stopped.
- **`scripts/reindex.py` will index anything you point it at.** In the plugin,
  only ever run it on `docs/`. The *hook* is guarded; manual runs are not.
- **`verse/INDEX.md` is written by `sync_verse.py`, not `reindex.py`.** Two
  generators, two files, both claiming to be generated. They don't currently
  collide, but it is a thin margin.
- **`add_verse_tag` assumes `handles[0]` is the root subobject** — held on a
  second actor class, so no longer a guess, but not established as a rule.
- **An absolute actor count in a notes file rots.** The starter-kit plan
  expected 631 from a 595-actor baseline; the level had reached 598, so 634 was
  correct. Write the delta, not the total.
- **CRLF warnings on every commit.** Cosmetic; no `.gitattributes` was added
  because that changes how every file in both repositories is stored.

---

## Decisions already settled — do not re-litigate

| Decision | Settled as |
| --- | --- |
| Audience | **Public distribution.** Framework and content separated structurally for that reason |
| Repo topology | **One repo = the plugin.** Not a separate pip package for the server; that only helps non-Claude-Code MCP clients, a one-day migration if anyone asks |
| Plugin scope | **Project scope, `fortnite-maps` only.** Deliberately not user scope — it should not load in unrelated projects |
| Content granularity | **One repo, N maps.** The consequence is that the "is the right project open in UEFN?" check is mandatory, and lives in each map's `CLAUDE.md` |
| Concurrency | **One map, one session** as policy; `state/` partitioned by topic. **No `.lock` file** — it would block the benign case and not the harmful one |
| Knowledge format | **Markdown tables partitioned by category**, not YAML + a query tool |
| Invalid assets | **Same table as the valid ones**, with a verdict column. Knowing a route is dead is worth what it cost to establish |
| INDEX.md | **Generated, never hand-written.** Every markdown file needs `description:` frontmatter or it indexes as `—` |
| `.verse` | **One-way mirror**, UEFN project → repo. Never written back. Fix the source in the UEFN project and re-run the mirror; editing `verse/` is overwritten |
| Recipes → tools | **Yes, for anything with one correct form.** If a doc says "always remember to X", X belongs in the tool |
| The server's name | The plugin is `uefn-ai-toolkit`; the MCP server inside it stays `uefn-mcp` (package `uefn_mcp`, `uefn-mcp.exe`). Deliberate. Don't "fix" it |

---

## Optimisations found but not built

From an evidence pass over sixteen build-logs. Ranked; the top two were built,
these were not. **Nothing here is urgent** — each is worth doing when a real
task asks for it, which is how the shape gets decided correctly.

- **A line-trace tool.** `set_actor_transform`'s own docstring says to verify
  geometry with a line trace and never with bounds — and there is no line-trace
  tool. `line_trace_multi` has two documented crash modes (returns the hit
  array, not the `(bool, hits)` tuple its signature suggests; returns `None`,
  not an empty array, on a miss) which already broke a real placement run in
  session 14. Textbook case for the recipes-to-tools rule.
- **Plural forms of the label-taking tools.** The 36-spawner job was 144 calls.
  Editor time was fine; the cost is model turns and context. Driving the tools
  from one Python process worked well and is the cheap answer, but a genuine
  batch form would be better. Whatever it looks like, it must not lose
  `set_actor_transform`'s modify/teleport/nudge — reimplementing tool bodies in
  a batch script is exactly how those fixes get dropped.
- **`list_content_assets` returns registry hits with no load check**, and has
  no name filter, while the docs insist a registry hit is not enough — session
  8 lost time to exactly that with `WID_Shotgun_SemiAuto_Athena_C`. Two
  parameters (`name_contains`, `verify_load`) would close it.

**Not worth pursuing**, so nobody re-investigates: item content on Item Granter
and Class Designer is a real platform wall confirmed from two angles, not a
missing wrapper.
