"""Deterministic identifier helpers.

Every id is a pure function of stable inputs (repo name, branch name,
committer identity, commit sha). We hash with :mod:`hashlib` rather than the
builtin :func:`hash`, which is salted per-process and therefore not stable
across runs.
"""

from __future__ import annotations

import hashlib
import re

__all__ = [
    "agent_id",
    "bot_id",
    "branch_id",
    "committer_id",
    "edge_id",
    "event_pulse_id",
    "loop_id",
    "pulse_id",
    "repo_id",
    "server_id",
    "short_sha",
    "slug",
]

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def _digest(value: str, length: int = 12) -> str:
    """Return a stable hex digest prefix of ``value``."""

    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def slug(value: str) -> str:
    """Lower-case, collapse non-alphanumerics to ``-``, and strip edges."""

    return _NON_SLUG.sub("-", value.lower()).strip("-") or "x"


def short_sha(sha: str, length: int = 12) -> str:
    """Return the first ``length`` characters of a commit sha."""

    return sha[:length]


def repo_id(name: str) -> str:
    """Stable node id for a repository."""

    return f"repo:{slug(name)}"


def branch_id(repo_name: str, branch: str) -> str:
    """Stable node id for a branch within a repository."""

    return f"branch:{slug(repo_name)}:{slug(branch)}"


def committer_id(email: str, name: str) -> str:
    """Stable node id for a committer identity.

    Identity keys on the lower-cased e-mail when present (the most stable
    handle), otherwise the lower-cased name. The result is hashed so the id is
    a fixed shape and does not leak the raw address.
    """

    key = email.strip().lower() or name.strip().lower()
    return f"committer:{_digest(key)}"


def pulse_id(repo_name: str, sha: str) -> str:
    """Stable id for a pulse (one commit in one repo)."""

    return f"pulse:{slug(repo_name)}:{short_sha(sha)}"


def server_id(name: str = "server") -> str:
    """Stable node id for the machine everything runs on."""

    return f"server:{slug(name)}"


def loop_id(name: str) -> str:
    """Stable node id for a recurring (cron-like) loop."""

    return f"loop:{slug(name)}"


def bot_id(name: str = "telegram") -> str:
    """Stable node id for a messaging bot."""

    return f"bot:{slug(name)}"


def agent_id(key: str) -> str:
    """Stable node id for an agent / remote session.

    ``key`` is hashed so a long or sensitive handle (e.g. a session uuid) does
    not leak into the id while staying a fixed, stable shape.
    """

    return f"agent:{_digest(key)}"


def event_pulse_id(event: str, key: str) -> str:
    """Stable id for a non-commit activity pulse.

    ``key`` uniquely identifies the event within its kind (a log line, a sync
    reflog entry, a session id). It is hashed so the id is compact and stable.
    """

    return f"event:{slug(event)}:{_digest(key, 16)}"


def edge_id(kind: str, source: str, target: str) -> str:
    """Stable id for an edge, hashed to keep it compact."""

    return f"edge:{kind}:{_digest(f'{source}->{target}', 16)}"
