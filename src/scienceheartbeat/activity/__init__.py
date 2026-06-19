"""Machine-activity source: loop runs, syncs, messages and sessions.

This package is to non-git activity what :mod:`scienceheartbeat.scan` is to git
history — a set of deterministic parsers that emit :class:`ActivityEvent`
records for the graph builder to turn into nodes, edges and pulses. All free
text is redacted before it leaves a parser.
"""

from __future__ import annotations

from scienceheartbeat.activity.collect import DEFAULT_LOOPS_DIR, collect_activity
from scienceheartbeat.activity.model import EVENT_PALETTE, ActivityEvent, Category, event_color

__all__ = [
    "DEFAULT_LOOPS_DIR",
    "EVENT_PALETTE",
    "ActivityEvent",
    "Category",
    "collect_activity",
    "event_color",
]
