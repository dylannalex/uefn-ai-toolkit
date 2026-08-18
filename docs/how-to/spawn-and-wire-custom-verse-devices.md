---
description: Spawning a project's own compiled Verse creative_device, reading/writing its @editable fields, and the Verse-tag workaround for the native-device binding wall.
---

# How to spawn and wire a custom (project-authored) Verse device

**Status: spawning, reading/writing `@editable` scalars, and the full Verse-tag workaround (declare → compile → add `VerseTagMarkup` component → set its tag → `FindCreativeObjectsWithTag` in Verse) are all confirmed working (SkyWars, session 10, 2026-08-10 — compiled clean, 32/32 actors tagged and read back correctly, level saved).** Binding a native device directly into an `@editable` object reference remains a confirmed wall — the tag workaround is what routes around it. **Not yet confirmed by a playtest** that the alternator/drip logic behaves correctly at runtime, only that every step up through tagging and saving worked. See [gotchas/event-wiring.md](../gotchas/event-wiring.md) for the full investigation trail this doc summarizes.

## Scope — read this first

This is about a **project's own Verse-authored `creative_device` class** (added via UEFN's Verse Explorer → "Add Verse File to Project" → "Verse Device" template, compiled once by hand — see "Compiling" below), not a native Fortnite Creative device. Once such a class is compiled:

| Task | Scriptable? |
| --- | --- |
| Spawning an instance of it | **Yes** — needs a specific technique, not the obvious one (see Part 1) |
| Reading/writing its `@editable` **scalar** fields (`float`, `int`, `logic`, `string`) | **Yes** — same as any other device's User Options, once you have the mangled property name (Part 2) |
| Binding a **native** device actor (Timer, Item Spawner, etc.) into an `@editable` field typed as that device's Verse interface (`timer_device`, `item_spawner_device`, ...) | **No** — confirmed wall, see [gotchas/event-wiring.md](../gotchas/event-wiring.md) |
| Binding one **custom Verse device** to another's `@editable` field | Untested — no project has needed it yet |
| Working around the native-device-binding wall via Verse tags instead of `@editable` refs | **Written, staged, not yet compile-verified** — see Part 4 |
| Compiling/recompiling Verse code itself | **No** — no scriptable trigger exists, confirmed dead end (see [gotchas/event-wiring.md](../gotchas/event-wiring.md)'s "From Verse" section). Always a manual `Verse > Build Verse Code` (Ctrl+Shift+B) click. |

## Part 1 — spawning a compiled custom Verse device

The compiled class does **not** show up via `unreal.load_class()`, and does **not** appear in any `list_assets`/asset-registry search under `/Game`. It lives in a separate content root named after the project itself (from the `.uefnproject`'s `bindings.modules` key — e.g. a project called "SkyWars" gets root `/SkyWars`), specifically under a `_Verse` package: `/<ProjectName>/_Verse.<verse_class_name>`.

```python
import unreal

cls = unreal.load_object(None, "/SkyWars/_Verse.global_spawn_alternator")
# unreal.load_class(None, same_path) returns None for a project's own
# compiled Verse class — don't use it here.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actor = actor_sub.spawn_actor_from_object(cls, unreal.Vector(0, 0, 0))
# spawn_actor_from_class(cls, location) FAILS for this:
#   NativizeClass: Cannot nativize 'Class' as 'Class' (allowed Class type: 'Actor')
# spawn_actor_from_object is the one that works.
```

The result is a generic actor of class `/CRD_VerseDevices/VerseDevice.VerseDevice_C` — **not** a class named after your Verse device. The real instance, holding your `@editable` fields, lives on a `Script` sub-object:

```python
script_obj = actor.get_editor_property("Script")
print(script_obj.get_class().get_path_name())  # -> /SkyWars/_Verse.global_spawn_alternator
```

## Part 2 — reading/writing `@editable` fields

`@editable` fields aren't reachable by their plain Verse name on `script_obj` — the real `FName` is mangled: `__verse_0x<8-hex-CRC>_<PropertyName>` (the hash isn't derivable by hand and differs per field/class). Discover it with a full, non-delta-encoded JSON dump:

```python
opt = unreal.JsonStringifyOptions()
opt.set_editor_property("flags", unreal.JsonStringifyFlags.DISABLE_DELTA_ENCODING)
# DISABLE_DELTA_ENCODING is required — the default delta-encoded dump
# silently omits any property still at its Verse-side default value
# (e.g. an unset `array{}`), so those never appear without this flag.
j = unreal.JsonObjectGraphFunctionLibrary.stringify([script_obj], opt)

import re
for m in re.finditer(r'__verse_0x[0-9A-Fa-f]+_(\w+)', j):
    print(m.group(0))  # e.g. __verse_0x69AF1449_SpawnTimer
```

Once you have the mangled name, `get_editor_property`/`set_editor_property` on `script_obj` work exactly like any other device property, **for scalars**:

```python
script_obj.set_editor_property("__verse_0x69FC4F75_DripInterval", 12.0)  # works fine
```

For an `@editable X : timer_device` (or any native-device-typed) field, this is where you hit the wall — see Part 3.

## Part 3 — the wall: native device → custom Verse `@editable` reference

```python
timer_actor = ...  # a real Device_Timer_V2_C instance
script_obj.set_editor_property("__verse_0x69AF1449_SpawnTimer", timer_actor)
# NativizeObject: Cannot nativize 'FortCreativeTimerDevice' as 'Object'
# (allowed Class type: 'timer_device')
```

Unlike a custom Verse device (which exposes its instance via the `Script` sub-object from Part 1), a **native** device actor has no persistent sub-object anywhere reachable from Python that implements its Verse interface — confirmed via a full non-delta JSON dump (zero hits for `__verse_0x`, "Wrapper", "Interface", or the interface class name). The native→Verse-interface adapter is created by a C++-only function inside the `VerseDevices` module; every angle tried to reach it from Python failed (direct assignment, path-string assignment, `unreal.VerseCreativeDevice.cast()`, casting through the loaded interface class via both `load_object` and `load_class`, inspecting `VerseDeviceWrapperClassMap` — the real native-class→interface-class lookup table, but pure data, no callable). Full blow-by-blow in [gotchas/event-wiring.md](../gotchas/event-wiring.md).

**Do not re-attempt this from scratch** — re-read the gotchas doc first if you think you've found a new angle, since several plausible-looking ones are already ruled out there.

## Part 4 — the workaround: Verse tags instead of `@editable` refs

Since native devices can't be bound into `@editable` fields from Python, have the Verse code discover its targets **at runtime by tag** instead. This needs one more manual Verse compile (tags are declared in Verse), but after that, tagging every target actor is fully scriptable.

### 4a. Declare the tag(s) in Verse

```verse
using { /Verse.org/Simulation/Tags }

my_target_tag := class(tag){}
```

A tag is just a Verse class deriving from `tag`. Put these in their own small `.verse` file or alongside a device file — same-project files share one flat module scope by default, so other `.verse` files in the project can reference the tag class without an explicit `using` for it (assumed from this project's existing files not cross-referencing each other; not independently re-verified).

### 4b. Look targets up in the device's `OnBegin`

```verse
using { /Fortnite.com/Devices }

my_device := class(creative_device):
    var Target : ?timer_device = false

    OnBegin<override>()<suspends> : void =
        for (Obj : FindCreativeObjectsWithTag(my_target_tag{})):
            if (T := timer_device[Obj]):
                set Target = option{T}
```

`FindCreativeObjectsWithTag` is `(InCreativeDevice:creative_device).FindCreativeObjectsWithTag(tag_type:castable_subtype(tag))<transacts>:generator(creative_object_interface)` — called as `Self.FindCreativeObjectsWithTag(...)` (or unqualified from within a `creative_device` method, sugar for the same). Cast each `creative_object_interface` result to the concrete device type with the same failable bracket syntax used everywhere else in this codebase for fallible conversions: `item_spawner_device[Obj]`, `timer_device[Obj]`, etc. — it silently filters out non-matching objects rather than erroring.

For multiple same-tagged targets (e.g. building an array), the `for` comprehension pattern combining an iteration clause with a cast clause works the same way arrays/maps do elsewhere in this codebase — remember the established rule that the yielded body must be on its own indented line, never inline after the `:`:

```verse
set Targets = for (Obj : FindCreativeObjectsWithTag(my_target_tag{}), T := item_spawner_device[Obj]):
    T
```

### 4c. Assign the tag to each target actor — this part is scriptable

Assigning a Verse tag in the Details panel means adding a **`VerseTagMarkup` component** to the actor and populating its tag list. Both steps are doable from Python:

**Add the component** (confirmed working — this is the same call the Details panel's "Add Component" button uses under the hood):

```python
sub_sys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
# NOTE: engine subsystem, not editor subsystem — get_editor_subsystem
# rejects SubobjectDataSubsystem outright.

handles = sub_sys.k2_gather_subobject_data_for_instance(target_actor)
root_handle = handles[0]

params = unreal.AddNewSubobjectParams()
params.set_editor_property("parent_handle", root_handle)
params.set_editor_property("new_class", unreal.VerseTagMarkupComponent)
handle, fail_text = sub_sys.add_new_subobject(params)
# fail_text is an empty Text on success
```

**Set the tag value** (confirmed working end to end — 32/32 actors tagged and read back correctly, SkyWars session 10):

```python
tag_cls = unreal.load_object(None, "/SkyWars/_Verse.my_target_tag")  # same load pattern as Part 1

tag_markup = target_actor.get_components_by_class(unreal.VerseTagMarkupComponent)[0]
tag_info = unreal.VerseTagTypeInfo()
tag_info.set_editor_property("InternalTag", tag_cls)

tag_container = tag_markup.get_editor_property("InternalTags")  # a VerseTagTypeInfoContainer struct
tag_container.set_editor_property("InternalTags", [tag_info])
tag_markup.set_editor_property("InternalTags", tag_container)
```

`VerseTagTypeInfoContainer.InternalTags` is an array of **`VerseTagTypeInfo` structs**, not raw class references directly — passing `[tag_cls]` straight into it fails (`NativizeStructInstance: Cannot nativize 'Class' as 'VerseTagTypeInfo'`). Each `VerseTagTypeInfo` wraps a single `ClassProperty` field, `InternalTag` (allowed base class `VerseTagBase` — i.e. any tag class, like `my_target_tag` itself, not an instance of it). Both the wrapper-struct requirement and the `InternalTag` field name were discovered the same way as any unknown property: construct a default struct/component, try a wrong-typed `set_editor_property` on a guessed field name, and read the allowed-class type out of the resulting `NativizeClass`/`NativizeStructInstance` error text.

Read back to confirm: `tag_markup.get_editor_property("InternalTags").get_editor_property("InternalTags")` gives the list of `VerseTagTypeInfo` structs back; each one's `.get_editor_property("InternalTag")` gives the tag class object, whose `.get_path_name()` should match what you set.

## Compiling

No scriptable trigger exists for `Verse > Build Verse Code` — this is a hard platform wall, not a missing wrapper (see [gotchas/event-wiring.md](../gotchas/event-wiring.md)'s "From Verse" section for what was ruled out: no `unreal`-exposed Verse-build subsystem, no headless CLI verb, the Lore CLI explicitly can't run alongside an open editor). Every device class change, and every new/changed tag declaration, needs a human to click Build in UEFN before any of the above works.
