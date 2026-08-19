# uefn-ai-toolkit

Build Fortnite maps by describing them to Claude, instead of clicking through
the UEFN editor by hand.

It is a Claude Code plugin with three parts: an MCP server that drives a
running UEFN editor over Epic's Python remote execution protocol, a set of
skills, and a knowledge base of what actually works in Fortnite Creative —
which assets are publish-safe, which device settings are scriptable, and
which routes are dead ends that look promising.

## What you need

- UEFN installed, with a project created.
- [Claude Code](https://claude.ai/code).
- [`uv`](https://docs.astral.sh/uv/) on your PATH (the server is Python).

## Install

```
/plugin marketplace add dylannalex/uefn-ai-toolkit
/plugin install uefn-ai-toolkit@dylannalex-uefn
```

Then **start a new Claude Code session** — MCP servers only connect at
session start. Open UEFN with your project loaded and ask:

> Set up my UEFN project for remote execution.

Claude finds the project on disk and turns on the two settings UEFN needs —
Python Scripting, and remote execution for it — both off by default. If UEFN
was already open you will be told to restart it; those settings are only read
at startup.

## Use it

Describe what you want:

> Show me everything currently placed in my level

> Spawn a chest at the centre of the map and put an assault rifle in it

> Move "SpawnPoint_1" up by 200 units

> Take a screenshot of the map from above so you can see it

> Check whether anything in my level will fail to publish

You don't need to know Unreal or Python. If Claude doesn't know a device or
prop's name, it can search your content browser for it.

## Keeping notes between sessions

Claude has no memory of the editor between conversations, and a `.uefnproject`
is binary — it can't be diffed or reviewed. Ask for a map project and the
plugin scaffolds a plain git repository of markdown alongside your map: the
design, what is currently built, what is still pending, and a build log.

> Set up a project folder for my new map

That repository is yours and holds no plugin files, so updating the plugin
never touches your notes.

## Limits worth knowing

- **One editor at a time.** Discovery connects to whichever UEFN instance it
  finds first, so keep one open. Several Claude Code sessions can now run
  against it — each gets its own command port.
- **Compiling Verse is a manual click.** There is no scriptable trigger for
  `Verse > Build Verse Code`; everything downstream of a compile is automated,
  the compile itself isn't.
- **Item content is only scriptable on Item Spawner V3.** Item Granter and
  Class Designer hold theirs behind a platform wall. This is documented rather
  than worked around, so nobody spends a session rediscovering it.
- Claude finds placed things by their World Outliner name, so clear, unique
  labels help.

## How it works

See `skills/uefn-knowledge/SKILL.md` for the knowledge base's routing table,
and [docs/internals/INDEX.md](docs/internals/INDEX.md) for the architecture,
the wire protocol, and a tool call traced end to end.
