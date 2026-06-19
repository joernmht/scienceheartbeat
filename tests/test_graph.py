from __future__ import annotations

from pathlib import Path

from scienceheartbeat.activity.model import ActivityEvent
from scienceheartbeat.core.model import EdgeKind, EventKind, NodeKind
from scienceheartbeat.graph import build_graph, intensity_for
from scienceheartbeat.scan import scan_repo


def test_build_graph_structure(sample_repo: Path) -> None:
    scanned = scan_repo(sample_repo)
    nodes, _edges, pulses = build_graph([scanned])

    kinds = [n.kind for n in nodes]
    assert kinds.count(NodeKind.REPO) == 1
    assert kinds.count(NodeKind.BRANCH) == 1
    assert kinds.count(NodeKind.COMMITTER) == 2  # ada + bob

    assert len(pulses) == 3
    # Every pulse travels committer -> branch -> repo.
    for p in pulses:
        assert len(p.path) == 3
        assert p.node == p.branch
        assert 0.0 <= p.intensity <= 1.0

    # Pulses are sorted by (t, id).
    assert [p.t for p in pulses] == sorted(p.t for p in pulses)


def test_intensity_is_monotonic_and_bounded() -> None:
    assert intensity_for(0, 0) == intensity_for(0, 0)
    assert intensity_for(0, 0) <= intensity_for(50, 50)
    assert intensity_for(10, 10) <= intensity_for(1000, 1000)
    assert 0.0 < intensity_for(0, 0) <= 1.0
    assert intensity_for(10_000, 10_000) <= 1.0


def test_nodes_have_layout_positions(sample_repo: Path) -> None:
    nodes, _, _ = build_graph([scan_repo(sample_repo)])
    # The single repo sits at the origin; other nodes are placed around it.
    repo = next(n for n in nodes if n.kind == NodeKind.REPO)
    assert (repo.x, repo.y) == (0.0, 0.0)
    committers = [n for n in nodes if n.kind == NodeKind.COMMITTER]
    assert all((n.x, n.y) != (0.0, 0.0) for n in committers)


def test_build_graph_with_activity(sample_repo: Path, sample_events: list[ActivityEvent]) -> None:
    nodes, edges, pulses = build_graph([scan_repo(sample_repo)], sample_events)

    node_kinds = {n.kind for n in nodes}
    assert {NodeKind.SERVER, NodeKind.LOOP, NodeKind.BOT, NodeKind.AGENT} <= node_kinds

    # In the server-centric layout the server is the origin.
    server = next(n for n in nodes if n.kind == NodeKind.SERVER)
    assert (server.x, server.y) == (0.0, 0.0)

    edge_kinds = {e.kind for e in edges}
    assert EdgeKind.RUNS_ON in edge_kinds  # loop/bot/agent -> server
    assert EdgeKind.ACCESSED in edge_kinds  # server -> synced repo, agent -> touched repo

    # 3 commits + 5 activity events, all events present.
    assert len(pulses) == 3 + len(sample_events)
    assert {p.event for p in pulses if p.event != EventKind.COMMIT} == {
        EventKind.LOOP_RUN,
        EventKind.SYNC,
        EventKind.MESSAGE,
        EventKind.SESSION,
        EventKind.ACCESS,
    }

    # The sync/access events wired to the matching repo node.
    sync = next(p for p in pulses if p.event == EventKind.SYNC)
    assert sync.repo.startswith("repo:")
    assert sync.node == sync.repo


def test_activity_is_opt_in(sample_repo: Path) -> None:
    # No events -> exactly the git-only graph (no server node).
    nodes, _, pulses = build_graph([scan_repo(sample_repo)])
    assert all(n.kind != NodeKind.SERVER for n in nodes)
    assert all(p.event == EventKind.COMMIT for p in pulses)
