# scienceheartbeat

A deterministic heartbeat dashboard for your repositories.

`scienceheartbeat` turns the change history of your git repositories into a
living *graph*: repositories and their branches pulse when a change lands, in a
colour keyed to the kind of change, along a timeline you can scrub through.

- **[Architecture](architecture.md)** — the derive-everything-from-one-source
  pipeline.
- **[Data model](data-model.md)** — the canonical `HeartbeatDocument`.
- **[The dashboard](dashboard.md)** — how the heartbeat is rendered.
- **[Determinism](determinism.md)** — what is guaranteed, and how.
- **[Roadmap](roadmap.md)** — the server, loop, Telegram and Claude nodes.

## Quick start

```bash
pip install -e ".[dev]"
scienceheartbeat serve ~/code/my-repo
```

Or open [`examples/demo/index.html`](../examples/demo) to see it immediately.
