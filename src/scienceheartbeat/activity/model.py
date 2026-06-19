"""The activity *source*: deterministic machine-activity events.

Where :mod:`scienceheartbeat.scan` reads git history, this package reads the
other things that happen on the research machine — recurring loop runs,
repository syncs (push/pull), Telegram/remote messages and remote sessions —
and turns them into :class:`ActivityEvent` records. Those records are the input
to :func:`scienceheartbeat.graph.build.build_graph` exactly as scanned commits
are, so the heartbeat beats for the whole machine, not just for commits.

Determinism mirrors the rest of the project: every parser sorts its output,
times are epoch seconds, and all free text passes through
:mod:`scienceheartbeat.activity.redact` so secrets and tokens never reach an
artifact. :data:`EVENT_PALETTE` colours the event categories; it is merged with
the change-kind palette into the document and versioned by ``PALETTE_VERSION``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from scienceheartbeat.core.model import EventKind, NodeKind

__all__ = [
    "EVENT_PALETTE",
    "ActivityEvent",
    "Category",
    "event_color",
]


class Category:
    """The palette keys used by non-commit events (one colour each)."""

    PUSH = "push"
    PULL = "pull"
    LOOP_OK = "loop-ok"
    LOOP_FAIL = "loop-fail"
    MSG_IN = "msg-in"
    MSG_OUT = "msg-out"
    SESSION = "session"
    ACCESS = "access"


#: Event-category → hex colour, chosen to read as a soft glow on the dashboard's
#: dark background and to stay distinct from the change-kind palette. Versioned
#: by ``PALETTE_VERSION``.
EVENT_PALETTE: dict[str, str] = {
    Category.PUSH: "#3ddc97",
    Category.PULL: "#ffb454",
    Category.LOOP_OK: "#7ee787",
    Category.LOOP_FAIL: "#ff6b6b",
    Category.MSG_IN: "#a78bfa",
    Category.MSG_OUT: "#5cc8ff",
    Category.SESSION: "#e58cff",
    Category.ACCESS: "#ffd479",
}

#: Fallback colour for an unknown category (matches ChangeKind.OTHER).
_FALLBACK = "#9fb0c0"


def event_color(category: str) -> str:
    """Return the palette colour for an event ``category`` (fallback grey)."""

    return EVENT_PALETTE.get(category, _FALLBACK)


class ActivityEvent(BaseModel):
    """One thing that happened on the machine, ready to become a pulse.

    The fields are deliberately source-agnostic so the graph builder can place
    every kind of event with the same logic. ``actor_kind``/``actor_key``
    identify the participant node that owns the event (a loop, the bot, an
    agent/session, or the server); ``repo`` names a scanned repository when the
    event is repo-scoped (a sync or an access) so it can be wired to that node.
    All human text (``title``/``detail``) is already redacted.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event: EventKind
    t: int
    uid: str
    actor_kind: NodeKind
    actor_key: str
    actor_label: str
    category: str
    title: str
    detail: str = ""
    repo: str = ""
    direction: str = ""
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
