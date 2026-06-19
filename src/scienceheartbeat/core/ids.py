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
    "branch_id",
    "committer_id",
    "edge_id",
    "pulse_id",
    "repo_id",
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


def edge_id(kind: str, source: str, target: str) -> str:
    """Stable id for an edge, hashed to keep it compact."""

    return f"edge:{kind}:{_digest(f'{source}->{target}', 16)}"
