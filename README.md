# science heartbeat

[![ci](https://github.com/joernmht/scienceheartbeat/actions/workflows/ci.yml/badge.svg)](https://github.com/joernmht/scienceheartbeat/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**A deterministic heartbeat dashboard for your repositories.**

`scienceheartbeat` turns the change history of your git repositories into a
living *graph*: repositories and their branches are nodes that softly **pulse**
when a change lands, in a colour keyed to the *kind* of change, along a
**timeline you can scrub through**. The source of every change — the
committer — is a node too, and each pulse is a travelling light that runs from
the committer, through the branch, to the repository.

It is built **deterministically from the ground up**: the pipeline reads git
history and emits a frozen, content-hashed JSON document that is byte-for-byte
reproducible. The dashboard is a single, dependency-free HTML file that is a
*pure function* of that document.

## See it live

The demo dashboard is a single self-contained HTML file. **A GitHub `blob`
link shows its source, not the rendered page** — to actually view it, use one
of these:

- **Hosted (GitHub Pages):** <https://joernmht.github.io/scienceheartbeat/>
  (enable once via Settings → Pages → Source: "GitHub Actions"; see
  [`.github/workflows/pages.yml`](.github/workflows/pages.yml)).
- **Instant preview (no setup):**
  [open the demo via raw.githack](https://raw.githack.com/joernmht/scienceheartbeat/claude/compassionate-goldberg-vctos3/examples/demo/index.html).
- **Locally:** download [`examples/demo/index.html`](examples/demo/index.html)
  and open it in a browser, or run `scienceheartbeat serve` (below).

## Install

```bash
pip install scienceheartbeat            # from PyPI (once published)
pip install -e ".[dev]"                 # from a clone, with the dev tools
```

The only runtime dependency is `pydantic`. `git` must be on your `PATH`.

## 60-second tour

```bash
# Build a self-contained dashboard from one or more repos (or a parent folder).
scienceheartbeat build ~/code/my-repo ~/code/another --out heartbeat-dashboard

# …or build and serve it (opens your browser).
scienceheartbeat serve ~/code --port 8765

# …or just emit the deterministic data document.
scienceheartbeat scan ~/code/my-repo > heartbeat.json
```

`build` writes a single, double-clickable `index.html` (everything inlined —
no server, no network) plus the underlying `heartbeat.json`.

It can also beat for the **whole machine**, not just commits — repository syncs,
recurring loop runs, remote messages and sessions:

```bash
# PRIVATE: ingests real machine activity → defaults to gitignored heartbeat-private/.
scienceheartbeat build ~/code --activity --owner-email you@example.com
```

See [Machine activity](#machine-activity-private) below — this output is private
and redacted; never publish it.

From Python:

```python
from scienceheartbeat import heartbeat_from_paths, render_html

doc = heartbeat_from_paths(["~/code/my-repo"])
open("index.html", "w").write(render_html(doc))   # self-contained dashboard
print(doc.content_hash)                            # stable across runs
```

There is a ready-made demo at [`examples/demo/index.html`](examples/demo) —
open it in a browser to see the heartbeat without scanning anything.

## What the dashboard shows

- **Nodes.** Each repository is a node; its branch orbits it; each committer
  is a node on the outer ring, shared across repositories they touch.
- **Pulses.** Every commit is a pulse. When the timeline cursor reaches it, a
  light travels committer → branch → repo and the branch node glows. Glow
  **intensity** scales with the size of the commit (a log of lines changed).
- **Colour = kind of change.** Each commit is classified — `code`, `tests`,
  `docs`, `build`, `deps`, `config`, `data`, `assets`, `other` — and the pulse
  takes that colour. The legend shows the palette and per-kind counts.
- **Timeline.** An ECG-style waveform of activity over time. Press play, change
  speed (0.5×–4×), or click/drag the waveform to scrub. The "now playing" panel
  names each event's **source**, target and detail.
- **Activity side rail.** A time-ordered, click-to-seek list of events you can
  filter by type (commits, syncs, loops, messages, sessions).

With `--activity`, machine nodes appear too: a central **server** with the
**loops**, **bot** and **agents/sessions** that run on it, `sync`/`loop`/
`message`/`session`/`access` pulses, and their own legend colours.

## Machine activity (private)

`--activity` folds four extra signals into the heartbeat, each via a
deterministic, **redacting** parser:

| signal | source | becomes |
|---|---|---|
| repository syncs | git remote-tracking reflogs | `sync` (push/pull) |
| recurring loop runs | run logs (`logs/*.log`) | `loop_run` (ok/fail) |
| remote messages | a Telegram/remote audit log | `message` (inbound) |
| remote sessions | `.sessions.json` | `session` + repo `access` |

**Privacy.** This reflects a real machine, so it is treated as private. All free
text is masked for tokens (e.g. the Overleaf git-bridge `olp_…`), URL
credentials and e-mails before it can reach a document; remote hosts are shown
without their token; loop-run bodies are never read in. `--activity` defaults to
a **gitignored `heartbeat-private/`** directory and prints a do-not-publish
notice. The public demo under `examples/` uses **synthetic** data only.

Flags: `--activity`, `--loops-dir DIR`, `--no-loops` (syncs only),
`--owner-email EMAIL`, `--sync-limit N`.

## How the change kinds are coloured

| kind | meaning | colour |
|---|---|---|
| `code` | source files | `#4fd1ff` |
| `tests` | test files / dirs | `#7cffb2` |
| `docs` | docs, `*.md`, `README` | `#ffd166` |
| `build` | CI, Dockerfile, Makefile, `.github/` | `#ff8fa3` |
| `deps` | lockfiles / manifests | `#f78c6c` |
| `config` | `*.toml/yaml/ini`, dotfiles | `#c792ea` |
| `data` | `*.csv/parquet/…` | `#82aaff` |
| `assets` | images, fonts, media | `#c3e88d` |
| `other` | everything else | `#9fb0c0` |

## Determinism

Determinism is a hard requirement, not a nice-to-have:

- The model is **frozen** and forbids extra fields; every emitted collection is
  sorted (`pulses` by `(time, id)`, nodes/edges by `id`).
- Identities are **stable hashes**, never the salted builtin `hash()`.
- Timestamps come straight from git as UTC epoch integers — no timezone or
  locale dependence.
- The JSON is serialised with sorted keys, and a SHA-256 **`content_hash`** is
  stamped in. Resource versions (schema/palette/classifier/layout) are stamped
  in too, so old artifacts stay self-describing.
- The dashboard uses wall-clock time only to animate smoothly; its visual state
  at any cursor position is a pure function of the document, and even the
  background starfield uses a *seeded* PRNG.

See [`docs/determinism.md`](docs/determinism.md).

## Roadmap

The MVP visualises repository changes and their committers. The data model
already reserves the node and edge kinds for what comes next, so they can be
added without a schema migration:

- a **server** node for the machine the work runs on;
- **loop** nodes for recurring local jobs, beating in the same timeline;
- a **bot** node for Telegram;
- **agent** nodes for Claude, including an `accessed` edge when an agent works
  in a cloned repository.

See [`docs/roadmap.md`](docs/roadmap.md).

## Documentation

- [Architecture](docs/architecture.md) — the derive-from-one-source pipeline
- [Data model](docs/data-model.md) — the canonical document
- [The dashboard](docs/dashboard.md) — how the heartbeat is rendered
- [Determinism](docs/determinism.md) — what is guaranteed, and how
- [Roadmap](docs/roadmap.md) — server, loops, Telegram and Claude nodes

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Bug reports and feature ideas have
issue templates. CI runs ruff, ruff-format, `mypy --strict` and pytest on
Python 3.11–3.13.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
