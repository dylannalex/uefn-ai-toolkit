---
description: The live-session workaround and the FortPickupCreative false positive that only failed after a restart.
---

# Correction, and a promising-looking dead end (`FortPickupCreative`)

Part of the [item-content investigation](overview.md). Continues from
[pass 3](03-third-pass-live-tests.md).

## Correction: how item content actually gets assigned — a live-gameplay action, not an edit-time UI action

First attempt at validating the K-not-N duplication hypothesis (end of
[pass 3](03-third-pass-live-tests.md)) assumed the item picker would show up
somewhere in the edit-time Details panel, or would accept a drag from the
Content Drawer onto the device in the viewport. **Both wrong** — live-tested
in the editor: the Details panel component tree has no item field anywhere
in it (confirmed by scrolling the full list — it's all component/function
bindings, e.g. `TriggerOnPickedUpItem`, `SpawnItemWhenReceived`, no plain
item slot), and dragging a weapon asset from the Content Drawer onto the
device in the viewport visually previews the item sitting on the spawner's
pad but doesn't actually register anything — re-reading `"Spawn Item"`
afterward still showed the fully-empty default
(`DefaultHandlerFunctions=(),EventSubscriptions=()`), and a
`duplicate_actor` clone made right after showed nothing either, consistent
with the assignment never having taken.

Per Epic's own docs (`using-item-spawner-devices-in-fortnite-creative`) and
corroborating community sources: **item registration happens in a live Play
session, not edit mode.** You place the device in the editor as normal
(scriptable, already proven), but assigning its content requires launching
a session, getting the item into the player's own inventory (Creative
islands give the owner/editor a cheat/creative-inventory menu during play
for exactly this), walking to the device, and dragging the item from
inventory onto it (PC) or standing on it and pressing the drop button
(console) — this is what "drop items near the device to register them"
means in Epic's phrasing. This doesn't change the K-not-N conclusion above
(still worth minimizing to one registration per distinct item and
duplicating the rest) — it just means each of those K touches costs "launch
a session and play," not "click a Details panel field," which makes
minimizing K matter more, not less.

## A different object entirely: `FortPickupCreative` — looked like a real breakthrough, confirmed dead end

Before accepting the live-session requirement, tried sidestepping the whole
"Device" family (Item Spawner/Item Granter) in favor of the actual physical
weapon-on-the-ground actor class, reasoning that a concrete pickup instance
might hold its item as a plain reference rather than a Verse-hookup struct.
Found via `dir(unreal)`: `FortPickupCreative`/`FortPickupAthena`/`FortPickup`
(native, not Blueprint `_C`), each with `primary_pickup_dummy_item` — an
`ObjectProperty` that reads back as plain `None` by default (not the
`GameplayEventFunction` empty-struct shape seen everywhere else). Promising
enough to chase:

1. Directly assigning a `FortWeaponRangedItemDefinition` asset (e.g.
   `/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_C_Ore_T02` — 335 real
   weapon definitions live under `/Game/Athena/Items/Weapons`, plainly
   named, browsable via the asset registry) **fails**: the property expects
   a `FortItem` *instance*, not an item *definition* asset
   (`Cannot nativize 'FortWeaponRangedItemDefinition' as 'Object' (allowed
   Class type: 'FortItem')`).
2. `unreal.FortItemFunctionLibrary.create_temporary_item_instance(item_definition,
   count, level) -> FortItem` **does** construct a `FortItem` (concretely a
   `FortWorldItem`) from a definition, fully from Python. Assigning that to
   `primary_pickup_dummy_item` **succeeded** — `set_editor_property` didn't
   error, and reading the property straight back showed the assignment
   held. At this point it looked like a genuine, fully-scriptable weapon
   assignment path outside the whole Item Spawner/Granter wall.
3. **Turned out to be a dead end**: the created `FortItem` lives in the
   `/Engine/Transient` package (visible in its full path,
   `/Engine/Transient.FortWorldItem_0`) — a strong hint from the name alone
   (`create_TEMPORARY_item_instance`) that this is meant for ephemeral
   UI/preview purposes (item cards, tooltips), not durable level content.
   Saving the level via `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()`
   "succeeded" (returned `True`, no exception) and the in-memory Python
   readback still showed the assignment — but that's not real evidence,
   since the object reference stays valid in memory for the rest of the
   *same* editor session regardless of what actually got written to disk.
   The real test is a fresh editor load: reopened the project after
   spawning+assigning+saving one of these, and **UEFN's own Message Log /
   Asset Check flagged it**: `Illegal property override: Value
   "/SkyWars/SkyWars.SkyWars:PersistentLevel...` with a one-click "Fix:
   Reset Property to Default" offered — i.e. UEFN's own validator considers
   a saved reference to a Transient object invalid and will silently reset
   it. Confirmed dead end, not just theoretical risk.

**Practical note for next time**: don't trust `save_current_level()`/`save_level`
returning success as proof a Python-set property is durably valid — for
anything assigning an object reference that *might* be Transient (check the
`get_path_name()`/`get_outer()` of the assigned value — a `/Engine/Transient`
prefix is the tell), the only real test is closing and reopening the
project (or at minimum a level reload) and checking the Message Log's Asset
Check output for "Illegal property override" warnings, not just re-reading
the property in the same session.

**Conclusion at this point**: no object in the Fortnite/Creative content set
was found that accepts a durable, Python-settable weapon reference. The
live-session drop-to-register mechanism above remained the only
confirmed-working path — until [pass 5](05-real-property-and-itemspawner-v3-confirmed.md)
found a real, working exception for Item Spawner V3.
