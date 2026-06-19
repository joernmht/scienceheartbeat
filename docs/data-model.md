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

`id`, `kind` (git: `repo` · `branch` · `committer`; machine: `server` ·
`agent` · `bot` · `loop`), `label`, `parent` (e.g. a branch's repo id, or the
server for a machine actor), and the baked layout `x`, `y`.

## `Edge`

`id`, `kind`, `source`, `target`, optional `label`. Kinds: `authored`
(committer → branch) and `branch_of` (branch → repo) from git; `runs_on`
(loop/bot/agent → server), `notifies` (loop → bot, bot → owner) and `accessed`
(server → synced repo, agent → touched repo) from machine activity.

## `Pulse`

One activity event (see **Event kinds**). Fields: `t` (epoch seconds), `event`
(the discriminator), `node` (the node that lights up), `path` (the node-id
chain for the travelling light — e.g. `[committer, branch, repo]` for a commit,
`[server, loop]` for a loop run), `category` + `color` (the palette key and its
colour), `intensity` (0–1), `source` + `source_id` (the actor), `repo`,
`branch`, `title`, `detail`. The commit-only fields `ref` (short sha),
`insertions`, `deletions`, `files_changed` and `kinds` (per-kind file breakdown)
default to empty for non-commit events.

## Event kinds

`commit`, `sync`, `loop_run`, `message`, `session`, `access`. Non-commit events
come from the deterministic, **redacting** [`activity/`](../src/scienceheartbeat/activity)
source (loop logs, git remote-tracking reflogs, a Telegram audit log,
`.sessions.json`). All free text is masked for tokens/credentials/e-mails before
it reaches a pulse, and the real-activity artifact is **private** (the public
demo is synthetic).

## Categories and the palette

The document `palette` maps every `category` to a hex colour. Two families:

- **Change kinds** (commit `category`): `code`, `tests`, `docs`, `build`,
  `deps`, `config`, `data`, `assets`, `other`. Declaration order is also the
  tie-break for a commit's primary kind. See
  [`classify/change_kind.py`](../src/scienceheartbeat/classify/change_kind.py).
- **Event categories** (activity `category`): `push`, `pull`, `loop-ok`,
  `loop-fail`, `msg-in`, `msg-out`, `session`, `access`. See
  [`activity/model.py`](../src/scienceheartbeat/activity/model.py).

## Identities

Ids are stable hashes (`core/ids.py`), never the salted builtin `hash()`. A
committer's identity keys on the lower-cased e-mail, so the same person is one
node across repositories even if their display name varies.
