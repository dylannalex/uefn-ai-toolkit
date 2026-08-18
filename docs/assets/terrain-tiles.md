---
description: The Creative Nature Tiles gallery — 300 publish-safe terrain tiles, their edge pivot, and the scale at which they stop looking right.
---

# Terrain tiles

`/Game/Creative/Items/Nature_Tiles/<Name>.<Name>_C` — around 300 Blueprints,
found by sweeping all 193 `FortExposedAssetList` assets for terrain keywords.
Real Fortnite ground with real texture, unlike a flat-colour material.

**All 17 tested came back valid** post-`save_level`:

| Asset | Verdict | Verified |
| --- | --- | --- |
| `BP_Grass_Temp_Solid`, `BP_Grass_Temp_Solid1` | valid | 2026-08 |
| `CP_ColorGrass_Solid_Full`, `CP_ColorGrass_FullGrass` | valid | 2026-08 |
| `BP_Forest_Solid` | valid | 2026-08 |
| `BP_Sand_Solid`, `BP_Sand_Solid_b`, `BP_WavySand_Solid` | valid | 2026-08 |
| `BP_Snow_Solid`, `BP_Snow_Solid_b`, `BP_Ice_Solid` | valid | 2026-08 |
| `BP_Lava_Solid`, `BP_Lava_Grass_Solid_a` | valid | 2026-08 |
| `BP_Rock_Solid`, `BP_Gravel_Solid` | valid | 2026-08 |
| `BP_Mud_Temp_Solid`, `BP_Dirt_Temp_Solid`, `BP_Snow_Mud_Solid` | valid | 2026-08 |
| `S_CobbleStone_Solid` | valid | 2026-08 |

Transition and corner variants exist for most pairs. **There is no snow→grass
transition tile** — snow transitions exist only to gravel, mud and ice.

## The pivot is on the tile edge, not the centre

**+256 in local Y.** Rotating tiles by random multiples of 90° to vary them
*orbits* each tile half a tile-width instead of spinning it in place,
producing scattered slabs with gaps between them.

To place a tile whose **centre** should land on `(cx, cy)` at yaw `t`:

```python
loc = (cx + 256 * sin(t), cy - 256 * cos(t))
```

Confirmed identical on every tile tested **except `CP_ColorGrass_FullGrass`,
whose pivot is centred** — measure per asset rather than assuming.

The walkable face sits at **pivot + 4** on essentially all of them
(`CP_ColorGrass_FullGrass` is +0.4), so a tile placed at `Z = surface - 4`
needs nothing else moved.

## Where they work, and where they don't

These are authored to be seen at player height across a **large flat area**.
Viewed from above on a small island they render as a flat checkerboard with
every seam visible — worse than plain ground.

One project covered a 26 m island's plateau with terrain-fitted scale-0.5 snow
tiles and reverted it; three separate attempts at a tile ground layer on small
islands were rejected there. Use them for large flat ground, not as a biome
cap on a small platform.

Note also that self-authored flat-colour materials were built for this job and
turned out to be unnecessary — the tiles are publish-safe and look better. See
[../gotchas/validation.md](../gotchas/validation.md) for authoring custom
content under the project root, which remains the right escape hatch when no
Epic asset fits.
