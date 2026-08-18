---
description: Fortnite Creative "User Options" are settable via set_editor_property with the exact key name, not the runtime-only set_user_option_value.
---

# "User Options" ARE settable at edit time — via `set_editor_property`

Fortnite Creative's "V2" device family (Island Settings, Round Settings,
Class Designer, Item Granter, Storm Controller, ...) expose their
Details-panel-configurable settings through a system Epic calls "User
Options." It's easy to conclude these are edit-time read-only:

- `device.get_user_option_definitions()` → returns an opaque
  `UserOptionDefinitionContainerInterface` with no usable Python
  `len()`/iteration. Not useful for enumeration.
- `device.set_user_option_value(player_controller, key, value)` and the
  plural `set_user_option_values(player_controller, values)` **require a
  live `PlayerController`**. Called with `None` in the editor (no PIE
  session running), they silently return `False` and change nothing — this
  looks exactly like "edit-time writes aren't supported," but it's actually
  because these two functions are the *runtime* (Verse-equivalent) override
  API, meant for changing a value mid-match, not the editor-default API.

**The actual edit-time write path is the plain `get_editor_property` /
`set_editor_property` pair, using the option's exact key string as the
property name** — e.g. `device.set_editor_property("bLastStandingWins",
True)`, `storm.set_editor_property("Resize Time", 150.0)` (yes, including
keys containing a literal space). This works because each User Option is
actually backed by a real dynamically-registered `FProperty` on the object,
just one that (a) doesn't go through the usual CamelCase→snake_case
conversion other native properties get, and (b) doesn't show up in
`dir(device)` — so guessing snake_case names or trusting `dir()` output will
both make it look unsupported when it isn't. Always try the **exact**
User-Option key (case-sensitive, spaces included) as a property name before
concluding a setting is Details-panel-only.

For **bulk reads** (e.g. keyword-sweeping a device's full option list),
`device.get_user_option_values()` returns a plain `Map[str, str]` of every
current key→value — far more usable from Python than
`get_user_option_definitions()`.

Enum-valued properties come back as typed enum instances (e.g.
`<BuildingMode.ALL: 3>`). To discover the valid values for one, don't guess
— `list(type(value))` on an already-read value gives every member.

This was verified across `IslandSettings0` (298 options),
`RoundSettings_Main` (39 options), and Item Granter/Storm Controller
instances (dozens each) in the same session — safe to treat as a general
pattern for the whole "V2" device family, not a one-off.

## Exception: actual item/weapon *content* is not covered by this pattern

Picking *which item* an Item Granter grants or an Item Spawner spawns is a
different, much narrower problem — see
[item-content/overview.md](item-content/overview.md) for the full investigation.
The short version: it's not a plain User Option, and the same is true of
device-to-device event wiring — see [event-wiring.md](event-wiring.md).
