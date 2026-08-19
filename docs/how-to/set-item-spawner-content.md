---
description: The current, working method for scripting Item Spawner V3 content.
---

# How to set Item Spawner content via script

**Status: confirmed working, survives a real UEFN editor restart** (verified 2026-08-09 against `SkyWars` — see [../gotchas/item-content/overview.md](../gotchas/item-content/overview.md) for the full trail; this doc is just the "how to use it" reference).

## Scope — read this first

Works for **`Device_ItemSpawner_V3_C`** (chests, "global spawn" item pads) and nothing else yet — don't generalize to other item-holding devices:

| Device | Scriptable? |
| --- | --- |
| `Device_ItemSpawner_V3_C` (chests, global-spawn pads) | **Yes** — this doc |
| `Device_ItemGranter_V2_C` | **No** — confirmed blocked, same error shape (`cannot be edited on instances`) on its equivalent component (`PickupItemListComponent_C.ItemList`). Still needs the live-session drop-to-register flow (see [gotchas/item-content/04-live-session-and-fortpickupcreative.md](../gotchas/item-content/04-live-session-and-fortpickupcreative.md)). |
| Anything else | Untested — check before assuming either way. |

The working property is specific to Item Spawner V3's component makeup — Item Granter's structurally-similar component turned out blocked.

## The property

On any `Device_ItemSpawner_V3_C` actor, find its `Minigame_Spawner_Component` sub-component (class `Minigame_Spawner_Component_C`, from `/Game/Athena/Items/Traps/MinigameSpawner/Minigame_Spawner_Component`) and read/write its `ToSpawnList` property — an array of `MinigameSpawnerSpawnParams` structs. In practice you only need to set `pickup_to_spawn` and, for stackables, `pickup_quantity`; everything else defaults sensibly:

```
pickup_to_spawn               # object ref: the item/weapon definition asset
pickup_quantity                # int, e.g. ammo/stack count
pickup_instigator_handle       # int, leave at -1 (default)
item_variant_guid              # struct, leave default {} for a non-variant item
spawn_transform                 # struct, leave default
weapon_ammo_override            # int, -1 = weapon's default
linked_weapon_ammo_override     # int, -1 = default
has_linked_weapon               # bool, False unless pairing with another weapon
```

## Minimal example

```python
import unreal

def set_item_spawner_content(actor_label: str, weapon_asset_path: str, quantity: int = 1):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    actor = next(a for a in actors if a.get_actor_label() == actor_label)

    comp = next(
        c for c in actor.get_components_by_class(unreal.ActorComponent)
        if 'Minigame_Spawner' in c.get_class().get_name()
    )

    item = unreal.load_asset(weapon_asset_path)
    entry = unreal.MinigameSpawnerSpawnParams()
    entry.set_editor_property("pickup_to_spawn", item)
    entry.set_editor_property("pickup_quantity", quantity)

    comp.set_editor_property("ToSpawnList", [entry])

set_item_spawner_content(
    "Central_Chest_01",
    "/Game/Athena/Items/Weapons/WID_Assault_AutoHigh_Athena_C_Ore_T03.WID_Assault_AutoHigh_Athena_C_Ore_T03",
)
```

For multiple items in one spawner (e.g. for the `Random Spawns` User Option — see [gotchas/user-options.md](../gotchas/user-options.md)), pass a list of several entries instead of one.

## Finding item asset paths

Real definitions live under `/Game/Athena/Items/...` (`.../Weapons`, e.g. `WID_Assault_Auto_Athena_C_Ore_T02`, 335 found in one sweep, tier code tracks rarity; `.../Consumables`; resources under `/Game/Items/ResourcePickups`). Search the registry, don't guess names:

```python
registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = registry.get_assets_by_path("/Game/Athena/Items/Weapons", recursive=True)
weapons = [a for a in assets if str(a.asset_class_path.asset_name) == 'FortWeaponRangedItemDefinition']
```

**Matching a colloquial item name ("Pump Shotgun") to an asset**: the asset name itself rarely matches (`WID_Shotgun_Standard_Athena_C_Ore_T03`). Two registry tags solve this *without loading every candidate* — much faster than loading hundreds of assets to read `ItemName`:

```python
asset_data.get_tag_value("DisplayName")  # e.g. "Pump Shotgun" — the in-game item name
asset_data.get_tag_value("Rarity")       # "0".."5" = Common, Uncommon, Rare, Epic, Legendary, Mythic
```

Confirmed empirically (SkyWars, session 8) by cross-referencing the `Rarity` tag against the filename's tier-code suffix (`_C_`/`_UC_`/`_R_`/`_VR_`/`_SR_`/`_UR_`) on plain, non-seasonal weapon families, where the two agree. **They stop agreeing once a weapon is part of a seasonal "Ore" upgrade-tier system** (`_Ore_T0X` in the name) — those can have a filename suffix that doesn't match the actual `Rarity` tag. **Trust the `Rarity` tag, not the filename**, whenever the two disagree.

Several current-gen healing items (Bandages, Med Kit, Shield Potion, Small Shield Potion, Chug Jug) only exist with a `DisplayName` prefixed "Legacy" (e.g. `Athena_Bandage` → "Legacy Bandage"). That's still the real, working, loadable asset for that item — don't skip it looking for a non-prefixed version that doesn't exist.

**Critical gotcha: the asset registry lists assets this project can't actually load.** A registry hit (a `get_assets_by_path` result, a `DisplayName`/`Rarity` tag) is not proof the asset is usable — confirmed on SkyWars where every asset under `/Game/Athena/Items/Consumables/ForagedItemVersions` (Apple, Banana, Coconut, Shield Mushroom, Bouncy Egg, etc.) has full registry tags and shows up in searches, but `unreal.load_asset(path)` returns `None` for every one of them. Always verify with a real `load_asset()` call (non-`None` result) before writing an asset path into `ToSpawnList` — don't stop at "the registry found it."

**Second, more dangerous gotcha: `load_asset()` succeeding is *still* not proof the asset is allowed.** Some assets load fine, set into `ToSpawnList` without error, read back correctly, and *only* surface a problem later as an "Asset Check" message-log warning ("Illegal References to Default" / a `FortValidator_FortExposedActors` "references disallowed object" error) — this is a real Creative-content allowlist restriction (some standard-looking BR weapon variants, e.g. SpyTech-reskinned or certain plain non-"Ore" weapon defs, aren't on the exposed/allowed list for external Creative islands), not a duplication artifact or a false alarm. It does **not** show up immediately — it can take a save, or simply not surface in the visible Message Log until the user happens to look. Confirmed on SkyWars (session 8): `WID_Spytech_Pistol_SemiAuto_Suppressed_Athena_R_Ore_T03`, `WID_Shotgun_SemiAuto_Athena_C`, and `/Game/Items/ResourcePickups/Athena_WoodItemData` all loaded and set cleanly but are disallowed; sibling variants (`WID_Pistol_SemiAuto_Suppressed_Athena_UC_Ore_T03`, `WID_Shotgun_SemiAuto_Athena_UC_Ore_T03`, `/Game/Items/ResourcePickups/WoodItemData`) are functionally identical and pass.

**Don't rely on the Message Log to catch this — validate directly, in Python, before committing:**

```python
evs = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
result, errors, warnings = evs.is_object_valid(actor, unreal.DataValidationUsecase.MANUAL)
# result == unreal.DataValidationResult.VALID means clean; errors are text, contain the exact disallowed path if not
```

This runs the *same* validators the editor's Message Log uses (including `FortValidator_FortExposedActors`), but synchronously and against a specific actor, with no UI round-trip. Use it two ways:
1. **Audit everything already placed** — loop over all actors of interest and call this to find every disallowed reference in one pass, not just whatever the Message Log happened to show.
2. **Pre-validate a candidate replacement before writing it in** — temporarily set the candidate on a scratch actor (or the real one, since you can revert in-memory before saving), call `is_object_valid`, and only keep it if `VALID`. This is dramatically faster than the old workflow of writing, saving, hoping the Message Log surfaces it, then asking a human to eyeball the warning text.

## After setting it

- **Read back to confirm** — `comp.get_editor_property("ToSpawnList")` — and **save with the `save_level` MCP tool**, not a raw engine save call.
- The pickup mesh on the chest/pad updates immediately in the viewport, a quick visual sanity check.
- **Survives a real editor close/reopen** — confirmed empirically, unlike a similar-looking `FortPickupCreative` approach that looked identical at this stage but silently failed on reload — see [gotchas/item-content/04-live-session-and-fortpickupcreative.md](../gotchas/item-content/04-live-session-and-fortpickupcreative.md).

## Granting an item without showing a pad

An Item Spawner is a *visible* device: it draws a floating base wherever it
stands. That matters because the only scriptable way to hand a player an
arbitrary item is to teleport a pre-loaded spawner to them and fire it
(Item Granter's content cannot be written — see
[../gotchas/item-content/overview.md](../gotchas/item-content/overview.md)),
and a pad appearing under the player is not what "grant an item" is supposed
to look like.

Two user options make that pattern invisible, both plain booleans and both
writable with `set_device_options`:

| Option | Set to | Why |
|---|---|---|
| `Base Visible During Game` | `False` | Hides the pad. The item still spawns and is still collectable — only the base mesh goes |
| `Run Over Pickup` | `True` | Collection happens on overlap, so the player never has to press anything |

With both set, teleport the spawner to the player's **feet** —
`Character.GetTransform().Translation`, not `GetViewLocation()`, which is the
camera and sits outside the capsule the overlap needs — fire it, and send it
home. SkyWars runs 60 spawners this way.

## What this means for workarounds, and what's not done yet

A manual "Details-panel item assignment sheet" (e.g. `personal/fortnite-maps/SkyWars/docs/manual-assignment-sheet.md`) can drop the manual pass **for its Item Spawner instances** and script the assignments directly; Item Granter entries in that sheet still need the live-session workaround. The `set_item_spawner_content` tool does this now, so the snippet above is reference rather than something to paste — see [../gotchas/item-content/overview.md](../gotchas/item-content/overview.md) for the full "what's left" status.
