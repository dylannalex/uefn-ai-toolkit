---
description: Verse behaviours that compile fine and are wrong at runtime — PlayerAddedEvent missing everyone already present, block archetypes as call arguments, and what persistence can and can't do.
---

# Verse gotchas

Findings about the Verse language and its Fortnite APIs, as opposed to
driving the editor from Python. Each was found by a device behaving wrongly
in a real match, not by a compile error.

## `PlayerAddedEvent` is not "for each player"

It is **"for each player who arrives after you subscribe"**. At a normal
match start every player is already in the playspace when a device's
`OnBegin` runs, so a handler subscribed only to `PlayerAddedEvent` never runs
for anyone.

This killed a device outright: its player→slot map stayed empty, and the loop
that granted items iterated an empty map every 10 seconds, forever, in every
match. The symptom reported by players was "we never get anything", with no
error anywhere.

**Always pair it with an explicit sweep of the players already present:**

```verse
OnBegin<override>()<suspends> : void =
    for (P : GetPlayspace().GetPlayers()):
        OnPlayerAdded(P)
    GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerAdded)
```

Worth auditing any device that subscribes to it.

## A device subscribed to a timer still has to start the timer

Subscribing to a `Timer`'s `SuccessEvent` does not start the timer. A device
that only subscribes and never calls `Start()` will sit silent forever, which
looks identical to a wiring problem.

Check the timer device's own configuration before adding `Start()`, though —
if it is set to auto-start, calling `Start()` as well double-fires it.

## A block-form archetype can't be used as a call argument

```verse
SaveStats(P, skywars_stats:      # does not compile
    Kills := Old.Kills
    Wins := Old.Wins)
```

Bind the archetype to a local first, then pass the local.

## Persistence is per-player, and that is a hard limit

Verse persistable data is stored **per player**. A player can be shown their
own history, and the players present in a match can be ranked against each
other, but the stats of absent players cannot be read.

An all-time global leaderboard across everyone who ever played is therefore
not available. That is a platform design constraint, not a gap in any
particular implementation — don't design around it expecting to find a way.

## A player is in the playspace before their character exists

Granting anything from `OnBegin` can drop it into thin air. Wait for
`GetFortCharacter[]` to succeed (with a timeout) before acting on a player's
position or inventory.

## No `.digest.verse` files exist to check APIs against

There are no digest files anywhere in this install, so an API's exact
signature cannot be verified locally before compiling. Compiling is a manual
click in UEFN (`Verse > Build Verse Code`) with no scriptable trigger — see
[event-wiring.md](event-wiring.md) — so a wrong guess costs a round trip
through the user. Write conservatively.
