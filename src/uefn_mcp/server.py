"""MCP server exposing UEFN (Unreal Editor for Fortnite) level-editing tools.

Talks to a running UEFN editor instance over the Python Editor Script Plugin's
remote execution protocol. The editor must be open with a project loaded and
"Remote Execution" enabled for the Python plugin (see README.md).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import remote_execution as re
from .bridge import UEFNConnectionError, extract_output_text, get_bridge

mcp = MCPServer("uefn-mcp")

Vec3 = dict[str, float]


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
) -> dict:
    """Move/rotate/scale the actor with the given label. Any of location,
    rotation, or scale left unset is left unchanged.
    """
    return get_bridge().exec_json(
        _ACTOR_LOOKUP
        + "if _actor is None:\n"
        "    result = {'success': False, 'error': \"No actor with label '\" + _params['label'] + \"'\"}\n"
        "else:\n"
        "    _loc = _params.get('location')\n"
        "    _rot = _params.get('rotation')\n"
        "    _scl = _params.get('scale')\n"
        "    if _loc:\n"
        "        _actor.set_actor_location(unreal.Vector(x=_loc.get('x', 0.0), y=_loc.get('y', 0.0), z=_loc.get('z', 0.0)), False, False)\n"
        "    if _rot:\n"
        "        _actor.set_actor_rotation(unreal.Rotator(pitch=_rot.get('pitch', 0.0), yaw=_rot.get('yaw', 0.0), roll=_rot.get('roll', 0.0)), False)\n"
        "    if _scl:\n"
        "        _actor.set_actor_scale3d(unreal.Vector(x=_scl.get('x', 1.0), y=_scl.get('y', 1.0), z=_scl.get('z', 1.0)))\n"
        + _transform_dict(indent=4)
        + "    result = {'success': True, **_transform}\n",
        label=label,
        location=location,
        rotation=rotation,
        scale=scale,
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
def save_level(all_dirty: bool = False) -> dict:
    """Save the current level. If `all_dirty` is True, saves all dirty levels instead."""
    return get_bridge().exec_json(
        "import unreal\n"
        "_les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)\n"
        "if _params.get('all_dirty'):\n"
        "    _ok = _les.save_all_dirty_levels()\n"
        "else:\n"
        "    _ok = _les.save_current_level()\n"
        "result = {'success': bool(_ok)}\n",
        all_dirty=all_dirty,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
