# CLAUDE.md — {{WORKSPACE_NAME}}

Map projects built in UEFN with Claude Code, one subfolder per map.

This repository is **content, not framework**. It holds no skills, scripts or
templates — those live in the `uefn-mcp` plugin, installed once at user scope
and reachable from here without anything being copied in. Ask for the
`uefn-knowledge` skill for validated asset paths, device class paths and
`unreal.*` gotchas; they are deliberately not duplicated here.

It is also not the maps themselves: the real map data (the `.uefnproject`
file and its binary assets) lives wherever UEFN saved it. This is the
readable, git-friendly layer of context that survives between sessions.

## Working here

- **Start from [INDEX.md](INDEX.md)**, then the map's own `INDEX.md`. Every
  markdown directory has one, mapping file → description, so you can open the
  one file you need instead of reading a directory of prose. They are
  generated — never hand-edit an `INDEX.md`.
- **Only one UEFN editor can be connected at a time**, and discovery picks
  whichever node it finds first. Before running any `uefn` tool against a
  map, confirm the project open in UEFN is *that* map — compare
  `get_editor_status` against the map's `CLAUDE.md`.
- **Knowledge about Fortnite goes to `knowledge/`, not into the map's notes.**
  The test is: would this still be true if this map were deleted? If yes it
  is framework knowledge, and it gets migrated into the plugin later.
