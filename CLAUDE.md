# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Read [docs/INDEX.md](docs/INDEX.md) before consulting anything else under `docs/`** — it routes to the right doc by task ("how do I add item content to a device", "is this setting scriptable", "how do I add a new tool", etc.) instead of requiring you to know which file has the answer.

## What this is

An MCP server that drives a running UEFN (Unreal Editor for Fortnite) instance
via Python, so an MCP client can inspect/build Fortnite maps without manual
editor UI clicks. It talks to UEFN's built-in Python Editor Script Plugin
remote execution protocol (UDP discovery + TCP command channel) — no plugin
code runs inside UEFN beyond what ships with the engine.

## Commands

```powershell
uv sync                  # install deps
uv run uefn-mcp           # run the server standalone (for manual testing)
claude mcp add uefn --scope user -- uv --directory "<path to this repo>" run uefn-mcp
```

There are no tests, lint, or type-check configs in this repo currently.

To exercise the server end-to-end, UEFN must be open with a project loaded
and Python remote execution enabled (see "UEFN prerequisite" below).

## Architecture

Three layers, each in `src/uefn_mcp/`:

- **`remote_execution.py`** — vendored, unmodified copy of Epic's
  `PythonScriptRemoteExecution` client (see the "Copyright Epic Games" header).
  Implements the wire protocol: UDP multicast ping/pong for discovering editor
  nodes, then a TCP command connection for sending Python and receiving
  results. Treat this as third-party code — don't add project-specific logic
  here.
- **`bridge.py`** — `UEFNBridge`, a thread-safe wrapper around one
  `RemoteExecution` command connection (module singleton via `get_bridge()`).
  Auto-connects on first use, reconnects once on a stale/closed connection.
  Two entry points tool implementations use:
  - `exec_raw(code, exec_mode)` — runs code, returns the raw protocol result
    dict (`success`, `result`, `output`).
  - `exec_json(code, **params)` — the primary interface. Wraps `code` so
    `params` are JSON round-tripped into an in-editor `_params` dict, requires
    `code` to assign its answer to a variable named `result`, and extracts
    that value by scanning stdout for `@@UEFN_MCP_RESULT_START@@...@@UEFN_MCP_RESULT_END@@`
    markers (the editor's own print output can't be trusted otherwise).
    Raises `UEFNScriptError` if the markers are missing or the script failed.
- **`server.py`** — `MCPServer("uefn-mcp")` and the `@mcp.tool()` definitions.
  Every tool (except `execute_python`) builds a Python source string that
  calls into `unreal.*` editor APIs and calls `get_bridge().exec_json(...)`.
  Shared snippets like actor-lookup-by-label (`_ACTOR_LOOKUP`) and
  transform-serialization (`_transform_dict`) are factored out as string
  builders and concatenated into the full script per tool.

When adding a new tool: write the `unreal` Python as a string that ends by
assigning a JSON-serializable value to `result`, pass any tool arguments
through as `exec_json(..., key=value)` kwargs (they arrive as `_params` inside
the editor-side script), and keep the tool's Python docstring precise — it's
what the MCP client sees to decide when/how to call the tool.

## UEFN prerequisite

Unlike stock Unreal Editor, UEFN ships with **two** independent Python
switches off by default, and both have to be on or discovery just silently
never hears a `pong` — there's no error that distinguishes "plugin inactive"
from "plugin active but not listening."

1. **Python Scripting itself** (Project Settings > Python in the UEFN UI) —
   `bEnablePythonForProject` under `dataSets.experimental.pythonExperimental`
   in the `.uefnproject` JSON file.
2. **Remote execution** for that plugin — a `Config/DefaultEngine.ini` in the
   target UEFN project (next to the `.uefnproject` file) with:

```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
RemoteExecutionMulticastGroupEndpoint=239.0.0.1:6766
RemoteExecutionMulticastBindAddress=127.0.0.1
RemoteExecutionMulticastTtl=0
```

`setup_uefn_project` sets both. Both are only read at editor startup, so
UEFN must be restarted after creating/editing either file — including when
Python Scripting was turned on by hand in the UEFN UI while the editor was
already running. Only one editor instance can be connected to at a time —
discovery picks the first node it finds.

## Working with `unreal.*` APIs

There's no local `unreal` module to introspect or type-check against — it
only exists inside the running editor process. Use the `execute_python` tool
against a live UEFN instance to explore `unreal.EditorAssetLibrary`,
`unreal.EditorActorSubsystem`, etc., and to discover Fortnite
device/Blueprint class paths (they aren't hardcoded anywhere in this repo)
before wiring a new dedicated tool around them.

Before concluding some Fortnite Creative device setting can only be changed
by hand in the Details panel, read
[docs/gotchas/user-options.md](docs/gotchas/user-options.md) — most
"V2" device settings that look read-only from Python (the "User Options"
system) are actually writable via `set_editor_property` using the option's
exact key name, not the runtime-only `set_user_option_value`. The rest of
`docs/gotchas/` tracks other non-obvious `unreal.*` behavior worth knowing
before wiring a new tool around it (see [docs/INDEX.md](docs/INDEX.md) for
the full list); add to it whenever a session turns up another gotcha.
