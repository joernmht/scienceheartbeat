"""Parse the Telegram/remote bot audit log into inbound message events.

The bot writes an audit line per interaction::

    2026-06-19T08:50:25 VOICE[de]: Was ist die letzte Änderung …
    2026-06-19T06:34:01 ASK[en] #11: The corpus is not finished …
    2026-06-17T07:10:00 UNLOCK ok

We surface the *inbound* remote traffic — questions (``ASK``), voice notes
(``VOICE``), change requests (``CHANGE``) and privileged ``UNLOCK`` attempts —
as ``MESSAGE`` events on the bot node. Message text is redacted and previewed,
never stored in full, and lifecycle/polling noise (``START``, ``bot started``,
``poll err``) is dropped. Outbound delivery is represented by the loops that
push notifications (see :mod:`scienceheartbeat.activity.loops`).
"""

from __future__ import annotations

import re
from pathlib import Path

from scienceheartbeat.activity.loops import _parse_iso
from scienceheartbeat.activity.model import ActivityEvent, Category
from scienceheartbeat.activity.redact import preview
from scienceheartbeat.core.model import EventKind, NodeKind

__all__ = ["telegram_events"]

_LINE = re.compile(r"^(?P<ts>\S+)\s+(?P<rest>.*)$")
_INBOUND = re.compile(
    r"^(?P<kind>ASK|VOICE|CHANGE|UNLOCK)"
    r"(?P<arrow>→\w+)?"
    r"(?:\[(?P<lang>\w+)\])?"
    r"(?:\s+#\d+)?"
    r":?\s*(?P<text>.*)$"
)
_BOT_KEY = "telegram"
_BOT_LABEL = "telegram bot"


def _event_from_line(lineno: int, line: str) -> ActivityEvent | None:
    head = _LINE.match(line)
    if head is None:
        return None
    t = _parse_iso(head.group("ts"))
    if t is None:
        return None
    body = _INBOUND.match(head.group("rest"))
    if body is None:
        return None  # START / bot started / poll err / other noise

    kind = body.group("kind")
    lang = body.group("lang") or ""
    voice = kind == "VOICE" or bool(body.group("arrow"))

    if kind == "UNLOCK":
        title = "/unlock"
        detail = "privileged"
    else:
        verb = "voice" if voice else kind.lower()
        title = preview(body.group("text"))
        detail = f"{verb}·{lang}" if lang else verb

    return ActivityEvent(
        event=EventKind.MESSAGE,
        t=t,
        uid=f"{lineno}:{head.group('ts')}",
        actor_kind=NodeKind.BOT,
        actor_key=_BOT_KEY,
        actor_label=_BOT_LABEL,
        category=Category.MSG_IN,
        title=title or "(message)",
        detail=detail,
        direction="in",
        intensity=0.6,
    )


def telegram_events(audit_log: str | Path) -> list[ActivityEvent]:
    """Return inbound ``MESSAGE`` events from a Telegram audit log, sorted.

    A missing file yields no events (not an error).
    """

    path = Path(audit_log).expanduser()
    if not path.is_file():
        return []
    events: list[ActivityEvent] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        event = _event_from_line(lineno, line)
        if event is not None:
            events.append(event)
    events.sort(key=lambda e: (e.t, e.uid))
    return events
