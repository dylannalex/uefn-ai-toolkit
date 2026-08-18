---
description: The confirmed working route: Item Spawner V3's ToSpawnList is a real, writable property.
---

# The real backing property, a new enumeration technique, and the confirmed fix

Part of the [item-content investigation](overview.md). Continues from
[pass 4](04-live-session-and-fortpickupcreative.md). This is where the
investigation actually resolves for Item Spawner V3 — see
[../../how-to/set-item-spawner-content.md](../../how-to/set-item-spawner-content.md)
for the how-to once you've read this.

## Found the real backing property — readable, but instance-writes are explicitly blocked

A user manually registered an item on a real chest via the live-session
mechanism ([pass 4](04-live-session-and-fortpickupcreative.md)), then
noticed the Details panel *does* show an "Item List" array property (1
element, a struct with "Pickup to Spawn" among other fields) when the
panel's category filter is set to "All" — contradicting the earlier
conclusion that no such property is visible anywhere in the Details panel.
It's real and it is Python-*readable* — the earlier conclusion was about
*writability*, which still holds for this specific property, but "no
visible property at all" was wrong and worth correcting.

Guessing the exact backing property name failed completely (tried ~50
names — `ItemList`, `Item List`, `PickupEntries`, `SpawnItemList`, etc. —
all `Failed to find property`), including checking every one of the
device's 24 sub-components individually. What finally worked was a
previously-undiscovered general-purpose tool:
**`unreal.JsonObjectGraphFunctionLibrary.stringify([obj], JsonStringifyOptions())`**
— an official (marked `! EXPERIMENTAL !` in its own docstring) UE function
that serializes an object and everything it reaches to a full JSON object
graph, **including properties invisible to `get_editor_property` guessing
and to the failed `property_link`/FField-walk attempts from
[pass 3](03-third-pass-live-tests.md)**. This is the real answer to "how do
you enumerate a Fortnite device's full property set from Python" — worth
reaching for immediately next time instead of re-attempting the FField/
`dir()` dead ends. Usage:

```python
result = unreal.JsonObjectGraphFunctionLibrary.stringify([actor], unreal.JsonStringifyOptions())
```

Running it against a configured `Device_ItemSpawner_V3_C` chest revealed
the real location: **not on the actor itself** — on its
`Creative_ItemPreview_Component` sub-component, under the property name
**`"Items to Load"`** (note: differs from the Details panel's displayed
label "Item List" — Epic's UI customization renames it, which is exactly
why guessing from the visible label never worked). It's an array of
`ItemVariantHandle` structs (`item`: object reference to a
`FortWeaponRangedItemDefinition`/etc. asset, `item_variant_guid`).

- **Read works fine**: `component.get_editor_property("Items to Load")`
  returns the real, correct weapon reference — confirmed against a chest a
  human had just configured via the live-session drop mechanism.
- **Write is explicitly blocked, with a clear reason given**:
  `component.set_editor_property("Items to Load", [entry])` fails with
  `Property 'Items to Load' for attribute 'Items to Load' on
  'Creative_ItemPreview_Component_C' cannot be edited on instances` — not a
  generic "property not found," but a specific instance-edit restriction.
  This reads as an intentional guard, most likely to force item assignment
  through Epic's official (licensing/entitlement-checked) registration flow
  rather than letting arbitrary code point a chest at any asset.

It also **empirically confirmed** the K-not-N duplication hypothesis from
[pass 3](03-third-pass-live-tests.md): since "Items to Load" is now
readable, a `duplicate_actor` clone of a manually-configured chest was
checked directly by reading this property on both — **the clone had the
identical item reference**, no live-session step needed for the copy.

## CONFIRMED (restart-tested) — `Minigame_Spawner_Component.ToSpawnList` is a real, scriptable, persistent write path

A different, second location holds what turned out to be the actual
gameplay-authoritative item data. On `Device_ItemSpawner_V3_C`'s
`Minigame_Spawner_Component` sub-component, the `ToSpawnList` property
(array of `MinigameSpawnerSpawnParams` structs) accepts a direct Python
write — unlike the preview component above — and **the user closed and
reopened UEFN for real, and the assignment survived**: `Central_Chest_02`'s
`ToSpawnList` still held `WID_Assault_Auto_Athena_C_Ore_T02` after
reconnecting. This is a confirmed, working, scriptable write path — not a
repeat of the `FortPickupCreative` false positive from
[pass 4](04-live-session-and-fortpickupcreative.md). See
[pass 6](06-pending-verification-historical-trail.md) for the full
discovery narrative (kept for the trail) and
[../../how-to/set-item-spawner-content.md](../../how-to/set-item-spawner-content.md)
for the practical how-to reference (code sample, field reference, scope
caveats — use that doc when actually doing this).

**Checked whether this extends to `Device_ItemGranter_V2_C` — it does not.**
Item Granter has no `Minigame_Spawner_Component`; its analogous component is
`PickupItemListComponent_C` (property `ItemList`, not `ToSpawnList`, on a
completely different Blueprint class from a different content path). Tried
the same write pattern against `ItemGranter_WoodDrip`'s
`PickupItemListComponent_C`: `set_editor_property("ItemList", ...)` fails
with the exact same restriction seen on the read-only preview component
above — `FortMinigameItemListComponent: Property 'ItemList' ... cannot be
edited on instances`. So: **Item Spawner V3's writability is not evidence
Item Granter (or any other item-holding device) also works** — each needs
its own empirical check, same as this whole investigation has repeatedly
shown. Item Granter still needs the live-session drop-to-register flow from
[pass 4](04-live-session-and-fortpickupcreative.md).
