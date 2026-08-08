# uefn-mcp

An MCP server that drives a running Unreal Editor for Fortnite (UEFN) instance
via Python, so an MCP client (e.g. Claude Code, Claude Desktop) can inspect
and build out Fortnite maps directly instead of clicking through the editor
UI by hand.

## How it works

UEFN ships the Python Editor Script Plugin, which includes a remote execution
protocol: UDP multicast for discovering a running editor, then a TCP channel
for sending it Python to execute. This server discovers the running editor,
opens a command connection, and exposes editor operations (spawn/move/delete
actors, browse content, save the level, run arbitrary Python) as MCP tools.

No plugin code runs inside UEFN beyond what ships with the engine already —
this is purely a client of that existing protocol.

## Prerequisites

- UEFN installed, with a project created and open.
- Python enabled for that project (in the UEFN editor: project settings →
  Experimental → Python).
- [uv](https://docs.astral.sh/uv/) installed to run this server.

## One-time setup: enable remote execution

**Unlike stock Unreal Editor, UEFN ships with Python remote execution off by
default.** Turn it on by adding a `Config/DefaultEngine.ini` file at the root
of your UEFN project (next to the `.uefnproject` file — create the `Config`
folder if it doesn't exist) containing:

```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
RemoteExecutionMulticastGroupEndpoint=239.0.0.1:6766
RemoteExecutionMulticastBindAddress=127.0.0.1
RemoteExecutionMulticastTtl=0
```

This setting is only read at editor startup, so **restart UEFN** after
creating/editing this file for it to take effect.

## Install

```powershell
uv sync
```

## Run standalone (for testing)

```powershell
uv run uefn-mcp
```

## Register with Claude Code

```powershell
claude mcp add uefn -- uv --directory "<path to this repo>" run uefn-mcp
```

Then, with UEFN open and your project loaded, ask Claude to list actors,
spawn props, move things around, etc.

## Tools

- `execute_python(code, mode)` — escape hatch to run arbitrary Python in the
  editor (`mode` is `"file"`, `"statement"`, or `"eval"`). Use this to explore
  `unreal.EditorAssetLibrary` for Fortnite device/prop class paths not covered
  by the other tools.
- `get_editor_status()` — connectivity + project/level/engine info.
- `list_actors(class_name?, limit?)` — list actors in the loaded level.
- `get_selected_actors()` — actors currently selected in the editor.
- `spawn_actor(class_path, location?, rotation?, scale?, label?)` — place an
  actor (native class or Blueprint asset path).
- `delete_actor(label)`
- `get_actor_transform(label)` / `set_actor_transform(label, location?, rotation?, scale?)`
- `duplicate_actor(label, offset?, new_label?)`
- `list_content_assets(path?, class_names?, recursive?, limit?)` — browse the
  content browser.
- `save_level(all_dirty?)`

## Notes / limitations

- Only one editor instance can be connected to at a time (the discovery step
  picks the first one it finds).
- Actor lookups are by editor label (World Outliner name), which isn't
  guaranteed unique; the first match wins.
- UEFN-specific device classes (the Fortnite Creative gallery) aren't
  hardcoded here — use `list_content_assets` or `execute_python` to find the
  class path for a given device/prop, then pass it to `spawn_actor`.
- Requires the `mcp` Python SDK v2.x (`mcp.server.mcpserver.MCPServer`).
