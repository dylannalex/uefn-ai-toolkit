---
description: Render the level to a PNG from Python via SceneCapture2D, so Claude can look at the map itself.
---

# Screenshotting the level from Python (works — use `SceneCapture2D`)

Claude can see the map on its own. Spawn a `SceneCapture2D`, point it at a
render target, capture, export the target to PNG, destroy the actor. It is
synchronous, needs no automation framework, does not touch the user's viewport
or window focus, and leaves nothing in the level.

**Do not use `HighResShot` or `AutomationLibrary.take_high_res_screenshot`.**
Both were tried across four separate sessions and produced a file exactly once
between them — `take_high_res_screenshot`'s `is_task_done()` never flips
because it expects the Automation framework's tick, and the `HighResShot`
console command silently no-ops on repeat calls. That dead end is what made
three sessions conclude self-screenshotting was impossible. It isn't; they were
just using the wrong API.

## The recipe

```python
import unreal
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_editor_world()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def shot(out_dir, name, loc, rot, w=1280, h=720, fov=70.0, bias=11.0):
    rt = unreal.RenderingLibrary.create_render_target2d(
        world, w, h, unreal.TextureRenderTargetFormat.RTF_RGBA8)   # see note 1
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
    c = cap.get_editor_property("capture_component2d")
    c.set_editor_property("texture_target", rt)
    c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property("fov_angle", fov)

    pp = unreal.PostProcessSettings()                              # see note 2
    pp.set_editor_property("override_auto_exposure_method", True)
    pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property("override_auto_exposure_bias", True)
    pp.set_editor_property("auto_exposure_bias", bias)
    c.set_editor_property("post_process_settings", pp)

    c.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, out_dir, name)
    eas.destroy_actor(cap)
```

Then read the resulting `.png` with an image-capable file reader.

## Two things that will bite you

**1. The format must be `RTF_RGBA8`, or you get an EXR named `.png`.**
`create_render_target2d` defaults to a 16-bit float format, and
`export_render_target` writes **OpenEXR** for float targets — with whatever
extension you asked for. The file is valid, just not a PNG, and an image
reader will reject it. Tell-tale: the first bytes are `76 2f 31 01`
(OpenEXR's magic) instead of `89 50 4e 47`. Passing `RTF_RGBA8` explicitly
fixes it.

**2. `SceneCapture2D` does not inherit the editor viewport's auto-exposure**,
so a straight capture comes out markedly darker and bluer than what the user
sees on screen — enough to misjudge a lighting or material question. Override
exposure to manual; `auto_exposure_bias = 11.0` matched the UEFN viewport
closely on a bright outdoor map. Re-check the bias if the map's lighting is
very dark or very bright.

## What it does *not* see

`SceneCapture2D` renders the world the way the game renders it, which means
**editor-only gizmos and runtime UI widgets are both invisible to it**. Point
it at a Creative device and you will often capture empty ground: a
`Device_Billboard_V2_C`, for instance, has only an
`EditorOnlyStaticMeshComponent` (the icon you see in the viewport) and a
`Billboard_WidgetComp` (populated at runtime) — neither appears. That is not a
placement bug; check the actor's location and bounds instead, and accept that
its *appearance* needs a real session. The same applies to trigger volumes,
spawn pads and most non-prop devices.

## Verify it left no trace

The capture actor is destroyed and the render target is transient, so actor
count and dirty-package count should both be unchanged across a capture:

```python
len(eas.get_all_level_actors())
len(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
```

Confirmed unchanged (557 actors, 0 dirty) across repeated captures in SkyWars.

## The fallback: capture the Windows screen instead

If you need to see the **editor UI** rather than the scene (a Message Log, a
Details panel, a dialog), `SceneCapture2D` can't help — it renders the world,
not the application. Capture the desktop from PowerShell instead:

```powershell
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
```

This works, but captures whatever is **in front** — usually the editor or IDE,
not necessarily UEFN. Bringing UEFN forward first steals focus from the user,
so prefer `SceneCapture2D` for anything about the map itself and keep this for
UI questions only.
