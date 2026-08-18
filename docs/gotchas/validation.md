---
description: Why a level passes validation and still fails to publish — is_object_valid before a save, raw assets vs Blueprint wrappers, and the content root that is exempt from the allowlist.
---

# Publishing validation: what passes, what actually ships

Fortnite only lets a published island reference assets on its Creative
exposure list (`FortExposedAssetList` data assets — 193 of them in this
build, covering 4748 asset paths). A reference to anything else fails
validation. The failure is not at spawn time, which is what makes all of this
confusing: the actor spawns, looks right, and is a problem later.

## 1. `is_object_valid` is only truthful after `save_level`

The exact same material on the exact same actor reads **VALID** on a
freshly-spawned, unsaved actor and **INVALID** on that identical actor
immediately after saving.

This has given false clean bills of health twice. One session's "0 invalid"
check ran pre-save and missed that all six of its biome ground materials, and
all 66 foliage props it had just placed, were disallowed.

**Always validate after saving, never before.** The `validate_level` tool
saves first by default for this reason.

Same shape of trap as the `FortPickupCreative` false positive, which only
failed after a restart — see
[item-content/04-live-session-and-fortpickupcreative.md](item-content/04-live-session-and-fortpickupcreative.md).

## 2. `is_object_valid` returns a tuple

`(DataValidationResult, warnings, errors)` — not the bare enum the name
suggests. Comparing the return value to the enum reports **every** actor as
invalid, because a tuple never equals an enum member.

```python
r = ev.is_object_valid(a, unreal.DataValidationUsecase.MANUAL)
if r != unreal.DataValidationResult.VALID:            # WRONG - always true
if r[0] != unreal.DataValidationResult.VALID or list(r[2]):   # right
```

The failure is loud (an implausible 100% failure rate) rather than silent,
but it still cost a debugging round in a project that had a real history of
validation problems.

## 3. A disallowed raw asset does not mean the content is unavailable

**Look for a Blueprint actor wrapper before giving up.** Every early test in
one session spawned raw assets directly — `spawn_actor_from_object` on a
loaded `StaticMesh` — and got `illegally references: disallowed object`,
which led to the wrong conclusion that real Fortnite trees were unusable.

Searching all 193 `FortExposedAssetList` data assets for tree entries found
real trees listed, but every one as a **Blueprint actor path**
(`/Game/Athena/Environments/Blueprints/Athena_Tree_Pine_01.Athena_Tree_Pine_01_C`),
never the bare mesh:

```python
registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = registry.get_assets_by_class(
    unreal.TopLevelAssetPath("/Script/FortniteGame", "FortExposedAssetList"), True)
# then JsonObjectGraphFunctionLibrary.stringify each one and search its
# AssetToExpose entries
```

Spawn a Blueprint with `unreal.load_class(None, bp_path)` +
`spawn_actor_from_class` — **not** `spawn_actor_from_object`, which is for
raw objects. Blueprints are actor classes; raw meshes are not.

## 4. When no Epic asset works, author it yourself under the project root

**Content under the project's own content root (`/<ProjectName>/...`) is
exempt from the allowlist.** This is the general escape hatch.

What does *not* work: creating the asset under `/Game/...`, even in a fresh
folder of your own. `/Game/` is the shared Fortnite content mount, writable
but not project-owned — a brand-new `MaterialInstanceConstant` created there
still failed with `hard references an unsaved package` plus a disallowed-object
error. Recreating the identical asset under `/<Project>/Content/Materials/`
validated clean immediately post-save.

Find the project's root from the level package's own path (e.g.
`/SkyWars/SkyWars`).

`/Engine/BasicShapes/*` primitives are always exposed regardless, since
`/Engine/` isn't Fortnite content at all.

## 5. Validated does not mean it looks right

`is_object_valid` answers "may I ship this", never "does this look right".
Two assets that validate cleanly and are visually wrong in context:
`Creative_BP_Grass_Parent` is a raised turf slab that reads as a carpet
offcut on existing grass, and `Hedge_Low_Square` is a geometric trimmed-hedge
cube that photographed as a flowering bush against the sky and as a green box
in place.

**Judge a prop from a `SceneCapture2D` at player eye height, in situ** — not
from a candidate line-up shot against the sky.

## 6. Prefer `set_editor_property` to type-specific setters

`component.set_material(0, mat)` succeeds, passes validation, and was found
**not persisted** after a save and later work in the same session — a
readback showed `override_materials` back to `[]` with no error at any step.
`comp.set_editor_property("override_materials", [mat])` survives.

Root cause unconfirmed, plausibly that `set_material` doesn't route through
the same dirty-marking path. The practical rule holds either way: for
anything that has to persist, prefer `set_editor_property`.
