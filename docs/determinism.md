# Determinism

Reproducibility is the whole premise of this project. Given the same repository
history and the same inputs, the emitted `heartbeat.json` is **byte-for-byte
identical**, and the rendered HTML is identical too.

## What is guaranteed

- **Frozen models.** Every model is `frozen` with `extra="forbid"`.
- **Sorted output.** `pulses` are sorted by `(t, id)`; `nodes` and `edges` by
  `id`; `sources` by `(name, path)`. Nothing depends on `set`/`dict` iteration
  order.
- **Stable ids.** Identities use `hashlib`, never the per-process-salted builtin
  `hash()`.
- **No timezone/locale dependence.** Timestamps come from git as UTC epoch
  integers (`%at`/`%ct`).
- **No wall-clock state** in any artifact — there is no "generated at" field.
- **Canonical JSON.** Serialised with `sort_keys=True` and stable separators.
- **Content hash.** A SHA-256 over every field except the hash itself is
  stamped into `content_hash`; `content_hash(doc)` recomputes and verifies it.
- **Stamped versions.** `schema`, `palette`, `classifier` and `layout` versions
  (`versions.py`) are stamped in, so an artifact stays self-describing if a rule
  changes later.
- **Dataset-independent intensity.** A pulse's `intensity` is a function of that
  one commit's churn, not of the rest of the dataset — adding history never
  perturbs earlier pulses.

## What is *not* part of the hash

The `path` of each scanned repository is recorded in `sources` for reference
and is included in the content hash. Because absolute paths differ between
machines, the document is reproducible "same inputs, **same paths** → identical
output". If you need a machine-independent hash, scan with stable names.

## The dashboard

The rendering engine uses real time only to advance the timeline cursor and for
cosmetic effects; its visual state at any cursor position is a pure function of
the document. Any randomness (the starfield) is seeded.

## Tests

`tests/test_determinism.py` builds the document twice from the same repository
and asserts the serialised JSON and rendered HTML are identical, and that the
content hash verifies. CI additionally regenerates `examples/demo` and fails if
it drifts.
