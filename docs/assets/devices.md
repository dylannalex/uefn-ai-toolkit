---
description: Fortnite Creative device class paths, plus the two devices that are the wrong tool for a job and shouldn't be re-tried.
---

# Device class paths

Discovered with `execute_python` against a live editor; none of these are
hardcoded in the server. Spawn with `spawn_actor`.

Most are Blueprints under `/CreativeCoreDevices/`, but not all — several ship
in their own `/CRD_*` roots, and a few are native C++ classes that never
appear in an asset-registry search at all.

| Device | Class path | Verified |
| --- | --- | --- |
| Island Settings (`Device_ExperienceSettings_V2`) | `/CreativeCoreDevices/Device_ExperienceSettings_V2_UEFN.Device_ExperienceSettings_V2_UEFN_C` | 2026-08 |
| Round Settings | `/CreativeCoreDevices/Device_RoundSettings_V2.Device_RoundSettings_V2_C` | 2026-08 |
| Class Designer | `/CreativeCoreDevices/Device_ClassDesigner_V2.Device_ClassDesigner_V2_C` | 2026-08 |
| Item Spawner V3 | `/CreativeCoreDevices/Device_ItemSpawner_V3.Device_ItemSpawner_V3_C` | 2026-08 |
| Item Granter | `/CreativeCoreDevices/Device_ItemGranter_V2.Device_ItemGranter_V2_C` | 2026-08 |
| Timer | `/CreativeCoreDevices/Device_Timer_V2.Device_Timer_V2_C` | 2026-08 |
| Storm Controller — Basic | `/CreativeCoreDevices/Device_StormControllerBasic_V2.Device_StormControllerBasic_V2_C` | 2026-08 |
| Storm Controller — Advanced | `/CreativeCoreDevices/Device_StormControllerAdvanced_V2.Device_StormControllerAdvanced_V2_C` | 2026-08 |
| Score Manager | `/CreativeCoreDevices/Device_ScoreManager_V2.Device_ScoreManager_V2_C` | 2026-08 |
| Billboard | `/CreativeCoreDevices/Device_Billboard_V2.Device_Billboard_V2_C` | 2026-08 |
| Player Spawn Pad | `/Script/FortniteGame.FortPlayerStartCreative` | 2026-08 |

**Player Spawn Pad is a native C++ class, not a Blueprint** — found with
`unreal.load_class`, never by searching the asset registry. If a device seems
not to exist, try `load_class` on a `/Script/FortniteGame.*` name before
concluding it isn't there.

## Reading and writing device settings

Most "V2" device settings live in a runtime **User Options** system rather
than as plain UPROPERTYs. They are still writable — see
[../gotchas/user-options.md](../gotchas/user-options.md). Two things worth
knowing up front:

- `actor.get_user_option_values()` returns a map of every option's current
  key → value as strings. Use it to audit or keyword-sweep a device's whole
  option list; `get_user_option_definitions()` returns an opaque container
  with no usable iteration from Python.
- **Not everything on a V2 device is a User Option.** `matchmaking_min_players`
  and `matchmaking_max_players` on Island Settings are plain properties. Try
  the obvious snake_case `get_editor_property` first before assuming an
  option key is needed.

## Wrong tool for the job — don't re-try these

| Device | Why not | Use instead |
| --- | --- | --- |
| Elimination Volume (`/CreativeCoreDevices/Athena/Items/Traps/Device_Context_EliminationZone.Device_Context_EliminationZone_C`) | Trap-shaped: a small-footprint device, not an infinite kill plane. Scaling it produces a lopsided collision volume. | `WorldSettings.kill_z` — a plain, directly settable property: `world.get_world_settings().set_editor_property("kill_z", -3000.0)`. Not gated behind User Options. `kill_z_damage_type` defaults to `DmgTypeBP_Environmental`. |
| Item Granter, for scripted item content | Its `PickupItemListComponent_C.ItemList` rejects instance writes, and no Verse function on `item_granter_device` accepts an arbitrary item reference either. A platform wall, confirmed against Epic's own Verse API docs. | Item Spawner V3 and the `set_item_spawner_content` tool. See [../gotchas/item-content/overview.md](../gotchas/item-content/overview.md). |
