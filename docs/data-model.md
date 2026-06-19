# Data model

The canonical artifact is the `HeartbeatDocument` (`core/model.py`), mirrored
by [`schema/heartbeat.schema.json`](../schema/heartbeat.schema.json). Every
model is frozen and forbids extra fields.

## `HeartbeatDocument`

| field | type | notes |
|---|---|---|
| `schema_version` | str | stamped from `versions.py` |
| `palette_version` | str | stamped |
| `classifier_version` | str | stamped |
| `layout_version` | str | stamped |
| `sources` | list[SourceInfo] | one per scanned repo, sorted |
| `nodes` | list[Node] | sorted by `id` |
| `edges` | list[Edge] | sorted by `id` |
| `pulses` | list[Pulse] | sorted by `(t, id)` |
| `palette` | dict[str, str] | change-kind → hex colour |
| `t_min`, `t_max` | int | UTC epoch bounds |
| `content_hash` | str | SHA-256 over all other fields |

## `Node`

`id`, `kind` (`repo` · `branch` · `committer` · reserved: `server` · `agent` ·
`bot` · `loop`), `label`, `parent` (e.g. a branch's repo id), and the baked
layout `x`, `y`.

## `Edge`

`id`, `kind` (`authored` · `branch_of` · reserved: `accessed` · `runs_on` ·
`notifies`), `source`, `target`, optional `label`.

## `Pulse`

One commit. `t` (author epoch seconds), `node` (the branch that lights up),
`path` (`[committer, branch, repo]` for the travelling light), `kind` + `color`,
`intensity` (0–1), `source` + `source_id` (the committer), `repo`, `branch`,
`title`, `ref` (short sha), `insertions`, `deletions`, `files_changed`, and
`kinds` (the per-kind file breakdown).

## Change kinds

`code`, `tests`, `docs`, `build`, `deps`, `config`, `data`, `assets`, `other`.
The declaration order is also the tie-break used to choose a commit's primary
kind. See [`classify/change_kind.py`](../src/scienceheartbeat/classify/change_kind.py).

## Identities

Ids are stable hashes (`core/ids.py`), never the salted builtin `hash()`. A
committer's identity keys on the lower-cased e-mail, so the same person is one
node across repositories even if their display name varies.
