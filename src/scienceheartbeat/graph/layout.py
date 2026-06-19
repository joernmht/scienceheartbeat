"""Deterministic graph layout.

Positions are a pure function of the (already deterministic) node grouping, so
the dashboard never runs a randomised force simulation. Coordinates are emitted
in an arbitrary centred unit space; the dashboard fits them to the viewport.

There are two layouts. :func:`compute_layout` is the git-only one (repos on an
inner ring, branches orbiting, committers outside). :func:`compute_layout_server`
is used when machine-activity nodes are present: the server sits at the centre
with the loops/bot/agents that *run on* it on an inner ring, the repositories
and their branches further out, and the committers on the outermost ring.
"""

from __future__ import annotations

import math

__all__ = ["Position", "compute_layout", "compute_layout_server"]

#: A laid-out point.
Position = tuple[float, float]

_R_REPO = 230.0  # radius of the inner repo ring (0 when there is a single repo)
_R_BRANCH = 95.0  # branch orbit radius around its repo
_R_COMMITTER = 470.0  # outer committer ring
_TOP = -math.pi / 2  # start angle (12 o'clock) for visual stability

# Server-centric layout: concentric rings out from the machine at the origin.
_S_R_MACHINE = 185.0  # loops / bot / agents that run on the server
_S_R_REPO = 400.0  # repositories
_S_R_BRANCH = 78.0  # branch orbit around its repo
_S_R_COMMITTER = 640.0  # committers (outermost)


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


def compute_layout_server(
    server: str,
    machine: list[str],
    repos: list[tuple[str, list[str]]],
    committers: list[str],
) -> dict[str, Position]:
    """Compute positions for the server-centric (machine-activity) layout.

    ``server`` is the single server node id (placed at the origin). ``machine``
    are the loop/bot/agent ids on the inner ring, ``repos`` the ordered
    ``(repo_id, [branch_id, ...])`` pairs on the middle ring, and ``committers``
    the outer ring. All ordering is the caller's responsibility (sorted by id)
    and fully determines the layout.
    """

    positions: dict[str, Position] = {server: (0.0, 0.0)}

    for index, node_id in enumerate(machine):
        positions[node_id] = _ring(len(machine), index, _S_R_MACHINE)

    repo_count = len(repos)
    for repo_index, (repo_id, branch_ids) in enumerate(repos):
        center = _ring(max(repo_count, 1), repo_index, _S_R_REPO)
        positions[repo_id] = center
        branch_count = len(branch_ids)
        for branch_index, branch_id in enumerate(branch_ids):
            if branch_count == 1:
                # Push a single branch radially outward from the centre.
                norm = math.hypot(center[0], center[1]) or 1.0
                ux, uy = center[0] / norm, center[1] / norm
                positions[branch_id] = (
                    center[0] + ux * _S_R_BRANCH,
                    center[1] + uy * _S_R_BRANCH,
                )
            else:
                offset = _ring(branch_count, branch_index, _S_R_BRANCH)
                positions[branch_id] = (center[0] + offset[0], center[1] + offset[1])

    for index, committer_id in enumerate(committers):
        positions[committer_id] = _ring(len(committers), index, _S_R_COMMITTER)

    return positions
