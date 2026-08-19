# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Route through the `uefn-knowledge` skill (`skills/uefn-knowledge/SKILL.md`) before opening anything under `docs/`** — it maps a task to the one file that answers it, so you don't need to know which file has the answer. Every directory under `docs/` also has a generated `INDEX.md`.

## What this is

A Claude Code **plugin**, `uefn-ai-toolkit`, that lets a session build Fortnite
maps inside UEFN (Unreal Editor for Fortnite). It bundles three things that
are useless apart:

- an **MCP server** (`src/uefn_mcp/`) that drives a running editor via Epic's
  Python Editor Script Plugin remote execution protocol (UDP discovery + TCP
  command channel) — no plugin code runs inside UEFN beyond what ships with
  the engine;
- **skills** (`skills/`) — `uefn-knowledge` (the routing table into `docs/`)
  and `new-map-project` (scaffolds a map's notes folder);
- a **knowledge base** (`docs/`) of validated asset paths, device class paths
  and `unreal.*` gotchas, all established against a live editor.

The plugin is `uefn-ai-toolkit`; the MCP server inside it is still `uefn-mcp`
(Python package `uefn_mcp`, console script `uefn-mcp`, `MCPServer("uefn-mcp")`,
and the `uefn-mcp.exe` you see in the process list). That split is deliberate —
the plugin is more than its server. Don't "fix" it.

A map's own notes live in a separate **content workspace** — a plain git
repository the user owns, one folder per map. Nothing from this repository is
ever copied into it: the workspace only *declares* the plugin, in its
`.claude/settings.json`, and Claude Code installs it once. That matters
historically, because the previous design *did* copy its skills into each
workspace, and every copy became a fork that could not receive an update.
The scope of that install is a separate question — currently project scope,
`fortnite-maps` only; see HANDOFF.md 0a-bis for the development setup.

## Layout

```
.claude-plugin/plugin.json       manifest: skills, hooks, mcpServers
.claude-plugin/marketplace.json  this repo is also its own marketplace
.mcp.json                        registers the server via ${CLAUDE_PLUGIN_ROOT}
hooks/hooks.json                 regenerates a content workspace's INDEX.md files
scripts/reindex.py               generates every INDEX.md from frontmatter
skills/                          uefn-knowledge, new-map-project
src/uefn_mcp/                    the MCP server (layers, below)
docs/                            assets/ how-to/ gotchas/ internals/
tests/test_bridge.py             self-check, runs without an editor
```

## Commands

```powershell
uv sync                     # install deps
uv run uefn-mcp             # run the server standalone (manual testing)
python tests/test_bridge.py # self-check that needs no editor
python scripts/reindex.py docs
```

Installed by users as a plugin (`/plugin marketplace add dylannalex/uefn-ai-toolkit`,
then `/plugin install uefn-ai-toolkit@dylannalex-uefn`). There is no lint or
type-check config. To exercise the server end to end, UEFN must be open with
a project loaded and Python remote execution enabled (below).

## Architecture

Four modules in `src/uefn_mcp/`, each depending only on the ones below:

- **`remote_execution.py`** — vendored, unmodified copy of Epic's
  `PythonScriptRemoteExecution` client (see its `Copyright Epic Games`
  header). Treat as third-party: no project-specific logic goes here, so it
  stays a drop-in match for whatever ships with the engine.
- **`bridge.py`** — `UEFNBridge`, a thread-safe wrapper around one command
  connection (module singleton via `get_bridge()`). Connects lazily,
  reconnects once on a stale connection. Two entry points:
  - `exec_raw(code, exec_mode)` — raw protocol result dict.
  - `exec_json(code, **params)` — the primary interface. Wraps `code` so
    `params` arrive as an in-editor `_params` dict, requires `code` to assign
    its answer to `result`, and extracts it from stdout between
    `@@UEFN_MCP_RESULT_START@@` / `@@UEFN_MCP_RESULT_END@@` markers (the
    editor's own log output can't otherwise be told apart from the answer).
    Raises `UEFNScriptError` if the markers are missing or the script failed.

  Each bridge reserves **its own command port**. Epic's client defaults every
  process to 6776 with `SO_REUSEADDR`, so two Claude Code sessions used to
  fight over one port until both died. Don't reintroduce a shared default.
- **`editor_ui.py`** — the exception to all of the above: it does not talk
  to the editor over the protocol at all, it presses keys on the editor's
  *window*, with `ctypes` and Win32 only. It exists for one job, compiling
  Verse, which has no scriptable trigger and used to be the one step that
  stopped and waited for a person. Keep it to that: anything reachable
  through `unreal.*` belongs in `server.py`, not here. The window is matched
  by **executable**, never by title, and the keystroke is withheld unless
  that window really is in the foreground — a wrong match means keys sent
  somewhere they were not meant to go.
- **`server.py`** — `MCPServer("uefn-mcp")` and the `@mcp.tool()` definitions.
  Every tool except `execute_python` builds a Python source string calling
  into `unreal.*` and hands it to `get_bridge().exec_json(...)`. Shared
  snippets (`_ACTOR_LOOKUP`, `_transform_dict`, `_VERSE_CLASS`) are string
  builders concatenated per tool.

When adding a tool: write the `unreal` Python as a string ending in an
assignment to `result`, pass arguments through as `exec_json(..., key=value)`
kwargs, and keep the docstring precise — it is what the client sees when
deciding whether to call it.

**A tool is the right home for a procedure with one correct form.** Several
tools exist only because prose kept being followed wrongly: `set_actor_transform`
does `modify()` + teleport + nudge-and-return + save because a bare
`set_actor_location` silently loses work, and `validate_level` saves first
because `is_object_valid` lies before a save. If a doc says "always remember
to X", that is a signal X belongs in the tool.

## UEFN prerequisite

Unlike stock Unreal Editor, UEFN ships **two** independent Python switches off
by default, and both must be on or discovery just never hears a `pong` —
there is no error distinguishing "plugin inactive" from "plugin active but
not listening."

1. **Python Scripting** (Project Settings > Python) —
   `bEnablePythonForProject` under `dataSets.experimental.pythonExperimental`
   in the `.uefnproject` JSON.
2. **Remote execution** — a `Config/DefaultEngine.ini` next to the
   `.uefnproject` file with:

```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
RemoteExecutionMulticastGroupEndpoint=239.0.0.1:6766
RemoteExecutionMulticastBindAddress=127.0.0.1
RemoteExecutionMulticastTtl=0
```

`setup_uefn_project` sets both. Both are read only at editor startup, so UEFN
must be restarted afterwards — including when Python Scripting was turned on
by hand while the editor was running. Only one editor can be connected at a
time; discovery picks the first node it finds.

## Working with `unreal.*` APIs

There is no local `unreal` module to introspect against — it exists only
inside the running editor. Use `execute_python` against a live UEFN instance
to explore, and to discover Fortnite device/Blueprint class paths (none are
hardcoded here) before wiring a dedicated tool around them.

Before concluding something can only be done by hand in the Details panel,
check the `uefn-knowledge` skill. Most "V2" device settings that look
read-only are writable via `set_editor_property` with the option's exact key
name; a raw asset that fails validation usually has a Blueprint wrapper that
passes. Add to `docs/` whenever a session turns up another finding — with a
`description:` in the frontmatter, or it will index as `—`.
