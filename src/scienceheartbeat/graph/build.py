"""Build the heartbeat graph (nodes, edges, pulses) from scanned repos.

This is the bridge from raw git history to the renderable model. It is
deterministic end to end: identities are derived by stable hashing, every
collection is sorted before it is returned, and pulse intensity is a
dataset-independent function of a commit's size (so adding history never
perturbs earlier pulses).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from scienceheartbeat.classify.change_kind import PALETTE, classify_commit
from scienceheartbeat.core.ids import branch_id, committer_id, edge_id, pulse_id, repo_id, slug
from scienceheartbeat.core.model import Edge, EdgeKind, Node, NodeKind, Pulse
from scienceheartbeat.graph.layout import compute_layout
from scienceheartbeat.scan.git import ScannedRepo

__all__ = ["build_graph", "intensity_for"]

# Dataset-independent intensity scale: a commit of this many changed lines
# reaches full brightness. Chosen empirically; versioned with the layout.
_INTENSITY_REFERENCE = 1500.0
_INTENSITY_FLOOR = 0.12


def intensity_for(insertions: int, deletions: int) -> float:
    """Map a commit's churn to a glow intensity in ``[floor, 1]``.

    Uses a log scale so a handful of large commits do not wash everything else
    out, and a floor so even tiny commits remain visible.
    """

    magnitude = insertions + deletions
    raw = math.log1p(magnitude) / math.log1p(_INTENSITY_REFERENCE)
    return round(max(_INTENSITY_FLOOR, min(1.0, raw)), 4)


def _unique_repo_names(repos: list[ScannedRepo]) -> dict[int, str]:
    """Assign each repo (by index) a display name with a unique slug.

    Collisions (two repos whose names slugify identically) are disambiguated
    deterministically by appending an index in sorted order.
    """

    by_slug: dict[str, list[int]] = defaultdict(list)
    for index, repo in enumerate(repos):
        by_slug[slug(repo.name)].append(index)

    names: dict[int, str] = {}
    for index, repo in enumerate(repos):
        group = by_slug[slug(repo.name)]
        if len(group) == 1:
            names[index] = repo.name
        else:
            rank = group.index(index)
            names[index] = repo.name if rank == 0 else f"{repo.name} ({rank + 1})"
    return names


def build_graph(repos: list[ScannedRepo]) -> tuple[list[Node], list[Edge], list[Pulse]]:
    """Return the sorted nodes, edges and pulses for ``repos``."""

    ordered = sorted(repos, key=lambda r: (r.name, r.path))
    display_names = _unique_repo_names(ordered)

    # --- identities and labels --------------------------------------------
    committer_names: dict[str, Counter[str]] = defaultdict(Counter)
    for repo in ordered:
        for commit in repo.commits:
            cid = committer_id(commit.author_email, commit.author_name)
            committer_names[cid][commit.author_name or commit.author_email] += 1

    def committer_label(cid: str) -> str:
        counts = committer_names[cid]
        # Most frequent name, ties broken alphabetically for determinism.
        return min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    # --- nodes (logical structure first, then positions) ------------------
    repo_branches: list[tuple[str, list[str]]] = []
    repo_meta: list[tuple[str, str, str]] = []  # (repo_id, repo_label, branch_id)
    for index, repo in enumerate(ordered):
        name = display_names[index]
        rid = repo_id(name)
        bid = branch_id(name, repo.branch)
        repo_branches.append((rid, [bid]))
        repo_meta.append((rid, name, bid))

    committer_ids = sorted(committer_names)
    positions = compute_layout(repo_branches, committer_ids)

    nodes: list[Node] = []
    edges: list[Edge] = []
    for index, repo in enumerate(ordered):
        rid, name, bid = repo_meta[index]
        rx, ry = positions[rid]
        bx, by = positions[bid]
        nodes.append(Node(id=rid, kind=NodeKind.REPO, label=name, parent=None, x=rx, y=ry))
        nodes.append(Node(id=bid, kind=NodeKind.BRANCH, label=repo.branch, parent=rid, x=bx, y=by))
        edges.append(
            Edge(
                id=edge_id(EdgeKind.BRANCH_OF.value, bid, rid),
                kind=EdgeKind.BRANCH_OF,
                source=bid,
                target=rid,
                label=None,
            )
        )

    for cid in committer_ids:
        cx, cy = positions[cid]
        nodes.append(
            Node(
                id=cid,
                kind=NodeKind.COMMITTER,
                label=committer_label(cid),
                parent=None,
                x=cx,
                y=cy,
            )
        )

    # --- authored edges (committer -> branch), de-duplicated --------------
    authored: set[tuple[str, str]] = set()
    pulses: list[Pulse] = []
    for index, repo in enumerate(ordered):
        rid, name, bid = repo_meta[index]
        for commit in repo.commits:
            cid = committer_id(commit.author_email, commit.author_name)
            authored.add((cid, bid))
            primary, breakdown = classify_commit([f.path for f in commit.files])
            pulses.append(
                Pulse(
                    id=pulse_id(name, commit.sha),
                    t=commit.author_time,
                    node=bid,
                    path=[cid, bid, rid],
                    kind=primary,
                    color=PALETTE[primary],
                    intensity=intensity_for(commit.insertions, commit.deletions),
                    source=committer_label(cid),
                    source_id=cid,
                    repo=rid,
                    branch=bid,
                    title=commit.subject,
                    ref=commit.sha[:12],
                    insertions=commit.insertions,
                    deletions=commit.deletions,
                    files_changed=len(commit.files),
                    kinds=breakdown,
                )
            )

    for cid, bid in sorted(authored):
        edges.append(
            Edge(
                id=edge_id(EdgeKind.AUTHORED.value, cid, bid),
                kind=EdgeKind.AUTHORED,
                source=cid,
                target=bid,
                label=None,
            )
        )

    nodes.sort(key=lambda n: n.id)
    edges.sort(key=lambda e: e.id)
    pulses.sort(key=lambda p: (p.t, p.id))
    return nodes, edges, pulses
