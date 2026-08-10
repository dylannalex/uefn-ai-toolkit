# Pass 2 — independent corroboration, still no live editor

Part of the [item-content investigation](index.md). Continues from
[pass 0](01-exception-and-ruled-out-routes.md).

No UEFN editor was connected during this pass either (`get_editor_status`
failed with `Remote party failed to attempt the command socket connection!`)
— everything below is documentary/third-party corroboration, not new
empirical testing. Checked Epic's own docs plus several community
`uefn-mcp`-style repos (via `gh repo clone`) for a different angle on the
same question:

- **`dylannalex/uefn-mcp-server`'s generated capability map**
  (`docs/uefn_python_capabilities.md`, built from a full 28,850-type scan of
  UEFN's Fortnite-specific Python surface) independently states, for the
  entire `Fort*` class domain: "No spawning of Fortnite-specific actors from
  Python" and "No inventory modification (read-only)." This was arrived at
  by a blanket API scan, not device-specific probing, but lands on the same
  conclusion as the device-level finding above.
- **Epic's "Weapon Templates in Fortnite" doc** describes a newer, separate
  system (Scene Graph/Prefab-based custom weapons + a Verse "Armory
  module") — checked in case it offered a scriptable creation path distinct
  from Item Granter/Spawner. It doesn't: initial weapon creation still
  requires the Prefab Editor UI ("Double-click the prefab thumbnail in the
  content browser to open the Prefab Editor"), and the Armory module is
  runtime-only property modification (damage multipliers, holster state) of
  an *already-instantiated* weapon — no spawn/create/assign-content function
  is documented.
  Source: https://dev.epicgames.com/documentation/fortnite/weapon-templates-in-fortnite
- **Re-fetched `item_spawner_device` Verse API reference directly** (rather
  than trusting the prior session's summary) — unchanged: `CycleToNextItem`,
  `SpawnItem`, `Enable`/`Disable`, respawn-timer get/set only. Nothing
  accepts an item/weapon reference.
  Source: https://dev.epicgames.com/documentation/en-us/fortnite/verse-api/fortnitedotcom/devices/item_spawner_device
- **Community confirmation from the outside**: `mikeyaworski/UEFN-Verse-Devices`'
  `weapon_manager_device.verse` grants weapons by indexing into an array of
  Details-panel-configured `item_granter_device` instances
  (`WeaponGranters: []item_granter_device`) — the author's own comment reads
  "Surely there is a better way," i.e. an experienced community Verse dev
  independently hit this wall and didn't find a way around it either.
  Source: https://github.com/mikeyaworski/UEFN-Verse-Devices/blob/master/weapon_manager_device.verse
- An Epic forum thread ("How to grant specific item from Item Granter Index
  in Verse?") confirms the only Verse-side lever is `SetNextItem(Index:int)`
  — selecting *among* pre-configured items by hardcoded index, not assigning
  what's at an index.
  Source: https://forums.unrealengine.com/t/how-to-grant-specific-item-from-item-granter-index-in-verse/1188167
- Re-fetched the asset-reflection doc directly: still exactly four
  categories (Meshes, Textures, Materials, Niagara VFX Particle Systems), no
  item/weapon type added since the prior pass.

**A stronger, still-untested version of angle 5** (from
[pass 0](01-exception-and-ruled-out-routes.md)) **surfaced**:
`yAstrosss/PythonMCP-UEFN`'s `device_deepread.py` implements a
self-test-gated raw-memory walk of a live object's compiled `UClass` FField
chain (exposed as `device_deep_options`/`device_deep_set` tools),
enumerating *every* UPROPERTY/`@editable` including ones left at their
default value — which even T3D-scrape-based option listing and `dir()` both
miss. Its own header claims validation against "UE 5.8.0 / Fortnite 41.10."
This is a materially more thorough version of the plain `property_link` gist
approach above (walks compiled-class memory directly instead of the
Python-exposed FProperty chain) and hasn't been tried against
`Device_ItemGranter_V2_C`/`Device_ItemSpawner_V3_C` — do that first, next
session with a live editor, before concluding impossible. Note it is
fundamentally still a property *enumerator* plus a typed `set_editor_property`
*writer* — not a new write mechanism — so if it also finds no backing
item-content property, that's strong (not merely probable) confirmation
there isn't one to find.
Source: https://github.com/yAstrosss/PythonMCP-UEFN (`device_deepread.py`)

**Conclusion at end of this pass: still confirmed impossible via
`execute_python`.** No new write path found; every independent source lands
on the same wall. The one remaining unexplored lever is `device_deep_options`
above — tried in [pass 3](03-third-pass-live-tests.md), also a dead end.
