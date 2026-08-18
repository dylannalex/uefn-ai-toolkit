---
name: uefn-knowledge
description: The UEFN/Fortnite knowledge base behind uefn-mcp — validated asset and device class paths (with the confirmed-invalid ones), how-to recipes for scripting devices and Verse, and non-obvious unreal.* gotchas that silently corrupt work. Use before spawning or validating any Fortnite asset, before concluding a device setting or item content can't be scripted, before any bulk transform work, before wiring devices together, when a spawn/move/save appears to succeed but doesn't persist, or whenever a class path or asset needs to be discovered against a live editor.
---

# UEFN knowledge base

Everything here was established by running Python against a live UEFN editor,
usually the hard way. **Read the relevant file before re-investigating
anything** — several entries exist specifically to stop a route from being
re-tried, and one of them cost a four-session detour.

Paths below are relative to this skill's own directory.

## Route by task

| Want to... | Read |
| --- | --- |
| Spawn a tree, rock, cliff, terrain tile or building prop | `../../docs/assets/INDEX.md` — check the roster **before** spawning; the invalid rows matter as much as the valid ones |
| Find a Fortnite device's class path | `../../docs/assets/devices.md` |
| Add or change what item a device spawns/grants | `../../docs/how-to/set-item-spawner-content.md` |
| Decide whether a device setting is scriptable at all | `../../docs/gotchas/user-options.md` (bools/numbers/enums), then `../../docs/gotchas/item-content/overview.md` (item/weapon content specifically) |
| Wire one device to trigger another | `../../docs/gotchas/event-wiring.md` |
| **Move, rescale or reposition placed actors** | `../../docs/gotchas/transform-persistence.md` — **read before any bulk transform work**; moves silently fail to save and leave collision behind |
| Spawn a project's own compiled Verse `creative_device`, or bind a native device into its `@editable` fields | `../../docs/how-to/spawn-and-wire-custom-verse-devices.md` |
| Write Verse that behaves at runtime | `../../docs/gotchas/verse-language.md` |
| Check whether what you built will actually publish | `../../docs/gotchas/validation.md` — `is_object_valid` lies before `save_level` |
| See the map for yourself instead of asking for a screenshot | `../../docs/how-to/screenshot-the-level.md` |
| Build an island or platform out of cliff slabs | `../../docs/how-to/compose-an-island-from-cliff-slabs.md` |
| Set up a new UEFN project for remote execution | `../../docs/internals/setup.md` |
| Debug a silent/failed connection to UEFN | `../../docs/gotchas/misc.md`, then `../../docs/internals/setup.md` |
| Understand or extend the MCP↔bridge↔UEFN plumbing | `../../docs/internals/INDEX.md` |

## The rules that override intuition

These are the ones that cost whole sessions when ignored:

1. **A raw asset that fails validation is not an unavailable asset.** Search
   for its Blueprint actor wrapper before falling back to primitives.
2. **`is_object_valid` is only trustworthy after `save_level`.** A pre-save
   check passes on content that will fail to publish.
3. **`set_actor_location` does not persist** unless the actor is `modify()`d
   first — the editor shows the move, the save reports success, and the
   change is gone on restart.
4. **Fortnite "User Options" are settable** via `set_editor_property` with
   the option's exact key name, despite looking read-only.
5. **Anything you can't find a publish-safe Epic asset for, author yourself**
   under the project's own content root (`/<ProjectName>/...`), which is
   exempt from the Creative allowlist.

## Adding to it

When a session establishes something new, write it down here rather than in
the map's own notes — unless it is only true of that one map. The test:
**would this still be true if the map were deleted?** If yes, it belongs in
this knowledge base; a validated asset path, a platform wall, a dead end
already ruled out. If no — an actor label, a coordinate, a judgement about
how a particular map should look — it belongs in the map's own repository.
