---
description: The full multi-pass investigation into whether item/weapon content is ever scriptable — read before re-testing anything here.
---

# Can UEFN item/weapon content ever be set via script?

**RESOLVED 2026-08-09, partially.** Confirmed scriptable for
`Device_ItemSpawner_V3_C` (chests, global-spawn pads) via
`Minigame_Spawner_Component.ToSpawnList`, survives a real editor restart —
see [../../how-to/set-item-spawner-content.md](../../how-to/set-item-spawner-content.md)
for the working method. **Still confirmed unscriptable for
`Device_ItemGranter_V2_C`** — its equivalent component
(`PickupItemListComponent_C.ItemList`) rejects instance writes with the
same error shape that used to block the Item Spawner path too.

If you just want to *use* the working method, go straight to the how-to
doc linked above. What follows is the full multi-pass investigation record
— read it before re-testing anything that looks like a dead end below, and
before starting new research on this topic (e.g. Item Granter, or any
other item-holding device not yet checked).

## The investigation, in order

1. [Exception and five ruled-out routes](01-exception-and-ruled-out-routes.md)
   — the initial finding that item content isn't a plain User Option, plus
   the first round of dead ends (Verse asset reflection, Item Granter
   Verse API, community tooling, Custom Items system, FField enumeration).
2. [Second pass: independent corroboration](02-second-pass-corroboration.md)
   — no live editor available, so this pass cross-checked the conclusion
   against other tools/docs instead, and surfaced one untested lead
   (`device_deep_options`).
3. [Third pass: live-editor tests](03-third-pass-live-tests.md) — tried the
   two remaining leads with a live editor (both dead ends), found a
   non-viable BR-chest lever, and stated the K-not-N duplication hypothesis.
4. [Correction, and `FortPickupCreative`](04-live-session-and-fortpickupcreative.md)
   — corrected the assumption about *how* item registration works (it's a
   live Play-session action, not an edit-time UI action), then chased and
   disproved a promising-looking `FortPickupCreative` shortcut.
5. [The real backing property, and the confirmed fix](05-real-property-and-itemspawner-v3-confirmed.md)
   — found the actual (read-only) backing property via a new enumeration
   technique, then found and restart-confirmed the real writable one
   (`ToSpawnList`). **This is where the question resolves.**
6. [Historical trail: how `ToSpawnList` was found](06-pending-verification-historical-trail.md)
   — the original in-the-moment writeup from before the restart test in
   pass 5 confirmed it, kept for the discovery narrative.

## What "done" would look like for the remaining gap (Item Granter, others)

Not yet done: a dedicated `@mcp.tool()` (e.g. `set_item_spawner_content`) in
`src/uefn_mcp/server.py` wrapping the working Item Spawner V3 method — see
[../../internals/architecture.md](../../internals/architecture.md) for how existing tools are
structured. Also not done: finding a scriptable path for Item Granter or
any other item-holding device.

- **If a working method is found for a device not covered above**:
  demonstrate it against a real device in a connected UEFN editor, with the
  exact code that worked. Turn it into a new `@mcp.tool()`, document the
  finding as a new numbered pass in this folder, and note that any project
  currently working around this manually (e.g.
  `personal/fortnite-maps/SkyWars/docs/manual-assignment-sheet.md`) can
  drop that workaround for the newly-covered device.
- **If it's confirmed impossible** (with real new evidence, not just
  re-asserting prior findings): append that evidence as a new numbered pass
  in this folder, in the same style as what's already there — specific,
  cited, reproducible — so the next attempt doesn't have to start from zero
  either.

A live UEFN editor with an open project is needed to test anything
empirically (this repo's `execute_python`/`get_editor_status`/etc. tools
require a connected editor). If none is available, note that limitation
rather than reasoning about the editor's behavior from documentation alone
— several passes above did exactly that and it's clearly marked where it
happened.
