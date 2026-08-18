---
description: Moving a placed actor silently fails to save without actor.modify(), and leaves its collision body behind — read before any bulk transform work.
---

# Moving a placed actor: two traps that report success while doing nothing

Both were hit in one session (SkyWars, session 12), cost an entire map
reposition, and are **project-agnostic** — they apply to any World Partition
level, which is every UEFN project. Read this before scripting any bulk move,
rescale or reposition.

The shared symptom: `set_actor_location` returns cleanly, an immediate
readback agrees, the viewport looks right, and the validator passes. Nothing
tells you anything is wrong until the next editor restart.

## 1. Transforms are not saved unless you call `actor.modify()` first

`set_actor_location` and `set_actor_scale3d` **never dirty the actor's
package**. In a World Partition level every actor lives in its own
`/<Project>/__ExternalActors__/...` package, so `save_level` finds nothing
marked dirty, writes nothing, and **returns success**. On the next restart
every move snaps back to where it was.

The diagnostic tell: **spawned actors keep their positions, moved actors
revert.** `set_editor_property` *does* dirty correctly — which is why, in the
session that found this, a Storm Controller's radii and `WorldSettings.kill_z`
survived a restart untouched while an entire map reposition was lost. It also
explains the confusing near-miss: one actor's move *did* persist, because the
same script happened to also set `override_materials` on it.

```python
a.modify()                                   # <- the missing piece
a.set_actor_location(v, False, True)
...
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
```

**Always check the dirty count around the save** — non-zero before, 0 after:

```python
len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
```

If it is already 0 *before* you save, your changes are not going to disk.
(Confirmed working in SkyWars session 13: dirty went 266 → 0 across the save,
and the layout survived a full editor reload.)

## 2. Collision does not follow the move

Even with `teleport=True`, a single absolute move leaves the collision body
behind — the mesh renders in the new place but is not standable. Symptom: a
line trace over moved terrain finds nothing, or hits whatever is underneath it
instead.

Neither `set_world_location` on the component nor `recreate_physics_state`
(which doesn't exist on `BaseBuildingStaticMeshComponent`) fixed it. The only
reliable repair observed is a **nudge-and-return**, applied to every moved
actor as the last step before saving:

```python
p = a.get_actor_location()
a.modify()
a.set_actor_location(unreal.Vector(p.x, p.y, p.z + 1.0), False, True)
a.set_actor_location(unreal.Vector(p.x, p.y, p.z), False, True)
```

This took rock-backed trace coverage from 767/1387 samples to 1386/1387.

## 3. How to verify anything geometric

- **Verify moves with a line trace, never with bounds.** `get_actor_bounds`
  cheerfully reports the new position while collision sits elsewhere, so
  bounds prove nothing about whether a surface is standable.
- **Assert on the expected surface height, not on a floor value.** A hole
  check written as `z < <some floor>` passes happily while every trace lands
  on a *different* surface than intended (in SkyWars, a hidden safety disc
  15cm below the real terrain). That produced a false "0 holes" result.
- **Run `is_object_valid` after `save_level`, never before** — a pre-save
  check is unreliable and gave two false clean bills of health in this
  project.
- `HitResult` fields are protected in UE 5.8's Python bindings — `h.location`
  raises. Use `h.to_tuple()`: index **4** is the impact location, **9** the
  hit actor, **10** the hit component.
