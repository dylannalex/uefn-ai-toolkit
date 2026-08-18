---
description: Third pass: live tests against a running editor (SkyWars session 7).
---

# Pass 3 — live-editor tests of the remaining leads, plus a new (non-viable) lead

Part of the [item-content investigation](overview.md) (SkyWars session 7).
Continues from [pass 2](02-second-pass-corroboration.md).

Live UEFN editor was connected for this pass, so both items angle 5 flagged
as "untested, try with a live editor" finally got tried directly:

- **`get_class().property_link` FField-chain walk (angle 5 first form)**:
  fails immediately — `unreal.Class` objects in UEFN's Python binding (the
  official Editor Scripting plugin, not full UnrealEnginePython) don't expose
  `property_link`/`property_link_next` at all
  (`AttributeError: 'BlueprintGeneratedClass' object has no attribute
  'property_link'`). `dir(cls)` on a device class confirms the binding only
  exposes a small fixed method set (`get_editor_property`,
  `set_editor_property`, `get_default_object`, ...), no raw FField
  enumeration. This closes off the whole "walk the compiled UClass memory
  layout from Python" family of approaches (including, by extension, the
  untested `device_deep_options` raw-memory variant from
  [pass 2](02-second-pass-corroboration.md) — same category of binding
  limitation, not worth trying since this binding doesn't expose the
  underlying reflection data at all, Python or otherwise).
- **`Device_ItemSpawner_V3_C`'s full `get_user_option_values()` dump**
  (bulk-read, not previously done against this specific device with fresh
  eyes) surfaced one option prior sessions hadn't logged: **`Random Spawns`**
  (enum: `Off`/`Random`/`No Repeats`). Sounds promising but **does not
  solve item-content assignment** — it only changes how the device cycles
  among items *already configured* in its (Python-invisible) item list; an
  empty/unconfigured spawner with `Random Spawns=Random` still spawns
  nothing. Doesn't reduce the manual-pick count, just adds randomization on
  top of picks you still have to make by hand.

## New lead found, real but not viable for curated content

Outside the Creative "Device_*" family entirely, the raw Battle-Royale chest
actor Blueprints (e.g.
`/Game/Building/ActorBlueprints/Containers/Supply_Chest_Creative.Supply_Chest_Creative_C`,
also `Creative_Chest_Parent_C`, `Tiered_Chest_Athena_C`) **do** expose a
plain, directly `get_editor_property`/`set_editor_property`-able `Name`
property, `SearchLootTierGroup` (default `Loot_AthenaSupplyDrop` on the
Supply Chest variant) — this points at a row in a main-game loot-tier
DataTable (`/Game/Items/Datatables/LootLevelData`, or one of the many
per-playlist `LootTierData`/`OverrideLootTierData` tables under
`/Game/Athena/Playlists/...`) and genuinely sidesteps the whole
GameplayEventFunction-hookup wall, confirmed by live-spawning one
(`spawn_actor_from_class` succeeded, real mesh `TreasureChestLootTier6`
loaded, `BuildingContainer`-family methods present — not broken/placeholder
content). **Why this isn't a usable fix**:

1. It's not a Creative "device" — no User Options interface, not in the
   device palette, not designed for placement outside the main BR game
   mode. Whether it actually spawns loot at runtime inside a custom UEFN
   minigame (no full BR match/loot-manager subsystem running) is
   *unverified* — this was only checked for clean edit-time spawning, not
   runtime behavior, which would need an actual Play session to confirm.
2. The loot-tier DataTables it reads from are tied to live, rotating BR
   seasonal playlists (`Papaya`, `Playground`, `Showdown`, ...), not a
   stable "give me common pool" row — no row was found matching a plain
   rarity name in a 899-row sweep of `LootLevelData`. Even if wired up, it
   would draw from whatever the current season's pool is, not a project's
   own curated per-tier item list.
3. Even setting that aside, it trades away exactly the design control a
   curated loot table needs (specific item per chest/tier) for "some random
   BR-season loot," which is a worse fit for a designed map, not just an
   automation shortcut.

Test actor was deleted after the check (`delete_actor`, no `save_level`
call — level was left untouched). Worth remembering this class/property
exists in case a *future* project actually wants "just drop live BR loot
pools with zero configuration" as a design goal (where losing curated
control isn't a downside) — but for curated per-tier content, it's a dead
end same as everything else in this investigation.

## Practical workaround for the actual bottleneck (item-count, not possibility)

Since item content is a real (if Python-invisible) per-instance property,
and engine-level actor duplication (`EditorActorSubsystem.duplicate_actor`,
wrapped by this repo's `duplicate_actor` MCP tool) does a full
property-level deep copy regardless of Python exposure, a
manually-configured device's item content should survive being duplicated —
meaning the real minimum manual-touch count for a project with N loot
instances but only K *distinct* items is K (configure one template per
unique item), not N. Everything after that — placement, positioning,
repeating for every actual instance — is `duplicate_actor` +
`set_actor_transform`, both scriptable. This was later empirically
confirmed — see [pass 5](05-real-property-and-itemspawner-v3-confirmed.md).
