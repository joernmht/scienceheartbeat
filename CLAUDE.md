# CLAUDE.md — scienceheartbeat

Guidance for Claude Code working in this repository. These instructions
override default behavior; follow them exactly.

## What this is

`scienceheartbeat` turns git history into a deterministic, scrub-able
*heartbeat* dashboard. The **canonical pydantic `HeartbeatDocument`**
(`src/scienceheartbeat/core/model.py`) is the *single source of truth*;
everything else is derived from it:

```
git repos / folders
  → scan/        deterministic `git log --numstat` parser + repo discovery
  → classify/    path → ChangeKind (fixed precedence) + versioned colour palette
  → graph/       repo·branch·committer nodes, edges, one pulse per commit + layout
  → timeline/    time bounds
  → export/      canonical JSON (sorted keys, SHA-256 content_hash) + self-contained HTML
  → dashboard/   dependency-free Canvas engine (assets/) + a static server
  → core/model.py  HeartbeatDocument (mirrors schema/heartbeat.schema.json)
```

**Determinism is a hard requirement.** Models are frozen / `extra="forbid"`;
every emitted collection is sorted (pulses by `(t, id)`, nodes/edges by `id`);
the JSON has sorted keys and a stamped `content_hash`. Never introduce
nondeterminism: no `set`/`dict` iteration order in output, no `hash()` for ids
(it is salted — use `core.ids`), no wall-clock fields in artifacts, no unseeded
RNG (the dashboard's starfield uses a seeded mulberry32). `tests/test_determinism.py`
guards this.

## Running tests / lint / types in THIS environment

The package is **not** pip-installed by default here, so bare `pytest` errors
with `ModuleNotFoundError: scienceheartbeat`. **Prefix with `PYTHONPATH=src`**
(create a venv and install `pydantic`, `jsonschema`, `pytest`, `ruff`, `mypy`
first if they are missing):

```bash
PYTHONPATH=src python3 -m pytest -q                       # full suite
PYTHONPATH=src python3 -m ruff check src tests examples    # lint (line-length 100)
PYTHONPATH=src python3 -m ruff format src tests examples    # format (a pre-commit hook)
PYTHONPATH=src python3 -m mypy                              # mypy --strict, targets src/scienceheartbeat
node --check src/scienceheartbeat/dashboard/assets/app.js  # dashboard JS syntax
```

CI runs ruff + ruff-format + `mypy --strict src/scienceheartbeat` + pytest on
Linux/macOS for Python 3.11–3.13. Keep all four green.

## The dashboard (`src/scienceheartbeat/dashboard/assets/`)

Three source assets — `index.html` (a template with `/*__STYLE__*/`,
`/*__APP__*/`, `__HEARTBEAT_DATA__` markers), `style.css`, `app.js` — are
inlined by `export/html.py:render_html` into one self-contained file. The
engine is **pure**: its visual state at any cursor time is a function of the
document; wall-clock time is used only to advance the cursor smoothly. If you
edit `app.js`, keep it that way and re-run `node --check`.

## Conventions (match the surrounding code)

- `from __future__ import annotations` at the top of every module.
- Frozen pydantic models; explicit `__all__`; module + public-function
  docstrings explaining *why*. No `Any` in public APIs.
- Tests live in `tests/` with **no `__init__.py`** (don't add one).
- Optional dependencies (`jsonschema` in tests) are imported lazily / gated
  with `pytest.importorskip`.
- Version any new frozen resource in `versions.py` and stamp it into the
  document.

## Roadmap (don't break the reserved kinds)

`NodeKind` already names `server`, `agent`, `bot`, `loop`, and `EdgeKind`
names `accessed`, `runs_on`, `notifies`. These are intentional placeholders for
the server node, Claude agents, Telegram bot and recurring loops — see
`docs/roadmap.md`. Extend along these seams rather than reshaping the schema.
