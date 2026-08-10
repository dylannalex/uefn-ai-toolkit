# Historical trail: how `ToSpawnList` was found, before the restart test confirmed it

Part of the [item-content investigation](index.md). This is the original,
in-the-moment writeup from before the restart-persistence check described
in [pass 5](05-real-property-and-itemspawner-v3-confirmed.md) was done —
kept for the historical trail (how the discovery actually happened), not as
current guidance. If you just want the confirmed how-to, see
[../../how-to-set-item-spawner-content.md](../../how-to-set-item-spawner-content.md).

---

POSSIBLE MAJOR REVISION — `Minigame_Spawner_Component.ToSpawnList` accepted
a direct Python write. PENDING a restart-persistence check before trusting
this; do not rely on it yet.

Right after finding `Creative_ItemPreview_Component`'s "Items to Load"
(read-only per [pass 5](05-real-property-and-itemspawner-v3-confirmed.md)),
the user pasted a full T3D copy/paste export of a configured
`Device_ItemSpawner_V3_C` (obtained via the editor's normal Ctrl+C on the
actor — worth remembering as another enumeration technique: T3D export via
copy-to-clipboard shows every component's real property names and current
values in one readable text block, arguably more complete than the JSON
graph stringify above since it's literally the level file's own save
format). That export showed a **second, different** location holding what
looks like the actual gameplay-authoritative item data — not the preview
component:

```
Begin Object Name="Minigame_Spawner_Component" ...
   ToSpawnList(0)=(PickupToSpawn="/Game/Athena/Items/Weapons/WID_Assault_AutoHigh_Athena_C_Ore_T03.WID_Assault_AutoHigh_Athena_C_Ore_T03")
End Object
```

`PickupToSpawn` matches the Details panel's "Pickup to Spawn" label exactly
(unlike "Items to Load" vs "Item List" on the preview component, which
didn't match — a good sign this is the real, UI-authoritative field, not a
cosmetic duplicate). Checked directly:

- **Read**: `component.get_editor_property("ToSpawnList")` on
  `Minigame_Spawner_Component` (class `Minigame_Spawner_Component_C`, from
  `/Game/Athena/Items/Traps/MinigameSpawner/Minigame_Spawner_Component`)
  returns an array of `MinigameSpawnerSpawnParams` structs:
  `pickup_to_spawn` (object ref), `pickup_quantity`, `pickup_instigator_handle`,
  `item_variant_guid`, `spawn_transform`, `weapon_ammo_override`,
  `linked_weapon_ammo_override`, `has_linked_weapon`. Confirmed matching a
  human-configured chest's real content.
- **Write — unlike the preview component, this one did NOT reject the
  instance edit.** Built a new `MinigameSpawnerSpawnParams` struct with
  `pickup_to_spawn` set to a different weapon asset
  (`WID_Assault_Auto_Athena_C_Ore_T02`), called
  `component.set_editor_property("ToSpawnList", [new_entry])` on a
  previously-*unconfigured* chest (`Central_Chest_02`) — **no exception**,
  readback showed the correct new value, and the user visually confirmed
  the weapon mesh appeared sitting on that chest in the viewport. Saved via
  the proper `save_level` MCP call (not the raw engine API misstep from
  earlier in this session).
- **Meaningfully different from the earlier `FortPickupCreative` false
  positive**: that one pointed to an object living in `/Engine/Transient`
  (a dead giveaway it wouldn't survive serialization, confirmed by an
  actual restart). This one points directly at the real, permanent content
  asset (`/Game/Athena/Items/Weapons/...`, the same kind of reference the
  human-configured chest already had) — no Transient package involved, a
  much better sign, but **not yet proof**. The same session already
  demonstrated once that "looked right in-editor, `save_level` returned
  success" is not sufficient evidence on its own.

**Status at the time of writing: pending a real close/reopen-UEFN test.**
This was later followed up and confirmed — see
[pass 5](05-real-property-and-itemspawner-v3-confirmed.md) for the restart
result.
