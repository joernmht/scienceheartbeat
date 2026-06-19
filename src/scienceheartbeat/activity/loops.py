"""Parse recurring-loop run logs into :class:`ActivityEvent` loop runs.

The machine runs cron-driven loops (standup, radio, quality, …); each run
appends a log file named ``<NN-name>-<ISO>.log`` whose first and last lines mark
the run::

    === loop:01-standup start:2026-06-19T09:00:01+00:00 ===
    ... (run output — never embedded; may contain file contents) ...
    === loop:01-standup end:2026-06-19T09:02:05+00:00 rc:0 ===

We emit exactly one ``LOOP_RUN`` event per log file with metadata only (loop
name, start time, exit status, duration) — the run body is **not** read into the
artifact, so nothing the loop printed can leak. ``rc == 0`` colours the run
``loop-ok``; anything else ``loop-fail``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from scienceheartbeat.activity.model import ActivityEvent, Category
from scienceheartbeat.core.model import EventKind, NodeKind

__all__ = ["loop_events"]

_START = re.compile(r"start:(\S+)")
_END = re.compile(r"end:(\S+)\s+rc:(-?\d+)")
_NN_PREFIX = re.compile(r"^\d+[-_]")
_STAMP_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}T[\d-]+$")


def _parse_iso(value: str) -> int | None:
    """Parse an ISO-8601 timestamp to epoch seconds (UTC); ``None`` on failure.

    A timestamp without an offset is treated as UTC (the machine's clock).
    """

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def _loop_label(basename: str) -> str:
    """``01-standup`` → ``standup`` (drop the ordering prefix)."""

    return _NN_PREFIX.sub("", basename) or basename


def _loop_basename(filename: str) -> str:
    """``01-standup-2026-06-19T09-00-01.log`` → ``01-standup``."""

    stem = filename[:-4] if filename.endswith(".log") else filename
    return _STAMP_SUFFIX.sub("", stem)


def _event_from_log(path: Path) -> ActivityEvent | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    head = lines[0] if lines else ""
    tail = next((ln for ln in reversed(lines) if "end:" in ln and "rc:" in ln), "")

    start_match = _START.search(head)
    start = _parse_iso(start_match.group(1)) if start_match else None
    if start is None:
        return None

    end_match = _END.search(tail)
    if end_match:
        end = _parse_iso(end_match.group(1))
        rc = int(end_match.group(2))
    else:
        end, rc = None, None  # crashed / truncated: no end marker

    duration = max(0, end - start) if end is not None else 0
    ok = rc == 0
    basename = _loop_basename(path.name)
    label = _loop_label(basename)
    detail = "no exit marker" if rc is None else f"exit {rc} · {duration}s"

    return ActivityEvent(
        event=EventKind.LOOP_RUN,
        t=start,
        uid=path.name,
        actor_kind=NodeKind.LOOP,
        actor_key=basename,
        actor_label=label,
        category=Category.LOOP_OK if ok else Category.LOOP_FAIL,
        title=f"{label} loop",
        detail=detail,
        intensity=0.55 if ok else 0.85,
    )


def loop_events(logs_dir: str | Path) -> list[ActivityEvent]:
    """Return one ``LOOP_RUN`` event per log file under ``logs_dir``, sorted.

    A missing directory yields no events (not an error).
    """

    base = Path(logs_dir).expanduser()
    if not base.is_dir():
        return []
    events = [
        event for path in sorted(base.glob("*.log")) if (event := _event_from_log(path)) is not None
    ]
    events.sort(key=lambda e: (e.t, e.uid))
    return events
