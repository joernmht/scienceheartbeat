# Roadmap

The MVP visualises repository changes and their committers. The data model
already reserves the node and edge kinds for what comes next, so each can be
added **without a schema migration** — extend along these seams rather than
reshaping the schema.

## Reserved kinds

`NodeKind`: `server`, `agent`, `bot`, `loop`.
`EdgeKind`: `accessed`, `runs_on`, `notifies`.

## Planned participants

### Server node

A single `server` node for the machine your work runs on. Other nodes
(`loop`, `agent`, `bot`) connect to it with `runs_on` edges, anchoring the
graph around "the box this all happens on".

### Loops

Recurring local jobs become `loop` nodes that beat in the same timeline as
commits. Each run is a pulse on the loop node (a new "kind" of pulse, e.g.
keyed by exit status), so a cron-like job's health reads at a glance alongside
code activity.

### Telegram bot

A `bot` node with `notifies` edges to whatever it pings. Messages sent become
pulses, so you can see the bot's chatter in time with everything else.

### Claude agents

`agent` nodes for Claude sessions. The key edge is `accessed`: when an agent
works inside a *cloned* repository, draw an `accessed` edge from the agent to
that repo and pulse it — so "Claude touched this repo" is visible in the
heartbeat. Capturing that signal likely means a small hook or log shipper that
emits agent-access events the pipeline can ingest as a new source, mirroring
how `scan/` ingests git history today.

## How to contribute one

1. The node/edge kinds exist — use them.
2. Add a *source* (like `scan/`) that produces events deterministically.
3. Feed those into `graph/build.py` as new nodes/edges/pulses.
4. Version any new frozen resource in `versions.py` and stamp it in.
5. Keep it deterministic; add tests under `tests/`.
