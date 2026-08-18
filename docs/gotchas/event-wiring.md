---
description: Device-to-device event hookups are Details-panel-only from Python; Verse can do it but can't be compiled headlessly.
---

# Device-to-device event wiring

## From Python: any `GameplayEventFunction`/`GameplayEventDescriptor` property is Details-panel-only

Not just item content (see [item-content/overview.md](item-content/overview.md))
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
is. See [item-content/overview.md](item-content/overview.md) for the full
detail.

## New wall (SkyWars, session 10, 2026-08-10): binding a native device to a custom Verse device's `@editable` reference is not Python-settable

This is a *different* gap from the one above — it's not about triggering
one device from another, it's about getting a **custom, project-authored
Verse `creative_device`** (added via Verse Explorer → "Verse Device"
template, compiled once by hand — see the main wiring path this doc
already describes) to hold a reference to a **native** device (Timer V2,
Item Spawner V3, etc.) in one of its own `@editable` fields, from Python,
after compiling.

First, spawning the compiled custom class at all needs a specific
technique — it doesn't show up via `unreal.load_class()` or any
`list_assets` search under `/Game`. It lives in a separate content root
named after the project (from the `.uefnproject`'s `modules` key, e.g.
`/SkyWars/_Verse.global_spawn_alternator`), reachable only via
`unreal.load_object()`. That loaded `VerseClass` object must be passed to
`EditorActorSubsystem.spawn_actor_from_object(cls, location)` — **not**
`spawn_actor_from_class`, which rejects it outright
(`NativizeClass: Cannot nativize 'Class' as 'Class' (allowed Class type:
'Actor')`). The result is a generic `/CRD_VerseDevices/VerseDevice.VerseDevice_C`
actor; the actual Verse instance holding your `@editable` fields lives on
its `Script` sub-object (`actor.get_editor_property("Script")`), typed as
your real Verse class.

Second, `@editable` fields aren't reachable by their plain Verse name on
that `Script` object — the real FName is mangled:
`__verse_0x<8-hex-CRC>_<PropertyName>` (hash isn't derivable by hand,
differs per field). Discover it via
`unreal.JsonObjectGraphFunctionLibrary.stringify([script_obj], options)`
with `options.flags = unreal.JsonStringifyFlags.DISABLE_DELTA_ENCODING` set
— **required**, since the default delta-encoded dump silently omits any
property still at its Verse-side default (an unset `array{}` never
appears without this flag) — then regex `__verse_0x[0-9A-Fa-f]+_<Name>`
over the result.

With the mangled name in hand, **assigning a native device actor to the
property fails**: e.g. a Verse field typed `timer_device` rejects a real
`Device_Timer_V2_C` actor with `NativizeObject: Cannot nativize
'FortCreativeTimerDevice' as 'Object' (allowed Class type: 'timer_device')`.
Unlike custom Verse devices (which expose their instance via the `Script`
sub-object above), native devices have **no** persistent sub-object
implementing their Verse interface anywhere reachable from Python —
confirmed via a full non-delta JSON dump of a `Device_Timer_V2_C` actor
(214k characters, zero hits for `__verse_0x`, "Wrapper", "Interface", or
"timer_device"). Also tried and failed: `unreal.VerseCreativeDevice.cast(actor)`
("Cannot cast type 'FortCreativeTimerDevice' to 'VerseCreativeDevice'");
casting through the loaded `timer_device` VerseClass object directly (the
binding treats this as casting *to* `Class` itself, not to the target
interface type). The native→Verse-interface adapter Epic uses internally
appears to be synthesized somewhere this Python binding can't reach.

**Not yet tested**: whether two custom Verse devices can reference each
other via `@editable` (both sides Verse-authored, so both would have a
`Script` sub-object) — untested because no project so far has needed it.
If you hit this, that's the next thing to check before assuming it's the
same wall.

**Further dig, same session, at the user's request — confirms this is a
real wall, not just an unexplored corner.** Found the actual native→Verse
class mapping: `VerseDeviceWrapperClassMap` assets exist per device
category (e.g. `/CreativeCoreDevices/VerseDeviceWrapperClassMap`,
`/CRD_Bouncer/VerseDeviceWrapperClassMap`, one per `CRD_*`/category
content folder — 136 found project-wide), each holding a `DeviceClassMap`
of native-class-path → Verse-interface-class-path pairs (confirmed:
`/CreativeCoreDevices/Device_Timer_V2.Device_Timer_V2_C` →
`uobject:/CreativeCoreDevices/_Verse.timer_device`, i.e. the interface
class really is the same `timer_device` object already being targeted —
there's no separate hidden wrapper *class* to find). This asset is pure
data (a lookup table), not a callable — `VerseDeviceWrapperClassMap`'s own
Python-exposed methods are just the generic `UObject` set, no
BlueprintCallable "get or create wrapper for actor" function anywhere on
it or reachable from it. Also tried: `unreal.load_class()` on the
built-in `timer_device` path (unlike a project's own custom Verse class,
this **does** return a `Class` object, an asymmetry worth knowing about —
built-in `CreativeCoreDevices` Verse interfaces are apparently registered
with the class loader at UEFN startup, project-specific compiled classes
aren't) — but `.cast()` through that loaded class still fails identically
(`Cannot cast type 'FortCreativeTimerDevice' to 'Class'`, same binding
quirk as casting through a `load_object`-obtained class: `.cast()` is a
classmethod bound to `type(self)`, i.e. plain `unreal.Class`, not to the
specific class instance you loaded — there is no compiled-in Python type
`unreal.timer_device` to call `.cast()` *on* correctly). Also tried
`spawn_actor_from_object` on the interface class itself (returns `None` —
interfaces aren't standalone-spawnable, unsurprising in hindsight).
**Conclusion after this second pass: the actual object that satisfies a
`timer_device`-typed property is created by a C++-only function inside
the `VerseDevices` module, not exposed to Blueprint or Python reflection
under any name/path tried.** Treat this as a confirmed wall, not an
unexplored corner, until someone finds a genuinely different angle (e.g.
decompiling/inspecting the `VerseDevices` module's C++ source directly,
which is out of scope for `execute_python` investigation).

**Possible escape hatch, not yet validated by any project**: Verse's
`FindCreativeObjectsWithTag` lets a `creative_device` look up any tagged
`creative_object` at runtime with no `@editable` reference at all — would
sidestep this wall entirely if adopted. Caveat: it reads **Verse tags**
specifically, routed through `VerseTagMarkupComponent`/`VerseGameplayTag`
— confirmed *different* from plain `AActor.Tags` (that one **is** a
plain, Python-settable `FName` array via `get_editor_property("tags")`,
but it is very likely not what `FindCreativeObjectsWithTag` reads).
Whether Verse tags specifically are Python-settable hasn't been checked by
any project yet — verify that before committing to this path, since it
also requires a Verse code rewrite and one more manual recompile either
way.
