"""Build the heartbeat graph (nodes, edges, pulses) from scanned repos + activity.

This is the bridge from raw signals — git history *and* machine activity — to
the renderable model. It is deterministic end to end: identities are derived by
stable hashing, every collection is sorted before it is returned, and pulse
intensity is a dataset-independent function of an event's size (so adding
history never perturbs earlier pulses).

With no activity it emits exactly the git-only graph (repos · branches ·
committers). With activity it adds the *machine* layer around a central
``server`` node: ``loop``/``bot``/``agent`` nodes that ``runs_on`` it, ``notifies``
edges (loop → bot → owner), ``accessed`` edges (server → synced repo, agent →
touched repo), and one pulse per activity event travelling its own path.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence

from scienceheartbeat.activity.model import ActivityEvent, event_color
from scienceheartbeat.classify.change_kind import PALETTE, classify_commit
from scienceheartbeat.core.ids import (
    agent_id,
    bot_id,
    branch_id,
    committer_id,
    edge_id,
    event_pulse_id,
    loop_id,
    pulse_id,
    repo_id,
    server_id,
    slug,
)
from scienceheartbeat.core.model import (
    Edge,
    EdgeKind,
    EventKind,
    Node,
    NodeKind,
    Pulse,
)
from scienceheartbeat.graph.layout import compute_layout, compute_layout_server
from scienceheartbeat.scan.git import ScannedRepo

__all__ = ["build_graph", "intensity_for"]

# Dataset-independent intensity scale: a commit of this many changed lines
# reaches full brightness. Chosen empirically; versioned with the layout.
_INTENSITY_REFERENCE = 1500.0
_INTENSITY_FLOOR = 0.12

_SERVER_LABEL = "the box"


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


def _actor_node_id(event: ActivityEvent) -> str:
    """Stable node id for the participant that owns ``event``."""

    if event.actor_kind == NodeKind.SERVER:
        return server_id()
    if event.actor_kind == NodeKind.LOOP:
        return loop_id(event.actor_key)
    if event.actor_kind == NodeKind.BOT:
        return bot_id(event.actor_key)
    return agent_id(event.actor_key)


def build_graph(
    repos: list[ScannedRepo],
    events: Sequence[ActivityEvent] = (),
    *,
    owner_email: str | None = None,
) -> tuple[list[Node], list[Edge], list[Pulse]]:
    """Return the sorted nodes, edges and pulses for ``repos`` and ``events``.

    ``events`` is the machine-activity stream (see
    :mod:`scienceheartbeat.activity`); when empty the result is exactly the
    git-only graph. ``owner_email`` names the human a message/notification
    travels to (matched against the commit committers); when unknown, messages
    route to/from the server node instead.
    """

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

    # --- logical commit structure -----------------------------------------
    repo_branches: list[tuple[str, list[str]]] = []
    repo_meta: list[tuple[str, str, str]] = []  # (repo_id, repo_label, branch_id)
    for index, repo in enumerate(ordered):
        name = display_names[index]
        rid = repo_id(name)
        bid = branch_id(name, repo.branch)
        repo_branches.append((rid, [bid]))
        repo_meta.append((rid, name, bid))

    committer_ids = sorted(committer_names)
    committer_set = set(committer_ids)
    repo_by_slug = {slug(name): rid for rid, name, _ in repo_meta}

    has_activity = bool(events)
    server = server_id()

    # --- machine actors (loops / bot / agents) ----------------------------
    actor_labels: dict[str, tuple[NodeKind, str]] = {}
    server_label = _SERVER_LABEL
    for event in events:
        aid = _actor_node_id(event)
        if event.actor_kind == NodeKind.SERVER:
            server_label = event.actor_label or server_label
            continue
        actor_labels.setdefault(aid, (event.actor_kind, event.actor_label))
    machine_ids = sorted(actor_labels)
    bot_node = next((aid for aid in machine_ids if actor_labels[aid][0] == NodeKind.BOT), None)
    owner_node = (
        committer_id(owner_email, "")
        if owner_email and committer_id(owner_email, "") in committer_set
        else None
    )

    # --- positions --------------------------------------------------------
    if has_activity:
        positions = compute_layout_server(server, machine_ids, repo_branches, committer_ids)
    else:
        positions = compute_layout(repo_branches, committer_ids)

    # --- nodes ------------------------------------------------------------
    nodes: list[Node] = []
    for index, repo in enumerate(ordered):
        rid, name, bid = repo_meta[index]
        rx, ry = positions[rid]
        bx, by = positions[bid]
        nodes.append(Node(id=rid, kind=NodeKind.REPO, label=name, parent=None, x=rx, y=ry))
        nodes.append(Node(id=bid, kind=NodeKind.BRANCH, label=repo.branch, parent=rid, x=bx, y=by))

    for cid in committer_ids:
        cx, cy = positions[cid]
        nodes.append(
            Node(
                id=cid, kind=NodeKind.COMMITTER, label=committer_label(cid), parent=None, x=cx, y=cy
            )
        )

    if has_activity:
        sx, sy = positions[server]
        nodes.append(
            Node(id=server, kind=NodeKind.SERVER, label=server_label, parent=None, x=sx, y=sy)
        )
        for aid in machine_ids:
            kind, label = actor_labels[aid]
            ax, ay = positions[aid]
            nodes.append(Node(id=aid, kind=kind, label=label, parent=server, x=ax, y=ay))

    # --- edges (de-duplicated) --------------------------------------------
    edges: list[Edge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    def add_edge(kind: EdgeKind, src: str, dst: str) -> None:
        key = (kind.value, src, dst)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            Edge(id=edge_id(kind.value, src, dst), kind=kind, source=src, target=dst, label=None)
        )

    for rid, _, bid in repo_meta:
        add_edge(EdgeKind.BRANCH_OF, bid, rid)

    authored: set[tuple[str, str]] = set()
    for index, repo in enumerate(ordered):
        _, _, bid = repo_meta[index]
        for commit in repo.commits:
            authored.add((committer_id(commit.author_email, commit.author_name), bid))
    for cid, bid in sorted(authored):
        add_edge(EdgeKind.AUTHORED, cid, bid)

    # --- commit pulses ----------------------------------------------------
    pulses: list[Pulse] = []
    for index, repo in enumerate(ordered):
        rid, name, bid = repo_meta[index]
        for commit in repo.commits:
            cid = committer_id(commit.author_email, commit.author_name)
            primary, breakdown = classify_commit([f.path for f in commit.files])
            pulses.append(
                Pulse(
                    id=pulse_id(name, commit.sha),
                    t=commit.author_time,
                    event=EventKind.COMMIT,
                    node=bid,
                    path=[cid, bid, rid],
                    category=primary.value,
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

    # --- activity edges + pulses ------------------------------------------
    if has_activity:
        for aid in machine_ids:
            add_edge(EdgeKind.RUNS_ON, aid, server)
        if bot_node is not None:
            for aid in machine_ids:
                if actor_labels[aid][0] == NodeKind.LOOP:
                    add_edge(EdgeKind.NOTIFIES, aid, bot_node)
            if owner_node is not None:
                add_edge(EdgeKind.NOTIFIES, bot_node, owner_node)

        for event in events:
            pulses.append(
                _activity_pulse(event, server, bot_node, owner_node, repo_by_slug, add_edge)
            )

    nodes.sort(key=lambda n: n.id)
    edges.sort(key=lambda e: e.id)
    pulses.sort(key=lambda p: (p.t, p.id))
    return nodes, edges, pulses


def _activity_pulse(
    event: ActivityEvent,
    server: str,
    bot_node: str | None,
    owner_node: str | None,
    repo_by_slug: dict[str, str],
    add_edge: Callable[[EdgeKind, str, str], None],
) -> Pulse:
    """Build one pulse (and any access edge) for an activity ``event``."""

    aid = _actor_node_id(event)
    rid = repo_by_slug.get(slug(event.repo)) if event.repo else None
    node = aid
    path: list[str] = [aid]

    if event.event == EventKind.LOOP_RUN:
        node, path = aid, [server, aid]
    elif event.event == EventKind.SYNC:
        if rid is not None:
            add_edge(EdgeKind.ACCESSED, server, rid)
            node, path = rid, [server, rid]
        else:
            node, path = server, [server]
    elif event.event == EventKind.MESSAGE:
        origin = owner_node or server
        if event.direction == "out":
            node, path = origin, [aid, origin]
        else:
            node, path = aid, [origin, aid]
    elif event.event == EventKind.SESSION:
        entry = bot_node or server
        node, path = aid, [entry, aid]
    elif event.event == EventKind.ACCESS:
        if rid is not None:
            add_edge(EdgeKind.ACCESSED, aid, rid)
            node, path = rid, [aid, rid]
        else:
            node, path = aid, [aid]

    return Pulse(
        id=event_pulse_id(event.event.value, event.uid),
        t=event.t,
        event=event.event,
        node=node,
        path=path,
        category=event.category,
        color=event_color(event.category),
        intensity=event.intensity,
        source=event.actor_label,
        source_id=aid,
        repo=rid or "",
        branch="",
        title=event.title,
        detail=event.detail,
    )
