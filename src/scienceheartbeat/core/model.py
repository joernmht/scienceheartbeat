"""Canonical, frozen data model for a science *heartbeat*.

This module is the **single source of truth** for the project. Everything
else — git scanning, classification, graph building, the exported JSON
document and the web dashboard — is derived from the types declared here.

The model deliberately mirrors ``schema/heartbeat.schema.json``. It is built
for *determinism*: every model is frozen and forbids extra fields, every
collection is emitted in a sorted, stable order, and no field carries
wall-clock state. Given the same repository history and the same inputs, the
derived :class:`HeartbeatDocument` is byte-for-byte reproducible.

The node and edge *kinds* are intentionally broader than the MVP needs. The
MVP emits only ``repo``/``branch``/``committer`` nodes, but the enums already
name the future participants (a ``server`` node, ``agent`` nodes for Claude,
``bot`` nodes for Telegram, and ``loop`` nodes for recurring jobs) so they can
be added without a schema migration. See ``docs/roadmap.md``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ChangeKind",
    "Edge",
    "EdgeKind",
    "HeartbeatDocument",
    "KindCount",
    "Node",
    "NodeKind",
    "Pulse",
    "SourceInfo",
]


class ChangeKind(StrEnum):
    """The category a change falls into, used to colour its heartbeat pulse.

    Order is significant: it is the deterministic tie-break used to pick a
    commit's *primary* kind when two categories touch the same number of
    files (earlier members win). See :func:`scienceheartbeat.classify`.
    """

    CODE = "code"
    TESTS = "tests"
    DOCS = "docs"
    BUILD = "build"
    DEPS = "deps"
    CONFIG = "config"
    DATA = "data"
    ASSETS = "assets"
    OTHER = "other"


class NodeKind(StrEnum):
    """The kind of participant a node represents.

    ``REPO``/``BRANCH``/``COMMITTER`` are emitted by the MVP. ``SERVER``,
    ``AGENT``, ``BOT`` and ``LOOP`` are reserved for the roadmap (a machine
    node, Claude agents, Telegram bots and recurring loops).
    """

    REPO = "repo"
    BRANCH = "branch"
    COMMITTER = "committer"
    SERVER = "server"
    AGENT = "agent"
    BOT = "bot"
    LOOP = "loop"


class EdgeKind(StrEnum):
    """The relationship an edge encodes.

    ``AUTHORED`` (committer → branch) and ``BRANCH_OF`` (branch → repo) are
    emitted by the MVP. The remainder are reserved for the roadmap.
    """

    AUTHORED = "authored"
    BRANCH_OF = "branch_of"
    ACCESSED = "accessed"
    RUNS_ON = "runs_on"
    NOTIFIES = "notifies"


class _Frozen(BaseModel):
    """Base for every model: frozen and ``extra="forbid"`` for determinism."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class KindCount(_Frozen):
    """How many files of a given :class:`ChangeKind` a commit touched."""

    kind: ChangeKind
    files: int = Field(ge=0)


class Node(_Frozen):
    """A participant in the heartbeat graph with a baked-in layout position.

    Positions are computed deterministically by
    :mod:`scienceheartbeat.graph.layout` and stored here so the dashboard is a
    pure function of the document (no client-side layout randomness).
    """

    id: str
    kind: NodeKind
    label: str
    parent: str | None = None
    x: float
    y: float


class Edge(_Frozen):
    """A directed relationship between two nodes."""

    id: str
    kind: EdgeKind
    source: str
    target: str
    label: str | None = None


class Pulse(_Frozen):
    """A single change event — one git commit — that lights up a node.

    ``path`` is the chain of node ids the pulse travels along for the
    travelling-light effect (committer → branch → repo). ``node`` is the
    primary node that brightens (the branch). ``t`` is the author time in UTC
    epoch seconds: *when the change was made*.
    """

    id: str
    t: int
    node: str
    path: list[str]
    kind: ChangeKind
    color: str
    intensity: float = Field(ge=0.0, le=1.0)
    source: str
    source_id: str
    repo: str
    branch: str
    title: str
    ref: str
    insertions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    files_changed: int = Field(ge=0)
    kinds: list[KindCount]


class SourceInfo(_Frozen):
    """Provenance for one scanned repository."""

    name: str
    path: str
    branch: str
    head: str
    commits: int = Field(ge=0)


class HeartbeatDocument(_Frozen):
    """The complete, deterministic artifact the dashboard consumes.

    Resource versions are stamped in for reproducibility, mirroring the
    convention used across the sibling ``lp2graph`` project. ``content_hash``
    is a SHA-256 over the canonical JSON of every other field; see
    :func:`scienceheartbeat.export.json_io.content_hash`.
    """

    schema_version: str
    palette_version: str
    classifier_version: str
    layout_version: str
    sources: list[SourceInfo]
    nodes: list[Node]
    edges: list[Edge]
    pulses: list[Pulse]
    palette: dict[str, str]
    t_min: int
    t_max: int
    content_hash: str = ""
