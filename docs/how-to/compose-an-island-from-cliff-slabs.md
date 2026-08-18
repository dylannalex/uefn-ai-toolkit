---
description: Build a round platform out of rotated cliff slabs by measuring the radial profile, and verify the result with traces rather than bounds.
---

# Composing a platform from rotated cliff slabs

Several Asteria cliff pieces have a flat plateau on top with the face
dropping away around it (see
[../assets/rocks-and-cliffs.md](../assets/rocks-and-cliffs.md)), so N rotated
copies of one piece make a round platform that is both surface and sides.

The naive version — place N copies at the piece's max radius — **produces real
holes**. One rollout dropped to Z=533 through gaps that were not visible from
above. The method below is what worked.

## 1. Find the plateau centroid, not the pivot

Trace a grid over an isolated copy of the piece and take the centroid of the
samples that land on the plateau. **Position by that centroid**, not by the
pivot or the bounds centre — rotated copies positioned by pivot do not stack
concentrically, because the pivot is not at the plateau's middle.

## 2. Measure the radial profile

From that centroid, cast rays outward every 5°, walking out in 25 cm steps,
and **stop at the first non-plateau sample**. Contiguity is the point: a
detached scrap of geometry beyond a gap is not usable ground, and a max-radius
measurement counts it.

## 3. Combine the profiles

For N copies rotated evenly, the union profile at angle `i` is:

```
union[i] = max(prof[i - k * 72 / N] for k in range(N))
```

The platform's **safe playable radius is the minimum of that union** — the
worst angle, not the average.

Measured for two pieces:

| Piece | N=4 | N=6 | max radius |
| --- | --- | --- | --- |
| `CP_Asteria_Cliff_Small_Corner_180_B` | 1350 | **1625** | 1875 |
| `CP_Asteria_Cliff_Mud_Small_Straight_A` | 1050 | **1150** | 1250 |

**N=8 buys nothing over N=6** for either piece.

## 4. Keep it above Z = 0

Every Asteria cliff uses `M_Rocks_2022`, which shades geometry below world
Z = 0 as submerged — a floating platform built at negative Z renders blue and
there is no material fix. See
[../assets/rocks-and-cliffs.md](../assets/rocks-and-cliffs.md).

## 5. Verify with traces, and assert on the right height

- **Move with `set_actor_transform`**, which handles the persistence and
  collision traps. A raw `set_actor_location` leaves the collision body behind,
  so the platform renders correctly and isn't standable. See
  [../gotchas/transform-persistence.md](../gotchas/transform-persistence.md).
- **A hole check must assert on the expected surface height**, not on a floor
  value. Written as `z < <some floor>` it returns "no holes" while every trace
  is landing on something else entirely — in one case a hidden safety disc
  15 cm below the intended terrain, which produced a false "0 holes" result.
- **Pass every non-terrain actor in the trace ignore list.** `line_trace_multi`
  stops at the first blocking hit, so props intercept the ray and the sweep
  reports ground "missing" over solid terrain — 40% of an island, in one case.
  See [../gotchas/misc.md](../gotchas/misc.md) for the trace API's shape.

## Seating props on the result

When placing a prop on the surface, put the prop itself in the trace ignore
list too — otherwise the trace hits the prop, or a neighbouring canopy, and
reports nonsense. One session re-seated 35 props that had been placed on top
of other props this way.

Add the asset's `bottomOffset` (see
[../assets/trees-and-foliage.md](../assets/trees-and-foliage.md)) to the traced
ground Z to seat its bounds bottom on the surface.
