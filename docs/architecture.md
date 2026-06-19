# Architecture

`scienceheartbeat` is built around **one canonical model**; everything else is
derived from it on demand. The canonical model is the frozen pydantic
`HeartbeatDocument` in `core/model.py`, which mirrors
`schema/heartbeat.schema.json`.

```
git repos / folders
  → scan/        deterministic `git log --numstat` parser + repo discovery
  → classify/    path → ChangeKind (fixed precedence) + versioned colour palette
  → graph/       repo·branch·committer nodes, edges, one pulse per commit + layout
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

### `classify/`

`classify_path()` maps a single path to exactly one `ChangeKind` through a
fixed-precedence rule chain (so it never depends on iteration order).
`classify_commit()` tallies a commit's files and picks a *primary* kind. The
`PALETTE` assigns each kind a colour and is versioned by `PALETTE_VERSION`.

### `graph/`

`build_graph()` turns scanned repos into:

- **Nodes** — one `repo` node per repository, one `branch` node per scanned
  branch, one `committer` node per identity (shared across repos).
- **Edges** — `branch_of` (branch → repo) and `authored` (committer → branch).
- **Pulses** — one per commit, with a primary kind/colour, a dataset-independent
  `intensity`, the travelling `path` `[committer, branch, repo]`, and the
  change's source (committer).

`layout.py` assigns deterministic positions (repos on an inner ring, branches
orbiting them, committers on an outer ring) which are baked into the nodes so
the dashboard never runs a randomised simulation.

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
