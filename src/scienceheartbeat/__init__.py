"""science heartbeat — a deterministic heartbeat dashboard for your repos.

Track changes across git repositories (or folders of repositories) and
visualise them as a living *heartbeat*: a graph whose repo/branch nodes softly
pulse in colours keyed to the kind of change, with a scrub-able timeline.

The package follows a derive-everything-from-one-source design: the frozen
:class:`~scienceheartbeat.core.model.HeartbeatDocument` is the single source of
truth, produced deterministically from git history and consumed by a
dependency-free web dashboard.

Quick start::

    from scienceheartbeat import heartbeat_from_paths, render_html

    doc = heartbeat_from_paths(["~/code/my-repo"])
    open("index.html", "w").write(render_html(doc))
"""

from __future__ import annotations

from scienceheartbeat.core.model import (
    ChangeKind,
    Edge,
    EdgeKind,
    HeartbeatDocument,
    Node,
    NodeKind,
    Pulse,
    SourceInfo,
)
from scienceheartbeat.export.html import render_html
from scienceheartbeat.export.json_io import dumps, loads, read, write
from scienceheartbeat.pipeline import heartbeat_from_paths, scan_paths
from scienceheartbeat.versions import PACKAGE_VERSION

__version__ = PACKAGE_VERSION

__all__ = [
    "ChangeKind",
    "Edge",
    "EdgeKind",
    "HeartbeatDocument",
    "Node",
    "NodeKind",
    "Pulse",
    "SourceInfo",
    "__version__",
    "dumps",
    "heartbeat_from_paths",
    "loads",
    "read",
    "render_html",
    "scan_paths",
    "write",
]
