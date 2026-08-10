# uefn-mcp

Lets Claude build Fortnite maps for you inside UEFN (Unreal Editor for
Fortnite) — placing props, moving things around, browsing your content —
instead of you clicking through the editor UI by hand.

## What you need first

- UEFN installed, with a project created.
- [Claude Code](https://claude.ai/code).

That's it — Claude can install everything else itself.

## Setup

Open a terminal in this folder, start Claude Code, and paste this:

> Install and register the uefn-mcp server with Claude Code: check whether
> `uv` is installed and install it if it's missing, run `uv sync` in this
> folder, then run
> `claude mcp add uefn --scope user -- uv --directory "$(pwd)" run uefn-mcp`.

`--scope user` registers the server globally instead of tying it to this one
folder, so it's also available from other working directories — e.g. a
`fortnite-maps` notes workspace set up via the `fortnite-map-setup` skill
(see [docs/INDEX.md](docs/INDEX.md)).

Once that's done, **start a new Claude Code session** in this folder (MCP
servers only connect when a session starts). Then open UEFN with your
project loaded and paste this:

> Set up my UEFN project for remote execution.

Claude will find your project on disk and turn on the two settings UEFN
needs — Python Scripting itself (Project Settings > Python) and remote
execution for it — both off by default. If UEFN was already open, Claude
will tell you to restart it — these settings only take effect on startup.

Once UEFN is back up with your project loaded, you're ready to build.

## What to ask Claude to do

Once it's set up, just describe what you want in your own words. For example:

> Show me everything currently placed in my level

> Spawn a chest at the center of the map

> Move the actor called "SpawnPoint_1" up by 200 units

> Duplicate "Tree_03" and offset the copy to the side

> What props/devices are available in my content browser?

> Save the level

If Claude gets stuck because it doesn't know the exact name of a Fortnite
device or prop, it can look through your content browser itself to find it
— you don't need to know Unreal or Python to use any of this.

## Limitations

- Only one UEFN instance can be connected at a time — if you have more than
  one open, Claude connects to whichever one it finds first.
- Claude finds things you've placed by their name in the World Outliner, so
  giving actors clear, unique names helps it find the right one.

## How it works

See [docs/INDEX.md](docs/INDEX.md) for a deeper look at the architecture, the wire
protocol this talks to UEFN, and a traced example of a tool call end to end.
