# The dashboard

The dashboard is a single self-contained HTML file produced by
`export/html.py:render_html`. It inlines three source assets from
`dashboard/assets/` — `index.html` (a template with `/*__STYLE__*/`,
`/*__APP__*/` and `__HEARTBEAT_DATA__` markers), `style.css` and `app.js` —
plus the document JSON, so it opens straight from disk with no server and no
network.

## The engine is pure

The Canvas engine in `app.js` is a **pure function of the document and the
timeline cursor**. Wall-clock time is used only to advance the cursor smoothly
while playing and for cosmetic twinkle; the visual state at any given cursor
time is fully reproducible. Even the background starfield uses a *seeded*
mulberry32 PRNG — there is no `Math.random` anywhere.

## What you see

- **Nodes** glow with an additive radial gradient. A node's brightness is the
  sum of its recent pulses' activations; its colour is the activation-weighted
  blend of those pulses' category colours. When machine activity is present the
  **server** is largest and central, then repos, then the loop/bot/agent
  actors, branches and committers; each machine kind has its own idle tint.
- **Pulses** ripple along their `path`: a commit travels committer → branch →
  repo, a loop run server → loop, a sync server → repo, and so on. The
  destination node flares then decays like a heartbeat (a quick rise, an
  exponential fall). The travelling light handles any path length (1–3 hops).
- **The ECG strip** at the bottom is an activity waveform across the whole
  timeline, its stroke coloured by the dominant category at each moment. A
  playhead marks the cursor.
- **The legend** lists the palette in two groups — change kinds and activity
  categories — with per-category counts.
- **"Now playing"** names the event at the cursor: its source, target and the
  detail appropriate to its kind (commit churn, sync host, loop status, …).
- **The activity side rail** is a time-ordered, click-to-seek list of events,
  filterable by type (all / commits / syncs / loops / msgs / sessions); the
  current event is highlighted and scrolled into view during playback.

## Controls

- **Play / pause** and **speed** (0.5×–4×). The timeline loops for an ambient,
  living feel.
- **Scrub** with the slider, or **click/drag the ECG** waveform.
- **Filter** the side rail by event type; **click a row** to seek to it.
- **Pan** by dragging the canvas, **zoom** with the wheel, **double-click** to
  reset the view. **Hover** a node for a tooltip.

## Editing the engine

Keep it dependency-free and keep the purity property. After editing `app.js`:

```bash
node --check src/scienceheartbeat/dashboard/assets/app.js
```

CI runs the same check.
