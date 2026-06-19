"""Assemble the canonical :class:`HeartbeatDocument` from scanned repos."""

from __future__ import annotations

from scienceheartbeat.classify.change_kind import PALETTE
from scienceheartbeat.core.model import HeartbeatDocument, SourceInfo
from scienceheartbeat.export.json_io import stamp_hash
from scienceheartbeat.graph.build import build_graph
from scienceheartbeat.scan.git import ScannedRepo
from scienceheartbeat.timeline.build import time_bounds
from scienceheartbeat.versions import (
    CLASSIFIER_VERSION,
    LAYOUT_VERSION,
    PALETTE_VERSION,
    SCHEMA_VERSION,
)

__all__ = ["build_document"]


def build_document(repos: list[ScannedRepo]) -> HeartbeatDocument:
    """Build a fully-stamped, content-hashed heartbeat document.

    The result is deterministic: identical scanned input yields byte-identical
    JSON via :func:`scienceheartbeat.export.json_io.dumps`.
    """

    nodes, edges, pulses = build_graph(repos)
    t_min, t_max = time_bounds(pulses)

    sources = sorted(
        (
            SourceInfo(
                name=repo.name,
                path=repo.path,
                branch=repo.branch,
                head=repo.head,
                commits=len(repo.commits),
            )
            for repo in repos
        ),
        key=lambda s: (s.name, s.path),
    )

    palette = {kind.value: color for kind, color in PALETTE.items()}

    document = HeartbeatDocument(
        schema_version=SCHEMA_VERSION,
        palette_version=PALETTE_VERSION,
        classifier_version=CLASSIFIER_VERSION,
        layout_version=LAYOUT_VERSION,
        sources=sources,
        nodes=nodes,
        edges=edges,
        pulses=pulses,
        palette=palette,
        t_min=t_min,
        t_max=t_max,
    )
    return stamp_hash(document)
