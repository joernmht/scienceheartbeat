# Architecture

`scienceheartbeat` is built around **one canonical model**; everything else is
derived from it on demand. The canonical model is the frozen pydantic
`HeartbeatDocument` in `core/model.py`, which mirrors
`schema/heartbeat.schema.json`.

```
git repos / folders
  → scan/        deterministic `git log --numstat` parser + repo discovery
  → activity/    deterministic, redacting parsers for machine activity (optional)
  → classify/    path → ChangeKind (fixed precedence) + versioned colour palette
  → graph/       repo·branch·committer + server·loop·bot·agent nodes, edges, pulses + layout
  → timeline/    time bounds
  → export/      canonical JSON (sorted keys, SHA-256 content_hash) + self-contained HTML
  → dashboard/   dependency-free Canvas engine (assets/) + a static server
```

## Stages

### `scan/`

`scan_repo()` shells out to `git log --numstat` with a pretty format that uses
ASCII record/field separators, reading author/committer **epoch** timestamps
(`%at`/`%ct`) so there is no timezone or locale dependence. `discover_repos()`
finds repositories beneath a folder. The output is a `ScannedRepo` (a list of
`Commit`s, each with classified `FileChange`s). No third-party dependency is
used — just the `git` binary.

### `activity/` (optional, private)

The counterpart to `scan/` for non-git signals. `collect_activity()` runs four
deterministic parsers and merges their `ActivityEvent`s in sorted order:
`loops.py` (recurring-loop run logs → `loop_run`), `syncs.py` (git
remote-tracking reflogs → `sync` push/pull), `telegram.py` (a bot audit log →
inbound `message`) and `sessions.py` (`.sessions.json` → `session`, plus an
`access` event when a session's prompt names a scanned repo). Every parser sorts
its output and routes all free text through `redact.py`, which masks tokens
(e.g. the Overleaf git-bridge `olp_…`), URL credentials and e-mails — so no
secret can reach a document. This output reflects a real machine and is treated
as **private** (the public demo is synthetic).

### `classify/`

`classify_path()` maps a single path to exactly one `ChangeKind` through a
fixed-precedence rule chain (so it never depends on iteration order).
`classify_commit()` tallies a commit's files and picks a *primary* kind. The
`PALETTE` assigns each kind a colour and is versioned by `PALETTE_VERSION`.

### `graph/`

`build_graph(repos, events)` turns scanned repos (and optional activity events)
into:

- **Nodes** — `repo`/`branch`/`committer` from git; and, when activity is
  present, one `server` node plus `loop`/`bot`/`agent` nodes for the machine
  actors.
- **Edges** — `branch_of` and `authored` from git; `runs_on` (actor → server),
  `notifies` (loop → bot → owner) and `accessed` (server → synced repo, agent →
  touched repo) from activity.
- **Pulses** — one per commit (`path` `[committer, branch, repo]`), plus one per
  activity event travelling its own path (e.g. `[server, loop]` for a loop run,
  `[server, repo]` for a sync). Each carries a `category`/`colour` and a
  dataset-independent `intensity`.

With no activity, `build_graph` emits exactly the git-only graph (no server
node), so the original behaviour is unchanged. `layout.py` bakes deterministic
positions: the git-only layout (repos inner, committers outer) or, when activity
is present, the **server-centric** layout (server at the centre, machine actors
on an inner ring, repos/branches further out, committers outermost).

### `export/`

`build_document()` assembles the stamped, content-hashed `HeartbeatDocument`.
`json_io.py` serialises it canonically (sorted keys, stable separators).
`html.py` inlines the dashboard assets and the document JSON into one
self-contained file.

### `dashboard/`

The Canvas engine in `assets/app.js`. It is a *pure function* of the document
and the timeline cursor — see [the dashboard page](dashboard.md).

## Why one canonical model

Deriving views on demand keeps every stage a small, testable, pure function,
and it makes determinism enforceable at one boundary (the emitted document)
rather than scattered across the codebase.
