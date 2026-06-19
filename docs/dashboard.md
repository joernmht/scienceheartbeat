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
  blend of those pulses' kind colours. Repos are largest, then branches, then
  committers.
- **Pulses** ripple along their `path`: when the cursor reaches a commit, a
  light travels committer → branch → repo, and the branch node flares then
  decays like a heartbeat (a quick rise, an exponential fall).
- **The ECG strip** at the bottom is an activity waveform across the whole
  timeline, its stroke coloured by the dominant change-kind at each moment. A
  playhead marks the cursor.
- **The legend** lists the palette and per-kind commit counts.
- **"Now playing"** names the change at the cursor: its source (committer),
  repo/branch, message, ref and churn.

## Controls

- **Play / pause** and **speed** (0.5×–4×). The timeline loops for an ambient,
  living feel.
- **Scrub** with the slider, or **click/drag the ECG** waveform.
- **Pan** by dragging the canvas, **zoom** with the wheel, **double-click** to
  reset the view. **Hover** a node for a tooltip.

## Editing the engine

Keep it dependency-free and keep the purity property. After editing `app.js`:

```bash
node --check src/scienceheartbeat/dashboard/assets/app.js
```

CI runs the same check.
