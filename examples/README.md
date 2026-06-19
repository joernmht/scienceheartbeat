# Examples

## `demo/` — a ready-made dashboard

Open [`demo/index.html`](demo/index.html) in any browser to see the heartbeat
without scanning a repository. It is a single self-contained file (HTML + CSS +
JS + data inlined), generated from synthetic, deterministic data so it has no
machine-specific paths.

- [`demo/index.html`](demo/index.html) — the dashboard
- [`demo/heartbeat.json`](demo/heartbeat.json) — the underlying document

## Regenerate the demo

```bash
python examples/generate_demo.py
```

The generator (`generate_demo.py`) fabricates two repositories' worth of
commits with a *seeded* RNG and runs them through the real pipeline. The output
is byte-for-byte reproducible — CI re-runs it and fails if `examples/demo`
drifts.

## Build a dashboard from your own repositories

```bash
# one repo
scienceheartbeat build ~/code/my-repo --out my-dashboard

# a folder of repos
scienceheartbeat build ~/code --out my-dashboard

# build and serve
scienceheartbeat serve ~/code
```
