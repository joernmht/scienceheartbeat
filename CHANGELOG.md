# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **TUD CRO chair corporate design**: the dashboard now wears the Chair of
  Railway Operations identity — TUD Dunkelblau field with a Türkis accent and
  the chair wordmark logo in the top bar. The Canvas engine reads its colours
  from CSS custom properties (`--canvas-*`, `--*-rgb`, `--accent-rgb`), so the
  glow, starfield and ECG follow the device appearance: dark by default, a
  light variant under `prefers-color-scheme: light` (the canvas keeps a deep
  field because the glow is additive and would vanish on white). The logo
  flips white on the dark field, brand-blue on light.
- **Mobile layout**: the three fixed panels no longer overlap on phones. Under
  720px the legend becomes a tap-to-show overlay (`key` button), the activity
  rail becomes a collapsible bottom drawer (`activity` button / drag handle),
  and the timeline goes edge-to-edge and compact with safe-area insets. The
  graph is now touch-navigable — one-finger pan, two-finger pinch-zoom, and
  touch-scrubbing on the ECG.
- **Trailing-range view**: a `7d` / `30d` / `all` toggle in the timeline
  controls narrows the visible window to the last week/month without
  rescanning. The cursor, ECG, scrub, legend totals and activity list all
  recompute for the selected range; the span label reads e.g. "42 events ·
  last 7d".

- **Machine activity** (`scienceheartbeat.activity`): the heartbeat now beats
  for the whole research machine, not just commits. Deterministic, redacting
  parsers turn four new signals into events — recurring **loop runs**
  (`logs/*.log`), repository **syncs** (push/pull from git remote-tracking
  reflogs), inbound **messages** (a Telegram/remote audit log) and remote
  **sessions** (`.sessions.json`, with agent → repo *access* detection).
- **Generalised pulse** (schema v2): a `Pulse` is now any activity event, not
  only a commit. Adds an `event` discriminator (`commit`/`sync`/`loop_run`/
  `message`/`session`/`access`), a free-form `category` palette key (replaces
  the commit-only `kind`) and a `detail` line; the commit churn fields are now
  optional. The reserved `server`/`agent`/`bot`/`loop` node kinds and
  `accessed`/`runs_on`/`notifies` edges are now emitted.
- **Server-centric layout** (layout v2) used when activity is present: the
  server sits at the centre with the loops/bot/agents that run on it on an
  inner ring, repositories and branches further out, committers outermost.
- **Activity event colours** added to the palette (palette v2): `push`, `pull`,
  `loop-ok`, `loop-fail`, `msg-in`, `msg-out`, `session`, `access`.
- **Dashboard**: renders the new node kinds, a per-event "now playing" panel,
  a two-group legend (changes + activity), and a new **activity / commit list
  side rail** — time-ordered, filterable by event type, click a row to seek.
- **CLI**: `--activity` (with `--loops-dir`, `--no-loops`, `--owner-email`,
  `--sync-limit`) on `build`/`serve`/`scan`.

### Privacy

- Secrets never reach an artifact: all free text passes a redaction pass that
  masks tokens (Overleaf git-bridge `olp_…`, GitHub, Slack), URL credentials
  and e-mails; remote hosts are surfaced without their token; loop-run bodies
  are never read into events.
- `--activity` output is **private** (real machine activity): it defaults to a
  gitignored `heartbeat-private/` directory and prints a do-not-publish notice.
  The public demo under `examples/` uses synthetic data only.

## [0.1.0] — 2026-06-19

Initial release — the MVP.

### Added

- **Deterministic core** (`scienceheartbeat.core`): a frozen pydantic
  `HeartbeatDocument` that is the single source of truth, mirroring
  `schema/heartbeat.schema.json`, with stable id helpers.
- **Git scanning** (`scienceheartbeat.scan`): a dependency-free `git log
  --numstat` parser reading UTC epoch timestamps, plus repository discovery
  beneath a folder.
- **Change classification** (`scienceheartbeat.classify`): a fixed-precedence
  path → change-kind classifier and a versioned colour palette.
- **Graph building** (`scienceheartbeat.graph`): repo / branch / committer
  nodes, authored / branch-of edges, one pulse per commit with a
  dataset-independent intensity, and a deterministic radial layout.
- **Export** (`scienceheartbeat.export`): canonical sorted-key JSON with a
  SHA-256 `content_hash`, and a self-contained dashboard HTML renderer.
- **Dashboard**: a dependency-free Canvas dashboard — glowing nodes, travelling
  light along edges, an ECG-style scrubbable timeline, a legend and a
  "now playing" panel naming the source of each change.
- **CLI**: `scienceheartbeat build | serve | scan | version`.
- A reproducible demo under `examples/`, full docs under `docs/`, a JSON
  Schema, and CI (ruff, ruff-format, mypy --strict, pytest on 3.11–3.13).

[Unreleased]: https://github.com/joernmht/scienceheartbeat/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/joernmht/scienceheartbeat/releases/tag/v0.1.0
