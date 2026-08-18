# Miscellaneous gotchas

Smaller findings that don't need their own file. Add to this file for a new
one-off finding; split it out once it grows past a page.

## Spawning a basic-shape mesh (Cube, Cylinder, ...) is not "spawn this class"

`/Engine/BasicShapes/Cube` etc. are **static mesh assets**, not actor
classes — `spawn_actor`/`EditorActorSubsystem.spawn_actor_from_class` with
that path as the class fails with `ActorClass is not valid`. Spawn a plain
`unreal.StaticMeshActor` instead, then assign the mesh:

```python
mesh = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
actor.get_components_by_class(unreal.StaticMeshComponent)[0].set_static_mesh(mesh)
```

## Stale `uefn-mcp.exe` processes cause a silent connection failure

If `get_editor_status` (or any tool) fails with `Remote party failed to
attempt the command socket connection!` even though UEFN is running with
Python Scripting + remote execution both correctly enabled for the right
project — check for **multiple `uefn-mcp.exe` processes** running at once
before assuming a config/project problem
(`tasklist | grep uefn-mcp` on Windows). Observed 4 simultaneous instances
in one session, apparently from prior reconnects that didn't exit cleanly;
they conflict over the remote-execution multicast port. Killing all of them
and retrying immediately fixed the connection — a fresh bridge process
starts automatically on the next tool call. Worth investigating on the
server side whether `bridge.py`'s reconnect-on-stale-connection logic
should also be killing/replacing the OS process rather than just the
in-process connection object, since this seems likely to recur for anyone
reconnecting across multiple sessions.

## `unreal.Rotator(a, b, c)` positional args are `(roll, pitch, yaw)`, not `(pitch, yaw, roll)`

Easy trap, confirmed by constructing one and reading it back:

```python
>>> unreal.Rotator(10.0, 20.0, 30.0).to_dict()
{'roll': 10.0, 'pitch': 20.0, 'yaw': 30.0}
```

Writing `unreal.Rotator(0.0, some_yaw, 0.0)` intending "pitch 0, yaw
some_yaw, roll 0" actually sets **pitch** to `some_yaw` and leaves yaw at
`0` — the value lands in the wrong axis entirely, not just relabeled.
Symptom in practice (SkyWars, session 10): trees/foliage props spawned
with a randomized "yaw" for natural variation all came out tipped over at
random angles instead of standing upright, since the random value was
being applied as pitch. Always pass rotation components as keyword args
(`unreal.Rotator(roll=0.0, pitch=0.0, yaw=some_yaw)`) to avoid relying on
positional order.

## `StaticMeshComponent.set_material(index, mat)` doesn't reliably survive `save_level` — use `set_editor_property("override_materials", [...])`

`comp.set_material(0, mat)` reads back correctly immediately after
calling it (and even passes `EditorValidatorSubsystem.is_object_valid`),
but was found **not actually persisted** after a `save_level` call
followed by later work in the same session (SkyWars, session 10) — a
later readback showed `override_materials` back to `[]` and
`get_material(0)` back to the engine default material, with no error at
any step. The reliable path, consistent with how every other
editor-time property in this project gets set:

```python
comp.set_editor_property("override_materials", [mat])
```

Verified this one *does* survive — readback matched immediately and after
a subsequent `save_level`. Root cause not confirmed (plausibly
`set_material` not routing through the same dirty-marking/property-changed
notification path that `set_editor_property` does, so `save_level` writes
a version of the package that predates the change) — but the practical
rule either way: **prefer `set_editor_property` over type-specific setter
methods** (`set_material`, possibly others) for anything that needs to
survive a save, even when the setter's own immediate readback looks fine.
`set_actor_rotation`/`set_actor_scale3d` were not observed to have this
problem (their changes did survive), so this isn't a blanket rule for
every setter method — but it's now a specific, confirmed exception to add
to the "always suspect setter methods across a save" list.

## A Creative device is a Blueprint, not the native class it wraps — and not every device lives in `/CreativeCoreDevices`

Placing `/Script/FortniteGame.FortPlayerStartCreative` gives you an actor that
*looks* like a Player Spawn Pad and reads back sensible properties, but Island
Settings' `SpawnLocation = SPAWN_PADS` never sees it, because that setting
enumerates the **device Blueprint**, not the base class. The real device is
`/CRD_PlayerSpawn/BP_Creative_Player_Spawner_Prop.BP_Creative_Player_Spawner_Prop_C`
— and it **spawns a `FortPlayerStartCreative` child actor of its own**, which
is the giveaway: the native actor is a *component* of the device.

Cost in SkyWars: 13 sessions with no working spawn points, players dropped
above the world origin every match, and two wrong fixes aimed at Island
Settings before the class itself was suspected.

Two habits that shorten this:

- **Diff a suspicious actor against its class CDO**
  (`unreal.get_default_object(cls)`) before theorising about its properties.
  In this case `ApplicableTeam = 1` and `PriorityGroup = 2147483647` looked
  like smoking guns and were simply the class defaults — that comparison
  redirected the search to the class itself.
- **Search the whole asset registry, not one device folder.** `reg.get_all_assets()`
  filtered by a name regex found `/CRD_PlayerSpawn/` immediately; every earlier
  search had looked only under `/CreativeCoreDevices`, which holds many devices
  but not all — several ship in their own `/CRD_*` roots, with a matching
  `PID_Device_*` item definition and `_Verse` type alongside them.

## `is_object_valid` returns a tuple, not a `DataValidationResult`

In UE 5.8 (Fortnite Release-41.30),
`EditorValidatorSubsystem.is_object_valid(obj, usecase)` returns a
**3-tuple** `(DataValidationResult, warnings, errors)` — not the bare enum
the name suggests. Comparing the return value directly reports **every**
actor as invalid, because a tuple never equals an enum member:

```python
r = ev.is_object_valid(a, unreal.DataValidationUsecase.MANUAL)
if r != unreal.DataValidationResult.VALID:   # WRONG - always true
if r[0] != unreal.DataValidationResult.VALID or list(r[2]):   # right
```

Caught in SkyWars session 13, where the broken form flagged all 557 actors
in a clean level. The failure is loud rather than silent (you get an
implausible 100% failure rate), but it costs a debugging round if the
project has a real history of validation problems — as this one did. The
two extra elements are `unreal.Array` objects of message tokens; treat a
non-empty `r[2]` as authoritative for errors and `r[1]` as warnings.

## `line_trace_multi` returns the hit array directly — and `None` when nothing is hit

`unreal.SystemLibrary.line_trace_multi(...)` does **not** return the
`(bool, out_hits)` tuple the Blueprint node's signature suggests. It returns
the `HitResult` **array itself**, so the idiomatic `hits[1]` raises
`IndexError: Array: Index 1 is out-of-bounds`. Worse, when the ray hits
nothing it returns **`None`**, not an empty array, so a bare `for h in hits:`
raises `TypeError: 'NoneType' object is not iterable`. Both forms crashed a
prop-placement run in SkyWars session 14 — the second one only once sampling
started reaching past an island's edge, i.e. well after the code looked
correct. Always:

```python
hits = unreal.SystemLibrary.line_trace_multi(
    world, start, end, unreal.TraceTypeQuery.ECC_VISIBILITY, True,
    ignore_actors, unreal.DrawDebugTrace.NONE, True)
for h in (hits or []):
    t = h.to_tuple()          # 4 = impact location, 9 = hit actor, 10 = component
```

(`TraceTypeQuery.TRACE_TYPE_QUERY1` still works but is deprecated in 5.8 in
favour of `ECC_VISIBILITY`.)

## A "multi" trace still stops at the first blocking hit — ignore everything but the terrain

`line_trace_multi` returns every hit *up to and including* the first blocking
one; it does not see through solid geometry. So a downward ray meant to sample
**ground height** lands on whatever prop happens to be in the way and never
reaches the terrain. The symptom is misleading rather than loud: a radial sweep
reports ground "missing" over a large fraction of an island that is in fact
completely solid — in SkyWars session 14, 40% of sample points, purely because
foliage was in the way.

The fix is to pass everything that is *not* terrain in the ignore list, then
pick the topmost remaining hit:

```python
ignore = [a for a in eas.get_all_level_actors()
          if not a.get_actor_label().startswith("Central_Body")]   # terrain prefix
```

This is the same warning as "pass the props array in the trace ignore list when
seating anything", but it bites a step earlier — it applies to *finding* the
ground, not just to sitting an actor on it.

## Taking a real screenshot of the level from Python — SUPERSEDED

**Read [`../how-to-screenshot-the-level.md`](../how-to-screenshot-the-level.md)
instead.** `SceneCapture2D` works reliably and synchronously; the section below
describes two APIs (`take_high_res_screenshot` and the `HighResShot` console
command) that were later confirmed to be dead ends, after four sessions were
lost to them. It is kept only so nobody re-tries them.

### Original note (do not act on this)

There **is** a way to capture an actual image of the editor viewport from
`execute_python`, not just read scene data — useful for visually
sanity-checking a build instead of relying on the user to send
screenshots. Two mechanisms exist, both incompletely reliable so far
(SkyWars, session 10):

- `unreal.AutomationLibrary.take_high_res_screenshot(res_x, res_y,
  filename, camera=some_camera_actor, force_game_view=...)` returns an
  `AutomationEditorTask`. Its `is_task_done()`/`is_valid_task()` methods
  exist (guessed property names like `is_complete` don't) but
  `is_task_done()` was observed to **never** flip `True` even after 10s
  of polling — this API appears designed to run under the Automation/
  Functional Testing framework's own tick, not as a fire-and-forget call
  from an ad-hoc script.
- The `HighResShot` console command
  (`unreal.SystemLibrary.execute_console_command(any_actor,
  "HighResShot 1280x720")`) **did** produce a real file once, but repeat
  calls (including with an explicit `filename=` to avoid overwrite
  collisions) silently produced nothing further in the same session —
  unclear whether the original success actually came from this command or
  from a coincidentally-flushed earlier `take_high_res_screenshot` task.

**Where the file lands** (needed either way, and not obvious —
screenshots do **not** go under the `.uefnproject`'s own folder):
`unreal.Paths.screen_shot_dir()` /
`unreal.Paths.convert_relative_path_to_full(...)` resolve it, e.g.
`C:/Users/<user>/AppData/Local/UnrealEditorFortnite/Saved/Screenshots/WindowsEditor/` —
under the shared UEFN editor's own AppData folder, not the project
directory `get_editor_status` reports (`project_file` there is a relative
path into the actual `FortniteGame` engine install, not the `.uefnproject`
folder). Read the resulting `.png` with a file-reading tool that supports
images once it appears.

**Practical guidance until this is more reliable**: spawn a temporary
`CameraActor` positioned/rotated for the shot you want, try
`HighResShot` via console command first, poll the screenshot directory
for a new file for a few seconds, and don't be surprised if a second
attempt in the same session doesn't produce anything — a UEFN restart
between attempts may be what actually unsticks it (not confirmed). Clean
up the temporary camera actor afterward. Worth a follow-up investigation
if a project leans on this a lot — right now it got exactly one
screenshot out of ~4 attempts across two different APIs.
