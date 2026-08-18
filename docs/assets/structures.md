---
description: Publish-safe walls, ruins, props and the two modular building kits — including the log cabin kit's pivots and the yaw rule that costs three iterations to find.
---

# Structures, props and building kits

Checked with `is_object_valid` after `save_level`.

## Props and ruins

Paths are `/Game/Creative/BuildingActors/...` unless noted.

| Asset | Verdict | Verified | Size W×D×H (cm) | Use |
| --- | --- | --- | --- | --- |
| `Props/Coliseum/CP_Coliseum_ExtWall_BotWall_01_NoDestroy` | valid | 2026-08 | 1542 × 475 × 384 | Low ruin wall — **real player cover** |
| `Props/Coliseum/CP_Coliseum_ExtWall_Column_01_NoDestroy` | valid | 2026-08 | 528 × 545 × 2336 | Free-standing column, scale ~0.25 |
| `Props/Coliseum/CP_Coliseum_ExtWall_Wall_01` / `_02` / `_03_NoDestroy` | valid | 2026-08 | 1562 / 2050 / 512 × ~280 × 1536 | Tall ruin walls |
| `Props/CP_Atlantis_QuarterWall_A_06` | valid | 2026-08 | 607 × 53 × 492 | Low wall |
| `Props/CP_Monument` | valid | 2026-08 | 521 × 172 × 148 | Small monument |
| `Props/CP_Farm_Windmill_NoSpinning` | valid | 2026-08 | 355 × 461 × 964 | Rustic landmark: wooden tower, red blades |
| `Props/CP_Wooden_Fence_A_NoSnap` | valid | 2026-08 | 540 × 24 × 159 | Fence segment |
| `Props/CP_Tree_Log_2` / `CP_Tree_Log_4` | valid | 2026-08 | 105×106×159 / 310×229×541 | Stumps and logs |
| `Props/CP_Farm_GrainSilo_Bottom` | valid | 2026-08 | 339 × 333 × 391 | Farm silo base |

## The LogCabin kit — a real rustic wooden house

`/Game/Building/ActorBlueprints/<sub>/<Name>.<Name>_C`. **All 10 pieces spawn
and validate clean.** This is actual logs, unlike the Oak kit below.

| Piece | Size W×D×H | Pivot / notes |
| --- | --- | --- |
| `Wall/LogCabin_Wall` | 512 × 37 × 384 | Base wall; pivot at base, centred on local X |
| `Wall/LogCabin_Wall_Door_Center` / `_Door_Left` | 512 × 47 × 386 | |
| `Wall/LogCabin_Wall_Largewindow` / `_Window_Left` | 512 × 64/52 × 384 | |
| `Corner/BP_FORT_LogCabin_Corner` | 87 × 82 × 384 | Corner post, hides the wall seam |
| `Roof/BP_FORT_LogCabin_Roof1` | 512 × 657 × 514 | **Pivot is the RIDGE**; falls 436 over 600 in +Y |
| `Roof/BP_FORT_LogCabin_Roof2` | 512 × 802 × 320 | Full shallow gable, own ridge at pivot +250 |
| `Roof/BP_FORT_LogCabin_Roof2_Cap` | 788 × 110 × 311 | Ridge cap for `Roof2` (height 224 matches) |
| `Wall/LogCabin_RoofWall` | 650 × 108 × 505 | **Half** gable triangle; high end at local x −250, matches `Roof1`'s slope |
| `Floor/BP_FORT_Logcabin_Floor` | 512 × 512 × 32 | **Pivot is the −Y edge**, centred on X; the slab is centred *vertically* on the pivot, so its top is pivot Z **+16** |

### Three rules, all measured by line-tracing an isolated piece

Bounds do not tell you any of this — each was found by tracing, after being
guessed wrong first.

1. **Which face shows logs is yaw-dependent, and walls and gables disagree.**
   Walls show logs on local **+Y**: for outward-facing logs use S=180, N=0,
   E=270, W=90. `RoofWall` shows logs on local **−Y** — the opposite
   handedness.

2. **`Roof1`'s pivot is the ridge, not the eave.** Both slopes of a gable go at
   the *same* point (the ridge line), one at yaw 0 and one at yaw 180 — not at
   the two wall lines. A 1024-deep house is exactly 2 × (512 wall + 88 eave).

3. **`RoofWall`'s slope direction and its log face are coupled**, so one half of
   each gable end always faces the wrong way. Mirror that half with
   `scale3d.y = -1`; `is_object_valid` accepts the negative scale. Set it via
   `get_actor_transform()` → `set_editor_property("scale3d", …)` →
   `set_actor_transform`; a plain `set_actor_scale3d` repeatedly dropped the
   MCP socket on this actor class while the transform route worked first try.

   **The mirror needs no position compensation.** `scale3d.y = -1` mirrors
   about local Y, and the piece's bounds offset from its pivot along the
   *ridge* axis is unchanged, so all four `RoofWall` halves of a gable end sit
   at exactly the same ridge-axis coordinate — the gable-end wall plane. One
   session shifted the mirrored halves 84 cm to "compensate" and the next had
   to undo it. Verify by symmetry, not theory: the two halves of one gable end
   must report **identical bounds** on the ridge axis.

## The Oak kit — industrial, despite the name

`/Game/Creative/Sets/Oak/BuildingPieces/` is a complete house kit —
`Oak_Floor`, `Oak_Solid_Wall` (`_02`/`_03`), `Oak_Door_S_01`, `Oak_Windows_02`,
`Oak_Window_C`, `Oak_Roof_S`/`_S2`, `Oak_HalfWall_S`, `Oak_Stair_F`. All 11
valid, on a clean **512 grid with 384-tall walls**. Measured pivots: the floor
covers X `p−256..p+256` and Y `p..p+512`; walls run along X centred on the
pivot, base at pivot Z.

**But "Oak" is an industrial POI, not oak wood.** Assembled, it is a dark
corrugated-metal shed. Use it for industrial builds only.

## There is no whole-building prop actor — don't re-search

Sweeping **all 4748 exposed asset paths** for
`house|cottage|cabin|hut|barn|prefab|village|shack` finds no single-actor
building anywhere. (An earlier, narrower search of only `/Game/Creative`
reached the same conclusion for the wrong reason, and missed the LogCabin kit
in `/Game/Building` — which does assemble into one.)

The `Western` family in `BuildingActors/Walls` is 7 trim pieces, not a kit.
Assemble from a module set, or use prop clusters.
