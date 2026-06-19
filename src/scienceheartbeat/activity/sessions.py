"""Parse the bot's remote-session store into session + access events.

The bot records each remote session it spawned in ``.sessions.json``::

    {"sessions": {"12": {"id": "12", "sid": "30cf…", "kind": "question",
                          "lang": "de", "prompt": "Was ist …", "ts": 1781859025}},
     "msg2sess": {…}, "counter": 12}

Each session becomes a ``SESSION`` event on an agent node (labelled by its short
id, never its uuid). When a session's prompt names a scanned repository, we also
emit an ``ACCESS`` event from that agent to the repo — "the remote session
touched this repo" — which is what the ``accessed`` edge encodes. Prompts are
redacted/previewed; full text is never stored.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from scienceheartbeat.activity.model import ActivityEvent, Category
from scienceheartbeat.activity.redact import preview
from scienceheartbeat.core.model import EventKind, NodeKind

__all__ = ["session_events"]


def _accessed_repos(prompt: str, repo_names: Sequence[str]) -> list[str]:
    """Return the scanned repo names mentioned in ``prompt`` (sorted, unique)."""

    low = prompt.lower()
    hits = {name for name in repo_names if name and name.lower() in low}
    return sorted(hits)


def session_events(
    sessions_file: str | Path,
    *,
    repo_names: Sequence[str] = (),
) -> list[ActivityEvent]:
    """Return ``SESSION`` (+ derived ``ACCESS``) events, sorted.

    ``repo_names`` are the display names of scanned repositories; a session whose
    prompt mentions one yields an extra ``ACCESS`` event linking its agent to
    that repo. A missing or malformed file yields no events (not an error).
    """

    path = Path(sessions_file).expanduser()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        sessions = raw["sessions"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    if not isinstance(sessions, dict):
        return []

    events: list[ActivityEvent] = []
    for key in sorted(sessions, key=lambda k: str(k)):
        entry = sessions[key]
        if not isinstance(entry, dict):
            continue
        sid = str(entry.get("sid") or entry.get("id") or key)
        ident = str(entry.get("id") or key)
        ts_raw = entry.get("ts")
        if not isinstance(ts_raw, (int, float)):
            continue
        ts = int(ts_raw)
        kind = str(entry.get("kind") or "session")
        lang = str(entry.get("lang") or "")
        prompt = str(entry.get("prompt") or "")
        label = f"session #{ident}"

        events.append(
            ActivityEvent(
                event=EventKind.SESSION,
                t=ts,
                uid=sid,
                actor_kind=NodeKind.AGENT,
                actor_key=sid,
                actor_label=label,
                category=Category.SESSION,
                title=preview(prompt) or f"{kind} session",
                detail=f"{kind}·{lang}" if lang else kind,
                intensity=0.7,
            )
        )

        for name in _accessed_repos(prompt, repo_names):
            events.append(
                ActivityEvent(
                    event=EventKind.ACCESS,
                    t=ts,
                    uid=f"{sid}:{name}",
                    actor_kind=NodeKind.AGENT,
                    actor_key=sid,
                    actor_label=label,
                    category=Category.ACCESS,
                    title=f"{label} touched {name}",
                    detail=kind,
                    repo=name,
                    intensity=0.5,
                )
            )

    events.sort(key=lambda e: (e.t, e.event, e.uid))
    return events
