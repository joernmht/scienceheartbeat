"""Gather every machine-activity source into one sorted event stream.

This is the activity counterpart to :func:`scienceheartbeat.pipeline.scan_paths`:
given the already-scanned repositories (for their paths and names) and the
loops directory, it runs each parser and merges the results deterministically.
Repository syncs come from the repos themselves; loop runs, messages and
sessions come from the loops directory. Any source that is absent simply
contributes nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from scienceheartbeat.activity.loops import loop_events
from scienceheartbeat.activity.model import ActivityEvent
from scienceheartbeat.activity.sessions import session_events
from scienceheartbeat.activity.syncs import sync_events
from scienceheartbeat.activity.telegram import telegram_events
from scienceheartbeat.scan.git import ScannedRepo

__all__ = ["DEFAULT_LOOPS_DIR", "collect_activity"]

#: Where the unattended research-ops loops live on this machine.
DEFAULT_LOOPS_DIR = "~/.claude/loops"


def collect_activity(
    scanned: Sequence[ScannedRepo],
    *,
    loops_dir: str | Path | None = DEFAULT_LOOPS_DIR,
    sync_limit: int | None = None,
) -> list[ActivityEvent]:
    """Return all activity events for ``scanned`` repos + ``loops_dir``, sorted.

    ``loops_dir`` supplies loop-run logs (``logs/``), the Telegram audit log
    (``tg_audit.log``) and the remote-session store (``.sessions.json``); pass
    ``None`` to skip them and emit repository syncs only. ``sync_limit`` caps the
    most-recent syncs kept per repository.
    """

    events: list[ActivityEvent] = []
    repo_names = [repo.name for repo in scanned]

    for repo in scanned:
        events.extend(sync_events(repo.path, repo.name, limit=sync_limit))

    if loops_dir is not None:
        base = Path(loops_dir).expanduser()
        events.extend(loop_events(base / "logs"))
        events.extend(telegram_events(base / "tg_audit.log"))
        events.extend(session_events(base / ".sessions.json", repo_names=repo_names))

    events.sort(key=lambda e: (e.t, e.event, e.uid))
    return events
