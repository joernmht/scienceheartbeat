"""Deterministic graph layout.

Positions are a pure function of the (already deterministic) node grouping, so
the dashboard never runs a randomised force simulation. Repositories sit on an
inner ring, their branches orbit them, and committers occupy an outer ring.
Coordinates are emitted in an arbitrary centred unit space; the dashboard fits
them to the viewport.
"""

from __future__ import annotations

import math

__all__ = ["Position", "compute_layout"]

#: A laid-out point.
Position = tuple[float, float]

_R_REPO = 230.0  # radius of the inner repo ring (0 when there is a single repo)
_R_BRANCH = 95.0  # branch orbit radius around its repo
_R_COMMITTER = 470.0  # outer committer ring
_TOP = -math.pi / 2  # start angle (12 o'clock) for visual stability


def _ring(count: int, index: int, radius: float, phase: float = _TOP) -> Position:
    if count <= 0:
        return (0.0, 0.0)
    angle = phase + 2.0 * math.pi * index / count
    return (radius * math.cos(angle), radius * math.sin(angle))


def compute_layout(
    repos: list[tuple[str, list[str]]],
    committers: list[str],
) -> dict[str, Position]:
    """Compute positions for every node.

    ``repos`` is an ordered list of ``(repo_id, [branch_id, ...])`` pairs and
    ``committers`` an ordered list of committer ids. The ordering is the
    caller's responsibility (it sorts by id) and fully determines the layout.
    """

    positions: dict[str, Position] = {}
    repo_count = len(repos)

    for repo_index, (repo_id, branch_ids) in enumerate(repos):
        center = (0.0, 0.0) if repo_count == 1 else _ring(repo_count, repo_index, _R_REPO)
        positions[repo_id] = center

        branch_count = len(branch_ids)
        for branch_index, branch_id in enumerate(branch_ids):
            if branch_count == 1:
                # Offset a single branch slightly above its repo.
                positions[branch_id] = (center[0], center[1] - _R_BRANCH)
            else:
                offset = _ring(branch_count, branch_index, _R_BRANCH)
                positions[branch_id] = (center[0] + offset[0], center[1] + offset[1])

    for committer_index, committer_id in enumerate(committers):
        positions[committer_id] = _ring(len(committers), committer_index, _R_COMMITTER)

    return positions
