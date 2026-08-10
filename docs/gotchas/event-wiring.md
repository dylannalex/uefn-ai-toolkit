# Device-to-device event wiring

## From Python: any `GameplayEventFunction`/`GameplayEventDescriptor` property is Details-panel-only

Not just item content (see [item-content/index.md](item-content/index.md))
— **any** User Option whose value reads back as a `GameplayEventFunction` or
`GameplayEventDescriptor` struct (empty `to_dict()`, `export_text()` showing
`DefaultHandlerFunctions=()`/`EventSubscriptions=()` when unwired) is a
Verse/Details-panel event-graph hookup, not a plain settable value —
regardless of which device it's on. Confirmed on a second device pair
(SkyWars project, Timer V2 → ItemSpawner V3): `Timer_GlobalSpawnEvent`'s
`Start`/`Complete`/`OnSuccess`/etc. and the receiving `ItemSpawner`'s
`Enable`/`Spawn Item`/`Cycle to Next Item` are all the same empty struct
shape, and neither device exposes any "Channel"/broadcast-style property as
an alternative. So: triggering one device from another (Timer → Spawner,
Button → Granter, etc.) needs the Details panel's event-graph UI, the same
as item-content selection. Quick test for any option that looks like it
might be a trigger/hookup: read it with `get_editor_property`, check
`type(value).__name__` — if it's `GameplayEventFunction`/
`GameplayEventDescriptor` (not a bool/float/str/enum), assume
Details-panel-only without further probing.

## From Verse: it's actually possible, just not headlessly triggerable

The Python restriction above is true **for the `execute_python` editor API
specifically** — it is not true for Verse. Verse devices can `Subscribe()`
to another device's event and call functions on a third device (confirmed
against Epic's own "Coding Device Interactions in Verse" docs and a real
community device on GitHub) — e.g. a Timer's `SuccessEvent` triggering an
ItemSpawner's `SpawnItem()`. So wiring that looks Details-panel-only from
Python may still be fully scriptable via a custom Verse device instead of
the event-graph UI.

The catch is narrower than "needs the Details panel": **compiling Verse
code (`Verse > Build Verse Code` / Ctrl+Shift+B) has no scriptable
trigger.** Checked directly:

- `dir(unreal)` inside a connected editor has no Verse-build-related class
  or subsystem (`VerseIntegrationEditorSubsystem` doesn't exist; nothing
  else in the ~140 `Verse*`-named classes is compile-related).
- No documented CLI/headless build path exists. Epic's own **Lore CLI**
  (the version-control system backing every UEFN project's `.lore` folder)
  only covers `repository`/`branch`/`revision`/`file`/`status`/`clone` — no
  build verb — and explicitly can't run while the project is open in the
  editor anyway, which rules it out for anything needing a live connection.
- The only lead is the local debug protocol (port 1961) the official Verse
  VS Code extension uses to push/build code against a running UEFN
  session — undocumented and not something to reverse-engineer to spoof a
  build trigger (unsupported, likely fragile across UEFN versions, and it'd
  mean bypassing Epic's own tooling gate rather than using a public API).

Practical result: writing the Verse device is fully doable headlessly (a
text file); one human click (Build) is unavoidable; but everything after
that — spawning the compiled device and binding its `@editable` properties
— is `execute_python`-scriptable again, since `@editable` Verse properties
are plain object-reference UPROPERTYs on the generated class, same as every
other device's User Options ([user-options.md](user-options.md)).

**Item content specifically remains a confirmed dead end** even accounting
for this: Epic's own `item_spawner_device` Verse API reference has no
function to set which item is configured (`SpawnItem`/`CycleToNextItem`/
`Enable`/`Disable`/respawn-timer setters only) — same wall as the Python
side, so this one isn't a Verse workaround candidate the way event wiring
is. See [item-content/index.md](item-content/index.md) for the full
detail.
