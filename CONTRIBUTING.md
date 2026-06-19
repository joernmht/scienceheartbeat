# Contributing to scienceheartbeat

Thank you for your interest. This project is in alpha; the MVP is in place and
the roadmap (a server node, loops, Telegram and Claude nodes) is open. Almost
every kind of contribution moves it forward.

## Setup

```bash
git clone https://github.com/joernmht/scienceheartbeat
cd scienceheartbeat
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

> The package uses a `src/` layout. If you prefer not to install it, every
> command also works with `PYTHONPATH=src` (see [`CLAUDE.md`](CLAUDE.md)).

## Day-to-day commands

```bash
ruff check src tests examples       # lint
ruff format src tests examples      # format
mypy src/scienceheartbeat           # strict type-check
pytest                              # full suite
pytest --cov=scienceheartbeat       # with coverage
node --check src/scienceheartbeat/dashboard/assets/app.js   # JS syntax
```

CI runs ruff, ruff-format, `mypy --strict` and pytest across Linux + macOS for
Python 3.11, 3.12 and 3.13. Failures block merge.

## What to contribute

- **A new change-kind rule.** Extend the classifier in
  `scienceheartbeat/classify`. Keep it a pure function of the path; bump
  `CLASSIFIER_VERSION` if the mapping changes. Add a `test_classify` case.
- **A roadmap node.** A server / loop / Telegram / Claude node. The node and
  edge kinds already exist; see [`docs/roadmap.md`](docs/roadmap.md).
- **Dashboard polish.** The renderer is `dashboard/assets/app.js`. Keep the
  visual state a pure function of the document and the cursor; seed any
  randomness.
- **Docs.** Especially the data-model and determinism pages.

## Determinism is the rule

This project's whole premise is reproducibility. A change is only acceptable if
the emitted `heartbeat.json` stays byte-identical for identical inputs:

- no unsorted `set`/`dict` iteration in output — sort before emitting;
- no `hash()` for ids (it is salted) — use the helpers in `core.ids`;
- no wall-clock state in artifacts; seed every RNG.

`tests/test_determinism.py` guards this.

## PR expectations

- One logical change per PR. **Conventional Commits** (`feat:`, `fix:`,
  `docs:`, `test:`, `refactor:`, `chore:`).
- Reference the issue: `Closes #123`.
- Add a test for new behavior. Update docs when behavior changes.
- If you change the schema or a versioned resource, bump the matching version
  in `versions.py` and note it in `CHANGELOG.md`.

## Coding standards

- `mypy --strict` passes; no `Any` in public APIs.
- `from __future__ import annotations` at the top of every module; frozen
  models; explicit `__all__`; module + public-function docstrings.
- Optional dependencies are imported lazily inside the function that needs
  them.

## License

By contributing you agree your work is licensed under Apache 2.0, matching the
project. No CLA required.
