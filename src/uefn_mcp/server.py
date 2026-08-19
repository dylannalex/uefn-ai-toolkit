"""MCP server exposing UEFN (Unreal Editor for Fortnite) level-editing tools.

Talks to a running UEFN editor instance over the Python Editor Script Plugin's
remote execution protocol. The editor must be open with a project loaded and
"Remote Execution" enabled for the Python plugin (see README.md).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import remote_execution as re
from .bridge import UEFNConnectionError, extract_output_text, get_bridge

mcp = MCPServer("uefn-mcp")

Vec3 = dict[str, float]


# ---------------------------------------------------------------------------
# Project setup (local filesystem only — no running editor/connection needed)
# ---------------------------------------------------------------------------

_REMOTE_EXEC_SECTION = "/Script/PythonScriptPlugin.PythonScriptPluginSettings"
_REMOTE_EXEC_SETTINGS = {
    "bRemoteExecution": "True",
    "RemoteExecutionMulticastGroupEndpoint": "239.0.0.1:6766",
    "RemoteExecutionMulticastBindAddress": "127.0.0.1",
    "RemoteExecutionMulticastTtl": "0",
}


def _apply_remote_execution_settings(text: str, force: bool) -> tuple[str, bool, list[str]]:
    """Ensure a DefaultEngine.ini's contents have the Python remote execution
    section/keys set, editing around whatever else is already in the file.

    Returns (new_text, changed, conflicting_keys).
    """
    lines = text.splitlines()
    header = f"[{_REMOTE_EXEC_SECTION}]"
    section_start = next((i for i, line in enumerate(lines) if line.strip() == header), None)

    if section_start is None:
        block = [header] + [f"{k}={v}" for k, v in _REMOTE_EXEC_SETTINGS.items()]
        pad = [""] if lines and lines[-1].strip() else []
        new_lines = lines + pad + block
        return "\n".join(new_lines) + "\n", True, []

    section_end = len(lines)
    for i in range(section_start + 1, len(lines)):
        if lines[i].strip().startswith("["):
            section_end = i
            break

    existing: dict[str, tuple[int, str]] = {}
    for i in range(section_start + 1, section_end):
        if "=" in lines[i]:
            key, _, value = lines[i].partition("=")
            existing[key.strip()] = (i, value.strip())

    changed = False
    conflicts: list[str] = []
    insert_at = section_end
    for key, desired in _REMOTE_EXEC_SETTINGS.items():
        if key in existing:
            idx, current = existing[key]
            if current != desired:
                if force:
                    lines[idx] = f"{key}={desired}"
                    changed = True
                else:
                    conflicts.append(key)
        else:
            lines.insert(insert_at, f"{key}={desired}")
            insert_at += 1
            section_end += 1
            changed = True

    return "\n".join(lines) + "\n", changed, conflicts


def _ensure_python_scripting_enabled(data: dict) -> bool:
    """Ensure a parsed .uefnproject JSON has Python Scripting turned on
    (`dataSets.experimental.pythonExperimental.bEnablePythonForProject`).

    This is UEFN's "Python Scripting" toggle under Project Settings > Python
    — a *separate* switch from the DefaultEngine.ini remote-execution keys
    `_apply_remote_execution_settings` writes. Remote execution has no effect
    until this one is also on; without it, `bRemoteExecution=True` silently
    does nothing and the editor never listens for a connection. Returns
    whether a change was made.
    """
    python_experimental = (
        data.setdefault("dataSets", {}).setdefault("experimental", {}).setdefault("pythonExperimental", {})
    )
    if python_experimental.get("bEnablePythonForProject") is True:
        return False
    python_experimental["bEnablePythonForProject"] = True
    return True


def _find_uefn_projects(root: Path, max_depth: int) -> list[Path]:
    root_depth = len(root.parts)
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if len(Path(dirpath).parts) - root_depth >= max_depth:
            dirnames[:] = []
        found.extend(Path(dirpath) / name for name in filenames if name.endswith(".uefnproject"))
    return found


@mcp.tool()
def find_uefn_projects(search_paths: list[str] | None = None, max_depth: int = 6) -> list[dict]:
    """Search the filesystem for UEFN projects (folders containing a
    `.uefnproject` file), so a project can be located without needing its
    path hardcoded or guessed at.

    Args:
        search_paths: Directories to search under. Defaults to the current
            user's home directory when not given — pass explicit path(s)
            (e.g. a known projects folder) for a faster, narrower search.
        max_depth: How many directory levels below each search path to
            descend. Kept shallow by default since a full home-directory
            walk is slow.

    Returns:
        List of dicts with `project_file` and `project_root` for each
        `.uefnproject` found.
    """
    roots = [Path(p).expanduser() for p in search_paths] if search_paths else [Path.home()]
    seen: set[Path] = set()
    results = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in _find_uefn_projects(root, max_depth):
            if path in seen:
                continue
            seen.add(path)
            results.append({"project_file": str(path), "project_root": str(path.parent)})
    return results


@mcp.tool()
def setup_uefn_project(project_path: str, force: bool = False) -> dict:
    """One-time setup that enables Python scripting + remote execution for a
    UEFN project, so this MCP server can connect to it once opened in the
    editor. Two independent switches have to be on, and this flips both:

    1. **Python Scripting itself** (Project Settings > Python in the UEFN
       UI) — sets `bEnablePythonForProject=true` under
       `dataSets.experimental.pythonExperimental` in the `.uefnproject` JSON.
       Without this, the plugin isn't even active, so remote execution has
       no effect regardless of what the ini says.
    2. **Remote execution** for that plugin — writes/updates
       `Config/DefaultEngine.ini` with the
       `[/Script/PythonScriptPlugin.PythonScriptPluginSettings]` section
       (bRemoteExecution=True and the multicast discovery settings), leaving
       any other settings already in that file untouched.

    Both are local file edits only — neither requires UEFN to be running.
    Both are only read at editor startup, so the editor must be (re)started
    afterward for either to take effect.

    Args:
        project_path: Path to the UEFN project folder (the one containing
            the `.uefnproject` file), or the `.uefnproject` file itself.
        force: If the ini already sets one of its keys to a different
            value, overwrite it. Otherwise such conflicts are left alone and
            reported back instead of being changed. Has no effect on the
            `.uefnproject` Python Scripting flag, which is only ever turned
            on, never overwritten.

    Returns:
        dict with `success`, `project_file`, `ini_path`, `changed` (bool,
        true if either file was modified), `python_scripting_enabled`
        (bool, whether the `.uefnproject` flag needed setting),
        `conflicts` (ini keys left unchanged because they already had a
        different value), and `restart_required`.
    """
    p = Path(project_path).expanduser()
    if p.is_file() and p.suffix == ".uefnproject":
        project_root = p.parent
    elif p.is_dir():
        project_root = p
    else:
        return {"success": False, "error": f"Path not found: {project_path}"}

    uefnprojects = list(project_root.glob("*.uefnproject"))
    if not uefnprojects:
        return {
            "success": False,
            "error": (
                f"No .uefnproject file found in {project_root}. Pass the "
                "project folder that contains it, or the .uefnproject file itself."
            ),
        }

    uefnproject_path = uefnprojects[0]
    project_data = json.loads(uefnproject_path.read_text(encoding="utf-8"))
    python_scripting_enabled = _ensure_python_scripting_enabled(project_data)
    if python_scripting_enabled:
        serialized = json.dumps(project_data, indent="\t").replace("\n", "\r\n")
        uefnproject_path.write_text(serialized, encoding="utf-8")

    config_dir = project_root / "Config"
    config_dir.mkdir(exist_ok=True)
    ini_path = config_dir / "DefaultEngine.ini"

    existing_text = ini_path.read_text(encoding="utf-8") if ini_path.exists() else ""
    new_text, ini_changed, conflicts = _apply_remote_execution_settings(existing_text, force)

    if ini_changed:
        ini_path.write_text(new_text, encoding="utf-8")

    changed = python_scripting_enabled or ini_changed

    if conflicts:
        message = (
            f"Existing conflicting values for {conflicts} were left unchanged; "
            "call again with force=True to overwrite them."
        )
    elif changed:
        message = "Python scripting + remote execution enabled. Restart UEFN for it to take effect."
    else:
        message = "Python scripting and remote execution were already enabled; no changes made."

    return {
        "success": True,
        "project_file": str(uefnproject_path),
        "ini_path": str(ini_path),
        "changed": changed,
        "python_scripting_enabled": python_scripting_enabled,
        "conflicts": conflicts,
        "restart_required": changed,
        "message": message,
    }


# ---------------------------------------------------------------------------
# Raw escape hatch
# ---------------------------------------------------------------------------


@mcp.tool()
def execute_python(code: str, mode: str = "file") -> dict:
    """Run arbitrary Python code inside the UEFN editor's `unreal` module.

    Use this to explore the editor when the dedicated tools aren't enough:
    e.g. browsing content with `unreal.EditorAssetLibrary`, inspecting
    Fortnite device/actor classes, or calling APIs not wrapped by other tools.

    Args:
        code: Python source to run. For "statement"/"eval" it must be a
            single expression/statement; for "file" (default) it can be a
            full multi-line script.
        mode: One of "file" (default, runs as a script), "statement"
            (executes and prints one statement), or "eval" (evaluates one
            expression and returns its value).

    Returns:
        dict with `success` (bool), `result` (the eval'd value or error
        text as a string), and `output` (anything printed/logged).
    """
    mode_map = {
        "file": re.MODE_EXEC_FILE,
        "statement": re.MODE_EXEC_STATEMENT,
        "eval": re.MODE_EVAL_STATEMENT,
    }
    exec_mode = mode_map.get(mode, re.MODE_EXEC_FILE)
    data = get_bridge().exec_raw(code, exec_mode=exec_mode)
    return {
        "success": data.get("success", False),
        "result": data.get("result"),
        "output": extract_output_text(data),
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@mcp.tool()
def get_editor_status() -> dict:
    """Check connectivity and report basic info about the connected UEFN editor
    (project file, current level name, engine version, actor/selection counts).
    """
    try:
        return get_bridge().exec_json(
            "import unreal\n"
            "_ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)\n"
            "_world = _ues.get_editor_world()\n"
            "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
            "result = {\n"
            "    'connected': True,\n"
            "    'project_file': unreal.Paths.get_project_file_path(),\n"
            "    'level_name': _world.get_name() if _world else None,\n"
            "    'engine_version': unreal.SystemLibrary.get_engine_version(),\n"
            "    'actor_count': len(_eas.get_all_level_actors()),\n"
            "    'selected_count': len(_eas.get_selected_level_actors()),\n"
            "}\n"
        )
    except UEFNConnectionError as exc:
        return {"connected": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

_ACTOR_LOOKUP = (
    "import unreal\n"
    "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
    "_actor = None\n"
    "for _a in _eas.get_all_level_actors():\n"
    "    if _a.get_actor_label() == _params['label']:\n"
    "        _actor = _a\n"
    "        break\n"
)


def _transform_dict(actor_expr: str = "_actor", indent: int = 0) -> str:
    pad = " " * indent
    lines = [
        f"_loc = {actor_expr}.get_actor_location()",
        f"_rot = {actor_expr}.get_actor_rotation()",
        f"_scl = {actor_expr}.get_actor_scale3d()",
        "_transform = {",
        "    'location': {'x': _loc.x, 'y': _loc.y, 'z': _loc.z},",
        "    'rotation': {'pitch': _rot.pitch, 'yaw': _rot.yaw, 'roll': _rot.roll},",
        "    'scale': {'x': _scl.x, 'y': _scl.y, 'z': _scl.z},",
        "}",
    ]
    return "".join(f"{pad}{line}\n" for line in lines)


@mcp.tool()
def list_actors(class_name: str | None = None, limit: int = 500) -> list[dict]:
    """List actors currently placed in the loaded level.

    Args:
        class_name: If set, only return actors whose class name contains
            this substring (case-insensitive), e.g. "StaticMeshActor".
        limit: Maximum number of actors to return.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        "_filter = _params.get('class_name')\n"
        "_limit = _params.get('limit', 500)\n"
        "_items = []\n"
        "for _a in _eas.get_all_level_actors():\n"
        "    _cls_name = _a.get_class().get_name()\n"
        "    if _filter and _filter.lower() not in _cls_name.lower():\n"
        "        continue\n"
        "    _loc = _a.get_actor_location()\n"
        "    _rot = _a.get_actor_rotation()\n"
        "    _scl = _a.get_actor_scale3d()\n"
        "    _items.append({\n"
        "        'label': _a.get_actor_label(),\n"
        "        'name': _a.get_name(),\n"
        "        'class': _cls_name,\n"
        "        'location': {'x': _loc.x, 'y': _loc.y, 'z': _loc.z},\n"
        "        'rotation': {'pitch': _rot.pitch, 'yaw': _rot.yaw, 'roll': _rot.roll},\n"
        "        'scale': {'x': _scl.x, 'y': _scl.y, 'z': _scl.z},\n"
        "    })\n"
        "    if len(_items) >= _limit:\n"
        "        break\n"
        "result = _items\n",
        class_name=class_name,
        limit=limit,
    )


@mcp.tool()
def get_selected_actors() -> list[dict]:
    """Return the actors currently selected in the UEFN editor viewport/outliner."""
    return get_bridge().exec_json(
        "import unreal\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        "result = [\n"
        "    {'label': _a.get_actor_label(), 'class': _a.get_class().get_name()}\n"
        "    for _a in _eas.get_selected_level_actors()\n"
        "]\n"
    )


@mcp.tool()
def spawn_actor(
    class_path: str,
    location: Vec3 | None = None,
    rotation: Vec3 | None = None,
    scale: Vec3 | None = None,
    label: str | None = None,
) -> dict:
    """Spawn an actor into the loaded level.

    Args:
        class_path: Object path of the class to spawn. Either a native class
            (e.g. "/Script/Engine.StaticMeshActor") or a Blueprint class
            asset path (e.g. "/Game/Devices/BP_MyDevice.BP_MyDevice"). Use
            `list_content_assets` or `execute_python` to discover available
            Fortnite device/prop Blueprint paths.
        location: World location {"x", "y", "z"} in cm. Defaults to origin.
        rotation: World rotation {"pitch", "yaw", "roll"} in degrees.
        scale: Actor scale {"x", "y", "z"}. Defaults to (1, 1, 1).
        label: Optional editor display name (shown in the World Outliner).
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        "def _resolve_class(path):\n"
        "    cls = unreal.load_class(None, path)\n"
        "    if cls is None:\n"
        "        try:\n"
        "            cls = unreal.EditorAssetLibrary.load_blueprint_class(path)\n"
        "        except Exception:\n"
        "            cls = None\n"
        "    return cls\n"
        "_cls = _resolve_class(_params['class_path'])\n"
        "if _cls is None:\n"
        "    result = {\n"
        "        'success': False,\n"
        "        'error': \"Could not resolve class '\" + _params['class_path']\n"
        "            + \"'. Use execute_python with unreal.EditorAssetLibrary.list_assets(...) to find the correct path.\",\n"
        "    }\n"
        "else:\n"
        "    _loc = _params.get('location') or {}\n"
        "    _rot = _params.get('rotation') or {}\n"
        "    _location = unreal.Vector(x=_loc.get('x', 0.0), y=_loc.get('y', 0.0), z=_loc.get('z', 0.0))\n"
        "    _rotation = unreal.Rotator(pitch=_rot.get('pitch', 0.0), yaw=_rot.get('yaw', 0.0), roll=_rot.get('roll', 0.0))\n"
        "    _actor = _eas.spawn_actor_from_class(_cls, _location, _rotation)\n"
        "    if _actor is None:\n"
        "        result = {'success': False, 'error': 'spawn_actor_from_class returned None'}\n"
        "    else:\n"
        "        _label = _params.get('label')\n"
        "        if _label:\n"
        "            _actor.set_actor_label(_label)\n"
        "        _scale = _params.get('scale')\n"
        "        if _scale:\n"
        "            _actor.set_actor_scale3d(unreal.Vector(x=_scale.get('x', 1.0), y=_scale.get('y', 1.0), z=_scale.get('z', 1.0)))\n"
        "        result = {\n"
        "            'success': True,\n"
        "            'label': _actor.get_actor_label(),\n"
        "            'name': _actor.get_name(),\n"
        "            'class': _actor.get_class().get_name(),\n"
        "        }\n",
        class_path=class_path,
        location=location,
        rotation=rotation,
        scale=scale,
        label=label,
    )


@mcp.tool()
def delete_actor(label: str) -> dict:
    """Delete the actor with the given editor label (World Outliner name)."""
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _eas.destroy_actor(_actor)\n"
        "    result = {'success': True}\n",
        label=label,
    )


@mcp.tool()
def get_actor_transform(label: str) -> dict:
    """Get the world transform (location/rotation/scale) of the actor with the given label."""
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        + _transform_dict(indent=4)
        + "    result = {'success': True, **_transform}\n",
        label=label,
    )


@mcp.tool()
def set_actor_transform(
    label: str,
    location: Vec3 | None = None,
    rotation: Vec3 | None = None,
    scale: Vec3 | None = None,
    save: bool = True,
) -> dict:
    """Move/rotate/scale the actor with the given label, and make it stick.

    Any of location, rotation or scale left unset is left unchanged.

    A bare `set_actor_location` looks like it worked and does not survive an
    editor restart: it never dirties the actor's World Partition package, so
    the save writes nothing while reporting success. It also leaves the
    collision body at the old position, so the mesh renders in the new place
    but is not standable. This tool handles both -- it calls `modify()` first,
    moves with `teleport=True`, then nudges the actor 1cm and back to rebuild
    collision, and saves dirty packages.

    Check `dirty_packages_before_save` in the result: if it is 0, nothing was
    written to disk. Verify geometry with a line trace, never with bounds --
    bounds report the new position whether or not collision followed.

    Args:
        label: Editor label of the actor to move.
        location: New world location {"x", "y", "z"} in cm.
        rotation: New world rotation {"pitch", "yaw", "roll"} in degrees.
        scale: New actor scale {"x", "y", "z"}.
        save: Save dirty packages afterwards. Pass False only when moving many
            actors in a row, and then call `save_level` at the end -- an
            unsaved transform is lost on restart.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _esu = unreal.EditorLoadingAndSavingUtils\n"
        "    _loc = _params.get('location')\n"
        "    _rot = _params.get('rotation')\n"
        "    _scl = _params.get('scale')\n"
        "    _actor.modify()\n"
        "    if _loc:\n"
        "        _actor.set_actor_location(unreal.Vector(x=_loc.get('x', 0.0), y=_loc.get('y', 0.0), z=_loc.get('z', 0.0)), False, True)\n"
        "    if _rot:\n"
        "        _actor.set_actor_rotation(unreal.Rotator(pitch=_rot.get('pitch', 0.0), yaw=_rot.get('yaw', 0.0), roll=_rot.get('roll', 0.0)), True)\n"
        "    if _scl:\n"
        "        _actor.set_actor_scale3d(unreal.Vector(x=_scl.get('x', 1.0), y=_scl.get('y', 1.0), z=_scl.get('z', 1.0)))\n"
        "    _p = _actor.get_actor_location()\n"
        "    _actor.set_actor_location(unreal.Vector(_p.x, _p.y, _p.z + 1.0), False, True)\n"
        "    _actor.set_actor_location(unreal.Vector(_p.x, _p.y, _p.z), False, True)\n"
        "    _dirty_before = len(_esu.get_dirty_map_packages())\n"
        "    _dirty_after = None\n"
        "    if _params.get('save', True):\n"
        "        _esu.save_dirty_packages(True, True)\n"
        "        _dirty_after = len(_esu.get_dirty_map_packages())\n"
        + _transform_dict(indent=4)
        + "    result = {\n"
        "        'success': True,\n"
        "        'dirty_packages_before_save': _dirty_before,\n"
        "        'dirty_packages_after_save': _dirty_after,\n"
        "        **_transform,\n"
        "    }\n",
        label=label,
        location=location,
        rotation=rotation,
        scale=scale,
        save=save,
    )


@mcp.tool()
def duplicate_actor(label: str, offset: Vec3 | None = None, new_label: str | None = None) -> dict:
    """Duplicate the actor with the given label, optionally offsetting the copy's
    world location and giving it a new editor label.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _off = _params.get('offset') or {}\n"
        "    _offset = unreal.Vector(x=_off.get('x', 0.0), y=_off.get('y', 0.0), z=_off.get('z', 0.0))\n"
        "    _new_actor = _eas.duplicate_actor(_actor, None, _offset)\n"
        "    if _new_actor is None:\n"
        "        result = {'success': False, 'error': 'duplicate_actor returned None'}\n"
        "    else:\n"
        "        _new_label = _params.get('new_label')\n"
        "        if _new_label:\n"
        "            _new_actor.set_actor_label(_new_label)\n"
        "        result = {'success': True, 'label': _new_actor.get_actor_label(), 'name': _new_actor.get_name()}\n",
        label=label,
        offset=offset,
        new_label=new_label,
    )


# ---------------------------------------------------------------------------
# Content browser / level
# ---------------------------------------------------------------------------


@mcp.tool()
def list_content_assets(
    path: str = "/Game",
    class_names: list[str] | None = None,
    recursive: bool = True,
    limit: int = 200,
) -> list[dict]:
    """Browse assets in the content browser (props, Blueprints, materials, etc.).

    Args:
        path: Content path to search, e.g. "/Game" or "/Game/Devices".
        class_names: If set, only return assets whose class name is in this list
            (e.g. ["StaticMesh", "Blueprint"]).
        recursive: Whether to search subfolders.
        limit: Maximum number of assets to return.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_paths = unreal.EditorAssetLibrary.list_assets(_params.get('path', '/Game'), recursive=_params.get('recursive', True), include_folder=False)\n"
        "_class_names = _params.get('class_names')\n"
        "_limit = _params.get('limit', 200)\n"
        "_items = []\n"
        "for _ap in _paths:\n"
        "    _data = unreal.EditorAssetLibrary.find_asset_data(_ap)\n"
        "    _cls = str(_data.asset_class_path.asset_name) if _data and _data.asset_class_path else ''\n"
        "    if _class_names and _cls not in _class_names:\n"
        "        continue\n"
        "    _items.append({'path': _ap, 'class': _cls})\n"
        "    if len(_items) >= _limit:\n"
        "        break\n"
        "result = _items\n",
        path=path,
        class_names=class_names,
        recursive=recursive,
        limit=limit,
    )


@mcp.tool()
def save_level() -> dict:
    """Save everything modified in the level, and report whether it reached disk.

    Saves through `save_dirty_packages` rather than `save_current_level`: a
    UEFN level is World Partitioned, so each actor lives in its own external
    package and saving only the level package leaves actor edits on the floor.

    `dirty_packages_before` is the number that matters. If it is 0 while you
    expect changes, those changes never dirtied anything and are not being
    written -- the usual cause is a transform applied without `modify()`.
    `dirty_packages_after` should be 0.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_esu = unreal.EditorLoadingAndSavingUtils\n"
        "_before = len(_esu.get_dirty_map_packages())\n"
        "_esu.save_dirty_packages(True, True)\n"
        "_after = len(_esu.get_dirty_map_packages())\n"
        "result = {\n"
        "    'success': _after == 0,\n"
        "    'dirty_packages_before': _before,\n"
        "    'dirty_packages_after': _after,\n"
        "}\n",
    )


# ---------------------------------------------------------------------------
# Persistence and validation
#
# These encode procedures documented in docs/gotchas/ that were still being
# re-derived by hand every session, and got done wrong. Each has a single
# correct form, so it belongs in the tool rather than in prose a caller has to
# remember at the right moment.
# ---------------------------------------------------------------------------


@mcp.tool()
def validate_level(save_first: bool = True, limit: int = 100) -> dict:
    """Check every actor in the level for content that will fail to publish.

    Fortnite only allows assets on its Creative exposure list, and a reference
    to a disallowed one surfaces through the editor's validator rather than at
    spawn time.

    Args:
        save_first: Save dirty packages before validating. Keep this True.
            `is_object_valid` reads VALID on a freshly-spawned actor and
            INVALID on that same actor right after a save, so a pre-save check
            gives false clean bills of health -- it has done so twice here.
        limit: Maximum number of invalid actors to list in the result.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        "_esu = unreal.EditorLoadingAndSavingUtils\n"
        "_dirty_before = _dirty_after = None\n"
        "if _params.get('save_first', True):\n"
        "    _dirty_before = len(_esu.get_dirty_map_packages())\n"
        "    _esu.save_dirty_packages(True, True)\n"
        "    _dirty_after = len(_esu.get_dirty_map_packages())\n"
        "_ev = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)\n"
        "_invalid = []\n"
        "_checked = 0\n"
        "for _a in _eas.get_all_level_actors():\n"
        "    _checked += 1\n"
        "    _r = _ev.is_object_valid(_a, unreal.DataValidationUsecase.MANUAL)\n"
        # is_object_valid returns (result, warnings, errors), not the bare
        # enum; comparing the tuple to the enum flags every actor in a clean
        # level, which cost a debugging round the one time it was done.
        "    _errors = [str(_e) for _e in list(_r[2])]\n"
        "    if _r[0] != unreal.DataValidationResult.VALID or _errors:\n"
        "        if len(_invalid) < _params.get('limit', 100):\n"
        "            _invalid.append({'label': _a.get_actor_label(), 'errors': _errors})\n"
        "result = {\n"
        "    'checked': _checked,\n"
        "    'invalid_count': len(_invalid),\n"
        "    'invalid': _invalid,\n"
        "    'saved_before_validating': bool(_params.get('save_first', True)),\n"
        "    'dirty_packages_before_save': _dirty_before,\n"
        "    'dirty_packages_after_save': _dirty_after,\n"
        "}\n",
        save_first=save_first,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Custom Verse devices
# ---------------------------------------------------------------------------

# load_class returns None for a project's own compiled Verse class;
# load_object is the one that works.
_VERSE_CLASS = (
    "def _verse_class(project, name):\n"
    "    return unreal.load_object(None, '/' + project + '/_Verse.' + name)\n"
)

_NO_SCRIPT = (
    "Actor has no Script sub-object -- it is not a custom Verse device."
)


@mcp.tool()
def spawn_verse_device(
    project_name: str,
    verse_class_name: str,
    location: Vec3 | None = None,
    label: str | None = None,
) -> dict:
    """Spawn one of the project's own compiled Verse `creative_device`s.

    A compiled Verse class does not appear in the asset registry and is not
    reachable through `spawn_actor` -- it lives under the project's own
    content root as `/<ProjectName>/_Verse.<verse_class_name>`, and only
    `spawn_actor_from_object` accepts it.

    The spawned actor is a generic `VerseDevice_C`; the instance holding the
    `@editable` fields is its `Script` sub-object, whose class path is
    returned here so you can confirm the right device was spawned.

    Args:
        project_name: The UEFN project name, which is also its content root
            (e.g. "SkyWars" -> "/SkyWars").
        verse_class_name: The Verse class name as written in the .verse source
            (e.g. "personal_drip_manager").
        location: World location {"x", "y", "z"} in cm. Defaults to origin.
        label: Optional editor display name.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        + _VERSE_CLASS
        + "_cls = _verse_class(_params['project_name'], _params['verse_class_name'])\n"
        "if _cls is None:\n"
        "    result = {'success': False, 'error': 'No compiled Verse class at /'"
        " + _params['project_name'] + '/_Verse.' + _params['verse_class_name']"
        " + '. Verse must be compiled in UEFN (Verse > Build Verse Code) before"
        " its classes exist; there is no scriptable compile.'}\n"
        "else:\n"
        "    _loc = _params.get('location') or {}\n"
        "    _v = unreal.Vector(x=_loc.get('x', 0.0), y=_loc.get('y', 0.0), z=_loc.get('z', 0.0))\n"
        "    _actor = _eas.spawn_actor_from_object(_cls, _v)\n"
        "    if _actor is None:\n"
        "        result = {'success': False, 'error': 'spawn_actor_from_object returned None'}\n"
        "    else:\n"
        "        if _params.get('label'):\n"
        "            _actor.set_actor_label(_params['label'])\n"
        "        _script = _actor.get_editor_property('Script')\n"
        "        result = {\n"
        "            'success': True,\n"
        "            'label': _actor.get_actor_label(),\n"
        "            'actor_class': _actor.get_class().get_path_name(),\n"
        "            'script_class': _script.get_class().get_path_name() if _script else None,\n"
        "        }\n",
        project_name=project_name,
        verse_class_name=verse_class_name,
        location=location,
        label=label,
    )


@mcp.tool()
def list_verse_editables(label: str) -> dict:
    """List the `@editable` fields of a spawned custom Verse device.

    Verse property names are mangled to `__verse_0x<CRC>_<Name>`, and the hash
    is not derivable by hand, so the real names have to be read off the object
    itself. Use the names this returns with `set_verse_editable`.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    import re as _re\n"
        "    _script = _actor.get_editor_property('Script')\n"
        "    if _script is None:\n"
        "        result = {'success': False, 'error': " + repr(_NO_SCRIPT) + "}\n"
        "    else:\n"
        "        _opt = unreal.JsonStringifyOptions()\n"
        # Without DISABLE_DELTA_ENCODING the dump omits every property still
        # at its Verse-side default, so unset fields never show up at all.
        "        _opt.set_editor_property('flags', unreal.JsonStringifyFlags.DISABLE_DELTA_ENCODING)\n"
        "        _j = unreal.JsonObjectGraphFunctionLibrary.stringify([_script], _opt)\n"
        "        _found = []\n"
        "        _names = []\n"
        "        for _m in _re.finditer('__verse_0x[0-9A-Fa-f]+_([A-Za-z0-9_]+)', _j):\n"
        "            if _m.group(0) not in _names:\n"
        "                _names.append(_m.group(0))\n"
        "                _found.append({'property': _m.group(0), 'verse_name': _m.group(1)})\n"
        "        result = {'success': True, 'script_class': _script.get_class().get_path_name(), 'editables': _found}\n",
        label=label,
    )


@mcp.tool()
def set_verse_editable(
    label: str, property_name: str, value: float | int | str | bool
) -> dict:
    """Set a scalar `@editable` field on a spawned custom Verse device.

    `property_name` is the mangled name from `list_verse_editables`, not the
    plain field name in the .verse source.

    Scalars only. A field typed as a native device (`@editable X : timer_device`)
    cannot be assigned from Python at all: native devices expose no Verse
    interface object reachable from here, and every angle at it is already
    ruled out. Use `add_verse_tag` and runtime tag lookup instead.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _script = _actor.get_editor_property('Script')\n"
        "    if _script is None:\n"
        "        result = {'success': False, 'error': " + repr(_NO_SCRIPT) + "}\n"
        "    else:\n"
        "        _script.set_editor_property(_params['property_name'], _params['value'])\n"
        "        _read = _script.get_editor_property(_params['property_name'])\n"
        "        if not isinstance(_read, (int, float, str, bool)):\n"
        "            _read = str(_read)\n"
        "        result = {'success': True, 'property': _params['property_name'], 'value': _read}\n",
        label=label,
        property_name=property_name,
        value=value,
    )


@mcp.tool()
def add_verse_tag(label: str, project_name: str, tag_class_name: str) -> dict:
    """Tag a placed actor with a Verse tag class, so Verse code can find it.

    This is the way around the wall that a native device cannot be bound into
    a custom Verse device's `@editable` field: the Verse code looks its
    targets up at runtime with `FindCreativeObjectsWithTag` instead, and
    attaching the tag is fully scriptable.

    Adds a `VerseTagMarkupComponent` if the actor has none, then appends the
    tag. Tags already on the actor are kept.

    Args:
        label: Editor label of the actor to tag.
        project_name: The UEFN project name / content root (e.g. "SkyWars").
        tag_class_name: The Verse tag class name (e.g. "my_target_tag"),
            declared as `my_target_tag := class(tag){}` and compiled.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + _VERSE_CLASS
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _tag = _verse_class(_params['project_name'], _params['tag_class_name'])\n"
        "    if _tag is None:\n"
        "        result = {'success': False, 'error': 'No compiled Verse tag class at /'"
        " + _params['project_name'] + '/_Verse.' + _params['tag_class_name']"
        " + '. Tags are declared in Verse and need a manual compile in UEFN first.'}\n"
        "    else:\n"
        "        _markups = _actor.get_components_by_class(unreal.VerseTagMarkupComponent)\n"
        "        if not _markups:\n"
        # add_new_subobject is the call the Details panel's Add Component
        # button makes. Note get_engine_subsystem: the editor one rejects
        # SubobjectDataSubsystem outright.
        "            _sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)\n"
        "            _handles = _sub.k2_gather_subobject_data_for_instance(_actor)\n"
        "            _p = unreal.AddNewSubobjectParams()\n"
        "            _p.set_editor_property('parent_handle', _handles[0])\n"
        "            _p.set_editor_property('new_class', unreal.VerseTagMarkupComponent)\n"
        "            _handle, _fail = _sub.add_new_subobject(_p)\n"
        "            if str(_fail):\n"
        "                raise RuntimeError('add_new_subobject failed: ' + str(_fail))\n"
        "            _markups = _actor.get_components_by_class(unreal.VerseTagMarkupComponent)\n"
        "        _markup = _markups[0]\n"
        "        _container = _markup.get_editor_property('InternalTags')\n"
        "        _existing = list(_container.get_editor_property('InternalTags'))\n"
        "        _paths = []\n"
        "        for _i in _existing:\n"
        "            _t = _i.get_editor_property('InternalTag')\n"
        "            if _t:\n"
        "                _paths.append(_t.get_path_name())\n"
        "        if _tag.get_path_name() not in _paths:\n"
        # InternalTags is an array of VerseTagTypeInfo structs, not of raw
        # class references -- passing the class straight in fails.
        "            _info = unreal.VerseTagTypeInfo()\n"
        "            _info.set_editor_property('InternalTag', _tag)\n"
        "            _existing.append(_info)\n"
        "            _container.set_editor_property('InternalTags', _existing)\n"
        "            _markup.set_editor_property('InternalTags', _container)\n"
        "        _back = _markup.get_editor_property('InternalTags').get_editor_property('InternalTags')\n"
        "        _tags = []\n"
        "        for _i in _back:\n"
        "            _t = _i.get_editor_property('InternalTag')\n"
        "            if _t:\n"
        "                _tags.append(_t.get_path_name())\n"
        "        result = {'success': True, 'label': _actor.get_actor_label(), 'tags': _tags}\n",
        label=label,
        project_name=project_name,
        tag_class_name=tag_class_name,
    )


# ---------------------------------------------------------------------------
# Item content
# ---------------------------------------------------------------------------


@mcp.tool()
def set_item_spawner_content(label: str, items: list[dict]) -> dict:
    """Set what an Item Spawner V3 device spawns.

    Item Spawner V3 is the only device whose item content is writable from
    Python. Item Granter and Class Designer hold theirs in a component that
    rejects instance writes -- a platform wall, not a missing wrapper -- so
    anything that needs scripted item content has to be built on this device.

    Args:
        label: Editor label of a `Device_ItemSpawner_V3_C` actor.
        items: One entry per item, `{"asset_path": str, "quantity": int}`.
            `asset_path` is an item definition (e.g.
            "/Game/Athena/Items/Weapons/WID_Assault_Auto_Athena_C_Ore_T02").
            Several entries feed the "Random Spawns" User Option.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _comp = None\n"
        "    for _c in _actor.get_components_by_class(unreal.ActorComponent):\n"
        "        if 'Minigame_Spawner' in _c.get_class().get_name():\n"
        "            _comp = _c\n"
        "            break\n"
        "    if _comp is None:\n"
        "        result = {'success': False, 'error': 'Actor has no Minigame_Spawner_Component -- it is not an Item Spawner V3.'}\n"
        "    else:\n"
        "        _entries = []\n"
        "        _missing = []\n"
        "        for _it in _params['items']:\n"
        "            _asset = unreal.load_asset(_it['asset_path'])\n"
        "            if _asset is None:\n"
        "                _missing.append(_it['asset_path'])\n"
        "                continue\n"
        "            _e = unreal.MinigameSpawnerSpawnParams()\n"
        "            _e.set_editor_property('pickup_to_spawn', _asset)\n"
        "            _e.set_editor_property('pickup_quantity', _it.get('quantity', 1))\n"
        "            _entries.append(_e)\n"
        "        if _missing:\n"
        # A registry hit does not mean an asset loads; several item families
        # show up in the registry and fail load_asset in this build.
        "            result = {'success': False, 'error': 'These asset paths did not load: '"
        " + ', '.join(_missing) + '. Confirm a path with load_asset before using it --"
        " an asset registry hit is not enough.'}\n"
        "        else:\n"
        "            _comp.set_editor_property('ToSpawnList', _entries)\n"
        "            _back = _comp.get_editor_property('ToSpawnList')\n"
        "            _items = []\n"
        "            for _b in _back:\n"
        "                _items.append({\n"
        "                    'asset': _b.get_editor_property('pickup_to_spawn').get_path_name(),\n"
        "                    'quantity': _b.get_editor_property('pickup_quantity'),\n"
        "                })\n"
        "            result = {'success': True, 'label': _actor.get_actor_label(), 'items': _items}\n",
        label=label,
        items=items,
    )


# ---------------------------------------------------------------------------
# Device User Options
# ---------------------------------------------------------------------------

# A User Option holding one of these is an event-graph hookup, not a value:
# it reads back as an empty struct and assigning to it does nothing. Wiring
# one device to another needs a custom Verse device instead -- see
# docs/gotchas/event-wiring.md.
_EVENT_TYPES = "('GameplayEventFunction', 'GameplayEventDescriptor')"

# Reading one option the way that actually works. The keys are the exact
# User-Option strings (spaces and capitals included) and do not appear in
# dir(), so this goes through get_editor_property, never attribute access.
_READ_OPTION = (
    "def _read_option(_dev, _key, _bulk=None):\n"
    "    _entry = {'key': _key}\n"
    "    try:\n"
    "        _v = _dev.get_editor_property(_key)\n"
    "    except Exception as _e:\n"
    # A "Namespace:Property" key lives on a mutator sub-object rather than on
    # the device, so get_editor_property cannot see it. Its current value is
    # still in the bulk map -- as a string, and read-only by this route.
    "        if _bulk is not None and _key in _bulk:\n"
    "            _entry['value'] = str(_bulk[_key])\n"
    "            _entry['type'] = 'str'\n"
    "            _entry['settable'] = False\n"
    "            _entry['note'] = ('Lives on a mutator sub-object, not on the device, so'\n"
    "                              ' set_editor_property cannot reach it. No edit-time'\n"
    "                              ' write path is known for these.')\n"
    "            return _entry\n"
    "        _entry['error'] = str(_e)\n"
    "        return _entry\n"
    "    _tn = type(_v).__name__\n"
    "    _entry['type'] = _tn\n"
    "    if _tn in " + _EVENT_TYPES + ":\n"
    "        _entry['value'] = None\n"
    "        _entry['settable'] = False\n"
    "        _entry['note'] = 'Event-graph hookup, not a value. Needs a custom Verse device.'\n"
    "        return _entry\n"
    "    _entry['settable'] = True\n"
    "    if isinstance(_v, (bool, int, float, str)):\n"
    "        _entry['value'] = _v\n"
    "        return _entry\n"
    # Enum members are reported by bare name, which is exactly what
    # set_device_options takes back -- str() would give "<Enum_Foo.BAR: 1>".
    "    try:\n"
    "        _entry['value'] = _v.name\n"
    "        _entry['enum_values'] = [_m.name for _m in list(type(_v))]\n"
    "    except Exception:\n"
    "        _entry['value'] = str(_v)\n"
    "    return _entry\n"
)


@mcp.tool()
def get_device_options(
    label: str, contains: str | None = None, limit: int = 60
) -> dict:
    """Read a Fortnite device's "User Options" -- its Details-panel settings.

    This is the readable form of the whole "V2" device family (Island
    Settings, Round Settings, Storm Controller, Item Granter, Class Designer,
    ...). Use it before `set_device_options` to learn a setting's exact key,
    its current value, and whether it can be written at all.

    Each returned option carries:
      - `key`: the exact User-Option string, spaces and capitals included.
        This is the name to pass to `set_device_options`; there is no
        snake_case equivalent and these keys do not appear in `dir()`.
      - `type`: the Python type name of the current value.
      - `settable`: False for event-graph hookups, which look like ordinary
        options and silently ignore writes.
      - `enum_values`: every valid member, when the option is an enum. Read
        this rather than guessing an enum's spelling.

    Args:
        label: Editor label of the device actor.
        contains: Case-insensitive substring filter on the key. A bare
            Island Settings device has ~300 options, so filter unless you
            genuinely want to page through all of them.
        limit: Maximum options to return.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + _READ_OPTION
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        # get_user_option_values is the only usable bulk enumeration:
        # get_user_option_definitions returns an opaque container with no
        # len() or iteration.
        "    try:\n"
        "        _all = _actor.get_user_option_values()\n"
        "    except Exception:\n"
        "        _all = None\n"
        "    if _all is None:\n"
        "        result = {'success': False, 'error': 'Actor exposes no User Options -- it is probably not a Fortnite device.'}\n"
        "    else:\n"
        "        _keys = sorted(str(_k) for _k in _all.keys())\n"
        "        _needle = (_params.get('contains') or '').lower()\n"
        "        if _needle:\n"
        "            _keys = [_k for _k in _keys if _needle in _k.lower()]\n"
        "        _total = len(_keys)\n"
        "        _limit = _params.get('limit', 60)\n"
        "        _options = [_read_option(_actor, _k, _all) for _k in _keys[:_limit]]\n"
        "        result = {\n"
        "            'success': True,\n"
        "            'label': _actor.get_actor_label(),\n"
        "            'matched': _total,\n"
        "            'returned': len(_options),\n"
        "            'options': _options,\n"
        "        }\n",
        label=label,
        contains=contains,
        limit=limit,
    )


@mcp.tool()
def set_device_options(label: str, options: dict, save: bool = True) -> dict:
    """Set a Fortnite device's "User Options" at edit time.

    Most settings that look Details-panel-only are writable this way. Two
    things make them look read-only when they are not, and this tool exists so
    neither has to be remembered:

    - `set_user_option_value` is the *runtime* API. In the editor it needs a
      live `PlayerController`, so it returns False and changes nothing --
      which reads exactly like "not supported at edit time". The edit-time
      path is `set_editor_property` with the option's exact key.
    - the key is the literal User-Option string, case-sensitive and spaces
      included ("Resize Time", "bLastStandingWins"). It gets none of the
      CamelCase-to-snake_case conversion native properties get, and it is
      absent from `dir()`.

    Every key is read back after writing, and a key whose value is an
    event-graph hookup is rejected rather than silently ignored. Get exact
    key names from `get_device_options` first.

    Args:
        label: Editor label of the device actor.
        options: `{exact User-Option key: value}`. Enums take their string
            name, e.g. `{"Building Mode": "ALL"}`.
        save: Save dirty packages afterwards. Pass False when configuring
            many devices in a row, then call `save_level` at the end.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + _READ_OPTION
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _applied = []\n"
        "    _rejected = []\n"
        "    for _key, _want in _params['options'].items():\n"
        "        _before = _read_option(_actor, _key)\n"
        "        if 'error' in _before:\n"
        "            _rejected.append({'key': _key, 'reason': 'No such option on this device. Check the exact key with get_device_options -- spaces and capitals are literal.'})\n"
        "            continue\n"
        "        if not _before.get('settable', False):\n"
        "            _rejected.append({'key': _key, 'reason': _before.get('note', 'Not settable.')})\n"
        "            continue\n"
        "        try:\n"
        # An enum property wants a member of its own type, so a string name is
        # resolved against the value already sitting there.
        "            if _before.get('enum_values') and isinstance(_want, str):\n"
        "                _want = getattr(type(_actor.get_editor_property(_key)), _want.upper())\n"
        "            _actor.set_editor_property(_key, _want)\n"
        "        except Exception as _e:\n"
        "            _rejected.append({'key': _key, 'reason': str(_e)})\n"
        "            continue\n"
        "        _after = _read_option(_actor, _key)\n"
        "        _applied.append({'key': _key, 'was': _before.get('value'), 'now': _after.get('value')})\n"
        "    _esu = unreal.EditorLoadingAndSavingUtils\n"
        "    _dirty_before = len(_esu.get_dirty_map_packages())\n"
        "    _dirty_after = None\n"
        "    if _params.get('save', True):\n"
        "        _esu.save_dirty_packages(True, True)\n"
        "        _dirty_after = len(_esu.get_dirty_map_packages())\n"
        "    result = {\n"
        "        'success': not _rejected,\n"
        "        'label': _actor.get_actor_label(),\n"
        "        'applied': _applied,\n"
        "        'rejected': _rejected,\n"
        "        'dirty_packages_before_save': _dirty_before,\n"
        "        'dirty_packages_after_save': _dirty_after,\n"
        "    }\n",
        label=label,
        options=options,
        save=save,
    )


# ---------------------------------------------------------------------------
# Verse
# ---------------------------------------------------------------------------


@mcp.tool()
def build_verse_code(
    project_name: str, expect_classes: list[str], timeout: float = 180.0
) -> dict:
    """Compile the project's Verse code, by pressing UEFN's own Build shortcut.

    Verse compilation has no scriptable trigger -- no `unreal` subsystem, no
    build verb in Epic's Lore CLI. It was the one step in building a map that
    always stopped and waited for a person, which mattered out of proportion
    to its size: Verse is the only route to device-to-device event wiring, so
    every wiring task inherited the wait. This presses `Ctrl+Shift+B` on the
    editor window, exactly as a person would, then waits for the result.

    The window is matched by its executable, not its title, and the keystroke
    is not sent at all unless that window is genuinely in the foreground -- so
    it cannot land somewhere it was not meant to. It does take focus briefly.

    Confirmation is by looking for the classes in `expect_classes`, so **name
    classes the build is supposed to create.** If they already exist, this
    returns immediately having proved nothing, and says so in `verified`. To
    confirm a rebuild that only changes an existing class's body, add a
    throwaway `zz_probe_tag := class(tag){}` and expect that.

    Args:
        project_name: The UEFN project / content root, e.g. "SkyWars".
        expect_classes: Verse class names that must load once the build is
            done, e.g. `["starter_weapon1_tag"]`.
        timeout: Seconds to wait for them to appear.
    """
    from .editor_ui import EditorWindowError
    from .editor_ui import build_verse_code as _press

    def _loaded() -> dict:
        return get_bridge().exec_json(
            "import unreal\n"
            "result = {_n: unreal.load_object(None, '/' + _params['project_name'] + '/_Verse.' + _n) is not None"
            " for _n in _params['names']}\n",
            project_name=project_name,
            names=expect_classes,
        )

    before = _loaded()
    if all(before.values()):
        return {
            "success": True,
            "verified": False,
            "classes": before,
            "note": (
                "Every expected class already loaded, so no build was "
                "triggered and nothing was proved. Name a class this build "
                "should newly create."
            ),
        }
    try:
        window = _press()
    except EditorWindowError as exc:
        return {"success": False, "verified": False, "error": str(exc)}

    started = time.monotonic()
    while time.monotonic() - started < timeout:
        time.sleep(3.0)
        try:
            now = _loaded()
        except Exception:
            # The editor stops answering while it compiles; that is the build
            # running, not a failure.
            continue
        if all(now.values()):
            return {
                "success": True,
                "verified": True,
                "window": window,
                "classes": now,
                "waited_seconds": round(time.monotonic() - started, 1),
            }
    return {
        "success": False,
        "verified": True,
        "window": window,
        "error": (
            f"The build was triggered but {expect_classes} did not all load "
            f"within {timeout}s. Verse compile errors go to UEFN's own output "
            "log, which is not readable from here -- check the editor."
        ),
    }


# ---------------------------------------------------------------------------
# Looking at the map
# ---------------------------------------------------------------------------


@mcp.tool()
def screenshot_level(
    output_dir: str,
    filename: str,
    location: Vec3,
    rotation: Vec3,
    width: int = 1280,
    height: int = 720,
    fov: float = 70.0,
    exposure_bias: float = 11.0,
) -> dict:
    """Render the level from a viewpoint to a PNG, so Claude can look at it.

    Spawns a temporary `SceneCapture2D`, captures, exports and destroys it.
    Synchronous, leaves nothing in the level, and does not touch the user's
    viewport or window focus. Read the resulting file with an image-capable
    reader.

    Do not reach for `HighResShot` or `take_high_res_screenshot` instead --
    both are confirmed dead ends that cost four sessions between them.

    Args:
        output_dir: Directory on the machine running UEFN to write into.
        filename: File name, e.g. "overview.png".
        location: Camera world location {"x", "y", "z"} in cm.
        rotation: Camera rotation {"pitch", "yaw", "roll"} in degrees.
        width: Image width in pixels.
        height: Image height in pixels.
        fov: Field of view in degrees.
        exposure_bias: Manual exposure bias. The default suits a lit outdoor
            scene; raise it if the render comes back black.
    """
    return get_bridge().exec_json(
        "import unreal\n"
        "import os as _os\n"
        "_ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)\n"
        "_world = _ues.get_editor_world()\n"
        "_eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\n"
        "_loc = _params['location']\n"
        "_rot = _params['rotation']\n"
        "_v = unreal.Vector(x=_loc.get('x', 0.0), y=_loc.get('y', 0.0), z=_loc.get('z', 0.0))\n"
        "_r = unreal.Rotator(pitch=_rot.get('pitch', 0.0), yaw=_rot.get('yaw', 0.0), roll=_rot.get('roll', 0.0))\n"
        # RTF_RGBA8 is required: the default float format makes
        # export_render_target write OpenEXR data under a .png name.
        "_rt = unreal.RenderingLibrary.create_render_target2d(_world, _params['width'], _params['height'], unreal.TextureRenderTargetFormat.RTF_RGBA8)\n"
        "_cap = _eas.spawn_actor_from_class(unreal.SceneCapture2D, _v, _r)\n"
        "try:\n"
        "    _c = _cap.get_editor_property('capture_component2d')\n"
        "    _c.set_editor_property('texture_target', _rt)\n"
        "    _c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)\n"
        "    _c.set_editor_property('fov_angle', _params['fov'])\n"
        "    _pp = unreal.PostProcessSettings()\n"
        "    _pp.set_editor_property('override_auto_exposure_method', True)\n"
        "    _pp.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)\n"
        "    _pp.set_editor_property('override_auto_exposure_bias', True)\n"
        "    _pp.set_editor_property('auto_exposure_bias', _params['exposure_bias'])\n"
        "    _c.set_editor_property('post_process_settings', _pp)\n"
        "    _c.capture_scene()\n"
        "    unreal.RenderingLibrary.export_render_target(_world, _rt, _params['output_dir'], _params['filename'])\n"
        "finally:\n"
        "    _eas.destroy_actor(_cap)\n"
        "_path = _os.path.join(_params['output_dir'], _params['filename'])\n"
        "result = {'success': _os.path.isfile(_path), 'path': _path}\n",
        output_dir=output_dir,
        filename=filename,
        location=location,
        rotation=rotation,
        width=width,
        height=height,
        fov=fov,
        exposure_bias=exposure_bias,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
