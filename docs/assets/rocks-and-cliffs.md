---
description: Publish-safe cliff slabs and rocks, their pivots and plateau shapes, the waterline that turns them blue below Z=0, and the biome cliff kits confirmed disallowed.
---

# Rocks and cliffs

Checked with `is_object_valid` after `save_level`. Spawn Blueprints as
`<path>.<Name>_C` with `load_class` + `spawn_actor_from_class`.

## The Asteria modular cliff kit — terrain slabs, not just walls

`/Game/Creative/BuildingActors/Props/Asteria/` — 41 Blueprints, 15 validated.

The important property, and the reason to reach for these first: several
pieces have a **large flat plateau on top with the cliff face dropping away
around it**, flat to within about ±10 cm (p5..p95). That makes one piece the
surface *and* the sides of a platform at once.

| Asset | Verdict | Verified | Notes |
| --- | --- | --- | --- |
| `CP_Asteria_Cliff_Small_Straight_A` / `_B` | valid | 2026-08 | Flat plateau on top |
| `CP_Asteria_Cliff_Small_Corner_90_A` | valid | 2026-08 | Flat plateau |
| `CP_Asteria_Cliff_Small_Corner_180_A` / `_B` | valid | 2026-08 | Flat plateau. `_B` guarantees radius 1350 at N=4, **1625 at N=6** (max 1875) |
| `CP_Asteria_Cliff_Small_Overhang_A` | valid | 2026-08 | Flat plateau |
| `CP_Asteria_Cliff_Medium_Corner_90_A` / `_180_A` | valid | 2026-08 | Flat plateau |
| `CP_Asteria_Cliff_Mud_Small_Straight_A` | valid | 2026-08 | Brown variant. Radius 1050 at N=4, **1150 at N=6** (max 1250) |
| `CP_Asteria_Cliff_Peak_A` / `_B` | valid | 2026-08 | **Pivot at base**, not centre; mass extends upward |
| `CP_Asteria_Cliff_Mountaintop_A` | valid | 2026-08 | Pivot at base |
| `CP_Rock_Common_Large_C_MudRock` | valid | 2026-08 | |
| `CP_Rock_Common_Medium_A` / `_B_MudRock` | valid | 2026-08 | |
| `CP_Asteria_DirtPile_A` | valid | 2026-08 | |
| `CP_ThroneRockWall_A` | valid | 2026-08 | 2562 × 198 × 1548 |
| `CP_Asteria_Cliff_Small_Corner_180_A` | valid | 2026-08 | |

To build a round platform out of rotated copies, read
[../how-to/compose-an-island-from-cliff-slabs.md](../how-to/compose-an-island-from-cliff-slabs.md)
— using max radius instead of the measured radial profile produces real holes.

## The waterline that isn't a gizmo

**`M_Rocks_2022`, the base material of every Asteria cliff, shades geometry
below world Z = 0 as submerged.** Params: `WaterHeight Z = 0.0`,
`WaterFade = 50`, `Waterline color`, `UnderWater`.

Any part of an Asteria cliff below Z = 0 renders blue — correct for a cliff
standing in the sea, wrong for a floating island. One project spent a session
guessing this blue shape was a Storm Controller gizmo.

The material chain is `MID → MI_Cliff_<piece>_Disp → MI_Cliff_Disp_MASTER →
MI_Cliff_Common → MI_Cliff_MASTER → M_Rocks_2022_RVTTop_Inst → M_Rocks_2022`.
The runtime instance is a transient `MaterialInstanceDynamic` the Blueprint
builds at construction, so it cannot be edited persistently, and authoring a
`MaterialInstanceConstant` child would hard-reference a disallowed `/Game/`
asset and fail validation.

**The fix is geometric: keep these meshes above Z = 0.** One map raised its
entire playfield +4500 for this.

## Other validated rocks

| Asset | Path | Verdict | Verified | Notes |
| --- | --- | --- | --- | --- |
| `Rock_Common_Large_C_Snow`, `Rock_Common_Small_A_Snow` | `/Game/Environments/Asteria/Rocks/Common/Blueprints/Snow/` | valid | 2026-08 | |
| `Asteria_IceFissureChunk_A`, `Asteria_FrozenArch_B` | `/Game/Environments/Asteria/Terrain/Frozen/Props/` | valid | 2026-08 | |
| `CP_Lava_Cliff_a/b/c/d`, `CP_Lava_CliffRock_a` | `/Game/Creative/Items/Lava_Tiles/` | valid | 2026-08 | |
| `CP_AridDunes_Small_Straight`, `CP_AridDunes_Small_Outer` | `/Game/Creative/Environments/Props/Cliffs/` | valid | 2026-08 | |
| `CP_Shoreline_*_NoWater_Snow` | `/Game/Creative/Environments/Props/Cliffs/` | valid | 2026-08 | |
| `CP_Asteria_Foliage_LeafPile_A`, `CP_Asteria_Foliage_LeafScatter_A` | `/Game/Creative/BuildingActors/Props/Asteria/` | valid | 2026-08 | |
| `BP_Oak_Prop_Arid_RockWall_01` | `/Game/Creative/BuildingActors/Props/Oak/` | valid | 2026-08 | 3927 × 2100 × 1549, big rock mass |
| `BP_Oak_Prop_Arid_RockArch_01` | `/Game/Creative/BuildingActors/Props/Oak/` | valid | 2026-08 | 2074 × 874 × 943, natural rock arch |
| `Prop_Cor_Rock_01` | `/Game/Building/ActorBlueprints/Prop/` | **invalid** | 2026-08 | Don't re-try |
| All `LavaRocks` static meshes | — | **invalid** | 2026-08 | Raw meshes; don't re-try |

## There is no publish-safe snow or volcanic cliff slab — don't re-search

**All 168 Blueprint cliff actors in the game were swept and 31 candidates
batch-validated.** The Helios biome cliff kits are exactly the right shape and
would give snow and volcanic terrain directly — and they are all disallowed:

- `/Game/Environments/Helios/Terrain/Cliffs/Blueprints/Boreal/*` — **invalid**
- `/Game/Environments/Helios/Terrain/Cliffs/Blueprints/Brimstone/*` — **invalid**
- `Asteria_SnowDrift_01` / `_02`, `Asteria_IceSheetLakeSmall` — **invalid**
- `Rock_Common_Medium_A_Snow`, every `Rock_Common_*_Ice` — **invalid**
- Every biome ground/floor *mesh* under `/Game/Environments/Sets/*/Meshes/` — **invalid**
- All six biome floor *materials* under `/Game/Environments/Sets/.../Materials/` — **invalid**

Biome identity therefore has to come from **props sitting on top of** a
validated slab body, not from the ground itself.

## Pivots — measure, don't assume

| Asset class | Pivot |
| --- | --- |
| `/Engine/BasicShapes/Cylinder`, `Cone`, `Sphere` | Geometric **centre**. A Cone placed at Z=1000 spans 950–1050 |
| `CP_Asteria_Cliff_Peak_A`, `CP_Asteria_Cliff_Mountaintop_A` | **Base**. Placed at Z=1000, bounds span ~996–3903 |

The default unrotated Cone is **wide-base-down, narrow-apex-up** (radius ~47
near the bottom of its bounds, ~2 near the top) — the opposite of a hanging
stalactite. To hang one point-down, rotate `Rotator(roll=180, pitch=0, yaw=…)`
using keyword arguments, then place at `desired_top_Z - (50 * scale)` since
the pivot is centred. A base-pivot mesh like `Cliff_Peak_A` needs no such
offset — set Z directly.

Scale tall cliff meshes off **target height, not target width**: `Peak_A` is
height:width ≈ 0.65 and `Mountaintop_A` ≈ 1.1, so sizing by width produces a
piece far taller than intended.
