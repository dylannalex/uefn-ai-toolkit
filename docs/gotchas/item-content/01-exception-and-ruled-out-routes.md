# Pass 0 — the exception, and five ruled-out routes

Part of the [item-content investigation](index.md). This file covers the
initial finding and the first round of dead ends.

## Actual item/weapon content is Details-panel-only (as first found)

The "User Options are settable via `set_editor_property`" pattern
([../user-options.md](../user-options.md)) covers bools, numbers, and
enums. It does **not** extend to picking *which item* an Item Granter
grants or an Item Spawner spawns. Confirmed by exhaustive probing in one
session (dumping the device's full `dir()`, trying dozens of guessed
property names, and inspecting every struct-valued property found via
`.to_dict()`/`.export_text()`):

- `ItemGranter`'s `ItemToGrant` reads back as a plain `int` (an index into
  something), but no backing array/list property could be found under any
  guessed name (`Items`, `ItemList`, `GrantItems`, `ItemDefinitions`, ...).
- Properties that *sound* like the item reference (`GrantItem` on Item
  Granter, `Spawn Item` on Item Spawner) are actually `GameplayEventFunction`
  structs — Verse/Blueprint event-binding hookups (the "User Options -
  Functions" tab in the Details panel), not the item content itself. Their
  `to_dict()` comes back empty on an unwired instance.
- Epic's own forum threads describe wiring these via the Details panel's
  item-picker widget (drag a weapon from the Content Browser into the
  slot) — there's no documented Python or Verse path to set it headlessly.

Conclusion at this point: populating actual loot (weapons, consumables,
resources) into an Item Granter or Item Spawner instance requires a human
in the Details panel. (Later passes below revise this for Item Spawner V3
specifically — see [index.md](index.md) for the current status.)

## Confirmed routes that do NOT solve this (as of 2026-08-09)

A dedicated research pass checked five alternative angles — all dead ends
or untested-but-low-promise:

1. **Verse asset reflection (`@editable` typed as item_definition)**: Epic's
   asset reflection system exposes only Meshes, Textures, Materials, and
   Niagara VFX systems to Verse. No `item_definition`, `weapon_item_definition`,
   or `fort_item_definition` type exists in the system. Checked against the
   official "Exposing Assets with Asset Reflection" doc.
   Source: https://dev.epicgames.com/documentation/en-us/uefn/exposing-assets-with-asset-reflection-to-verse-in-unreal-editor-for-fortnite

2. **`item_granter_device` Verse API (first full check — was missing from
   prior session)**: The Verse API is richer than `item_spawner_device` —
   it adds `SetNextItem(Index)`, `GetItemIndex()`, `GrantItemIndex(ItemIndex)`,
   `SetItemGrantCountAtIndex(ItemIndex, Count)`, `GetItemGrantCountAtIndex(Index)`,
   `CycleToNextItem/Previous/Random`, and `RestockItems()`. But ALL of these
   are index-based operations that select or grant among the items *already
   configured* in the device's Details panel. No function accepts an
   `item_definition` or similar type to set what's *at* each index.
   Source: https://dev.epicgames.com/documentation/en-us/fortnite/verse-api/fortnitedotcom/devices/item_granter_device

3. **UEFN-TOOLBELT community project**: Real GitHub repo is
   `undergroundrap/UEFN-TOOLBELT`. Checked `docs/FORTNITE_DEVICES.md` —
   explicitly notes `item_definition` on Item Spawner is "set in editor." The
   55-category, 358-tool library covers actor organization, procedural
   generation, materials, Verse scaffolding, etc., but item/weapon content
   assignment is explicitly an unaddressed domain. No `ItemGranter` or
   `ItemSpawner` item content tooling found.

4. **Custom Items & Inventory system**: Epic added a beta system (Scene Graph
   `item_component` / `inventory_component`) with `AddItem()`,
   `AddItemDistribute()`, and `GrantEntitlement()`. This is limited to
   *custom island-specific items* only — it cannot grant standard Fortnite
   weapons or consumables from the main game's content library.
   Source: https://dev.epicgames.com/documentation/fortnite/custom-items-and-inventory-overview-in-fortnite

5. **Full FProperty enumeration via `get_class().property_link` chain**: A
   lower-level introspection method (documented at
   https://gist.github.com/apple1417/b23f91f7a9e3b834d6d052d35a0010ff)
   walks ALL FProperties on a UClass via `prop = obj.get_class().property_link;
   while prop: name=prop.name; prop=prop.property_link_next` — bypassing
   `dir()` which undercounts (confirmed in the User Options finding above).
   This was NOT yet tested against a live `Device_ItemGranter_V2_C` or
   `Device_ItemSpawner_V3_C` as of this writing — UEFN was not running during
   the research pass. Low-but-nonzero probability of surfacing a property
   name not found by prior guessing. Worth trying once with a live editor
   before concluding impossible. (Tried in [pass 3](03-third-pass-live-tests.md)
   — dead end.)
