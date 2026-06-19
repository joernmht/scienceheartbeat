"""Timeline bounds for the heartbeat.

The dashboard derives its scrubber range and ECG waveform from the pulse
stream directly, so this module only needs to expose the deterministic time
bounds. Bounds use *author* time — when each change was made.
"""

from __future__ import annotations

from scienceheartbeat.core.model import Pulse

__all__ = ["time_bounds"]


def time_bounds(pulses: list[Pulse]) -> tuple[int, int]:
    """Return ``(t_min, t_max)`` over ``pulses`` (``(0, 0)`` when empty)."""

    if not pulses:
        return (0, 0)
    times = [p.t for p in pulses]
    return (min(times), max(times))
