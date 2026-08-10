# How to set Item Spawner content via script

**Status: confirmed working, survives a real UEFN editor restart** (verified 2026-08-09 against `SkyWars` — see [gotchas/item-content/index.md](gotchas/item-content/index.md) for the full trail; this doc is just the "how to use it" reference).

## Scope — read this first

Works for **`Device_ItemSpawner_V3_C`** (chests, "global spawn" item pads) and nothing else yet — don't generalize to other item-holding devices:

| Device | Scriptable? |
| --- | --- |
| `Device_ItemSpawner_V3_C` (chests, global-spawn pads) | **Yes** — this doc |
| `Device_ItemGranter_V2_C` | **No** — confirmed blocked, same error shape (`cannot be edited on instances`) on its equivalent component (`PickupItemListComponent_C.ItemList`). Still needs the live-session drop-to-register flow (see [gotchas/item-content/04-live-session-and-fortpickupcreative.md](gotchas/item-content/04-live-session-and-fortpickupcreative.md)). |
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

For multiple items in one spawner (e.g. for the `Random Spawns` User Option — see [gotchas/user-options.md](gotchas/user-options.md)), pass a list of several entries instead of one.

## Finding item asset paths

Real definitions live under `/Game/Athena/Items/...` (`.../Weapons`, e.g. `WID_Assault_Auto_Athena_C_Ore_T02`, 335 found in one sweep, tier code tracks rarity; `.../Consumables`; resources under `/Game/Items/ResourcePickups`). Search the registry, don't guess names:

```python
registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = registry.get_assets_by_path("/Game/Athena/Items/Weapons", recursive=True)
weapons = [a for a in assets if str(a.asset_class_path.asset_name) == 'FortWeaponRangedItemDefinition']
```

## After setting it

- **Read back to confirm** — `comp.get_editor_property("ToSpawnList")` — and **save with the `save_level` MCP tool**, not a raw engine save call.
- The pickup mesh on the chest/pad updates immediately in the viewport, a quick visual sanity check.
- **Survives a real editor close/reopen** — confirmed empirically, unlike a similar-looking `FortPickupCreative` approach that looked identical at this stage but silently failed on reload — see [gotchas/item-content/04-live-session-and-fortpickupcreative.md](gotchas/item-content/04-live-session-and-fortpickupcreative.md).

## What this means for workarounds, and what's not done yet

A manual "Details-panel item assignment sheet" (e.g. `personal/fortnite-maps/SkyWars/docs/manual-assignment-sheet.md`) can drop the manual pass **for its Item Spawner instances** and script the assignments directly; Item Granter entries in that sheet still need the live-session workaround. This could also become a dedicated `@mcp.tool()` (e.g. `set_item_spawner_content`) in `src/uefn_mcp/server.py` instead of hand-writing the snippet above every time — see [architecture.md](architecture.md) for how tools are structured, and [gotchas/item-content/index.md](gotchas/item-content/index.md) for the full "what's left" status. Not implemented as of this writing.
