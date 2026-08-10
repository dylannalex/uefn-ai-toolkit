# Miscellaneous gotchas

Smaller findings that don't need their own file. Add to this file for a new
one-off finding; split it out once it grows past a page.

## Spawning a basic-shape mesh (Cube, Cylinder, ...) is not "spawn this class"

`/Engine/BasicShapes/Cube` etc. are **static mesh assets**, not actor
classes — `spawn_actor`/`EditorActorSubsystem.spawn_actor_from_class` with
that path as the class fails with `ActorClass is not valid`. Spawn a plain
`unreal.StaticMeshActor` instead, then assign the mesh:

```python
mesh = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
actor.get_components_by_class(unreal.StaticMeshComponent)[0].set_static_mesh(mesh)
```

## Stale `uefn-mcp.exe` processes cause a silent connection failure

If `get_editor_status` (or any tool) fails with `Remote party failed to
attempt the command socket connection!` even though UEFN is running with
Python Scripting + remote execution both correctly enabled for the right
project — check for **multiple `uefn-mcp.exe` processes** running at once
before assuming a config/project problem
(`tasklist | grep uefn-mcp` on Windows). Observed 4 simultaneous instances
in one session, apparently from prior reconnects that didn't exit cleanly;
they conflict over the remote-execution multicast port. Killing all of them
and retrying immediately fixed the connection — a fresh bridge process
starts automatically on the next tool call. Worth investigating on the
server side whether `bridge.py`'s reconnect-on-stale-connection logic
should also be killing/replacing the OS process rather than just the
in-process connection object, since this seems likely to recur for anyone
reconnecting across multiple sessions.
