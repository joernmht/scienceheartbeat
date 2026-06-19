# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
