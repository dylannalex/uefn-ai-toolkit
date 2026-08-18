---
description: Publish-safe trees, palms, bushes and groundcover with measured sizes and seating offsets — and the ones confirmed disallowed, so they aren't re-tested.
---

# Trees, foliage and groundcover

Every row was spawned, `save_level`'d, then checked with `is_object_valid`
(never before the save — see [../gotchas/validation.md](../gotchas/validation.md)).
Paths are Blueprint actor classes, spawned as `<path>.<Name>_C` with
`load_class` + `spawn_actor_from_class`.

**Start with the Asteria foliage library.** `/Game/Environments/Asteria/Foliage/Trees/`
holds around 119 tree Blueprints across Oak, HolmOak, SessileOak, Birch,
Cypress, Pine, CherryBlossom, JapaneseMaple, Olive, Balsa, Rubber, Umbrella,
Kapok and Bamboo, in green / red / yellow / snow variants — **25 of 25
candidates tested came back valid**. That hit rate is far better than the
`/Game/Athena/...` and `/Game/Building/...` foliage, which one project fought
with for eleven sessions before finding this folder.

`bottomOffset` is `actor_location.z - bounds_min_z`: **add it to the traced
ground Z** to seat the bounds bottom on the ground.

## Asteria trees — measured

| Asset | Path | Verdict | Verified | xyRadius / Height / bottomOffset | Notes |
| --- | --- | --- | --- | --- | --- |
| `BP_Hera_Oak_Tree_Medium_Grasslands_CS` | `…/Foliage/Trees/Oak/Blueprint/` | valid | 2026-08 | 533 / 1248 / 92.4 | Best-looking of the set: big, vivid, lush green |
| `BP_Asteria_Oak_Tree_Medium` | `…/Foliage/Trees/Oak/Blueprint/` | valid | 2026-08 | 533 / 1248 / 92.4 | Same mesh, lighter green leaf material |
| `BP_Asteria_Oak_Tree_Medium_J` | `…/Foliage/Trees/Oak/Blueprint/` | valid | 2026-08 | 533 / 1248 / 92.4 | Third colour variant |
| `BP_Helios_HolmOak_Tree` | `…/Foliage/Trees/HolmOak/Blueprints/` | valid | 2026-08 | 1097 / 1473 / 216.0 | Broad umbrella canopy, widest medium tree |
| `BP_Tree_Asteria_CypressTree_01` | `…/Foliage/Trees/CypressTree/Blueprints/` | valid | 2026-08 | 410 / 2321 / 45.2 | Tall narrow vertical accent, reads well on a skyline |
| `BP_Asteria_Cherry_Blossom_Tree` | `…/Foliage/Trees/CherryBlossom/Blueprint/` | valid | 2026-08 | 627 / 1672 / 89.5 | Pink blossom; a landmark, use one or two only |
| `Asteria_PhysicsTreeStump_01` | `…/Foliage/Trees/PhysicsTree/Blueprint/` | valid | 2026-08 | 144 / 270 / 103.7 | Small stump |
| `BP_Asteria_Oak_Tree_Large` | `…/Foliage/Trees/Oak/Blueprint/` | valid | 2026-08 | — | Validated, not yet used |
| `BP_Asteria_Oak_Tree_Mediuam_Red` | `…/Foliage/Trees/Oak/Blueprint/` | valid | 2026-08 | — | Orange autumn. Epic's own typo in the asset name — not ours |
| `BP_Tree_Asteria_SessileOak` | `…/Foliage/Trees/SessileOak/Blueprints/` | valid | 2026-08 | 3017 wide | Very large |
| `BP_Tree_Asteria_OliveTree` | `…/Foliage/Trees/Olive/Blueprints/` | valid | 2026-08 | 945 × 810 | Smallest real tree |
| `BP_Tree_Asteria_RubberTree` | `…/Foliage/Trees/Rubber/Blueprints/` | valid | 2026-08 | — | |
| `BP_Tree_Asteria_BalsaTree` | `…/Foliage/Trees/Balsa/Blueprints/` | valid | 2026-08 | — | |
| `BP_Umbrella_Tree` | `…/Foliage/Trees/Umbrella/Blueprints/` | valid | 2026-08 | — | |

## Athena and Building trees

| Asset | Path | Verdict | Verified | Notes |
| --- | --- | --- | --- | --- |
| `Athena_Tree_Jungle_01` | `/Game/Athena/Environments/Blueprints/` | valid | 2026-08 | |
| `Athena_Tree_Large_2` | `/Game/Athena/Environments/Blueprints/` | valid | 2026-08 | |
| `Athena_Tree_Medium_01_` | `/Game/Athena/Environments/Blueprints/` | valid | 2026-08 | Trailing underscore is part of the name |
| `Athena_Tree_Pine_01_Snow` | `/Game/Athena/Environments/Blueprints/` | valid | 2026-08 | |
| `Palm_Tree_06`, `Palm_Tree_06a` | `/Game/Building/ActorBlueprints/Prop/` | valid | 2026-08 | |
| `Apollo_Desert_Palm_01` | `/Game/Athena/Apollo/Environments/BuildingActors/Desert/Foliage/` | valid | 2026-08 | |
| `Tree_Dead_A`, `Tree_Dead_B`, `Tree_Dead_C` | `/Game/Building/ActorBlueprints/Prop/` | valid | 2026-08 | |
| `Tree_Bush_1a` | `/Game/Building/ActorBlueprints/Prop/` | valid | 2026-08 | |
| `Athena_Tree_Large_1` | `/Game/Athena/Environments/Blueprints/` | **invalid** | 2026-08 | Don't re-try |
| `Athena_Tree_Large_Snow` | `/Game/Athena/Environments/Blueprints/` | **invalid** | 2026-08 | Don't re-try |
| `Athena_Tree_Medium_01_Snow` | `/Game/Athena/Environments/Blueprints/` | **invalid** | 2026-08 | Don't re-try |
| `Plant_Shrub_01`, `Plant_Shrub_03` | `/Game/Building/ActorBlueprints/Prop/` | **invalid** | 2026-08 | Don't re-try |
| Every `CP_`-prefixed ApolloTrees Blueprint | `…/ApolloTrees/` | **invalid** | 2026-08 | Birch, MountainPine, Swamp, Willow, BigBush. **The `CP_` prefix does not predict exposure** — it looks like "Creative Prop" and means nothing here |

## Groundcover

| Asset | Path | Verdict | Verified | xyRadius / Height / bottomOffset | Notes |
| --- | --- | --- | --- | --- | --- |
| `Apollo_BigBush` | `/Game/Athena/Apollo/Environments/BuildingActors/Foliage/` | valid | 2026-08 | 591 / 1034 / **384.0** | Big lush dome. Note the large bottom offset — its pivot sits well above the bounds bottom |
| `Athena_Prop_Plant_Shrub_04` | `/Game/Athena/BuildingActors/Props/Building/ActorBlueprints/Containers/` | valid | 2026-08 | 111 / 161 / 8.5 | Round green shrub, the workhorse |
| `Athena_Prop_Plant_Shrub_06` | `…/Containers/` | valid | 2026-08 | 97 / 110 / 4.6 | Smaller round shrub |
| `Athena_Prop_Plant_Shrub_bush_sm_01` | `…/Containers/` | valid | 2026-08 | 76 / 135 / 0.6 | Smallest round shrub |
| `Tree_Bush_3` | `/Game/Building/ActorBlueprints/Prop/` | valid | 2026-08 | 113 / 187 / 0.9 | Sparse sprig, good low scatter |
| `BP_JunglePlants_IvyGroundPlant_01` | `/Game/Environments/Asteria/Foliage/JunglePlants/IvyPlants/Blueprints/` | valid | 2026-08 | 219 / **37** / 8.9 | Flattest usable groundcover found |
| `Creative_BP_Grass_Parent` | `/Game/Creative/BuildingActors/Props/` | valid but **visually wrong** | 2026-08 | 321 × 372 × 65 | A raised turf slab, not grass tufts. On existing grass it reads as a carpet offcut |
| `Hedge_Low_Square` | `/Game/Building/ActorBlueprints/Prop/` | valid but **visually wrong** | 2026-08 | 255 × 256 × 194 | A geometric trimmed-hedge cube. Photographed as a flowering bush against the sky, read as a green box in place; six were placed and deleted the same session |

All the groundcover above takes scale 0.7–1.9 without looking wrong, which is
what makes a scatter layer read as varied rather than stamped.

## Two rules for using any of this

**Validated is not the same as good.** The last two rows above pass
validation and are wrong in context. Judge a prop from a `SceneCapture2D` at
player eye height, in place — never from a line-up against the sky.

**Add less density than a top-down render suggests.** A layer of 131 ground
plants over one island read as visibly overcrowded from the ground; 117 were
deleted. Top-down renders systematically understate density.
