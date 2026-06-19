"""High-level orchestration: paths in, :class:`HeartbeatDocument` out.

This ties the deterministic stages together — discover repositories beneath
the given paths, scan each one's git history, and build the stamped document.
"""

from __future__ import annotations

from pathlib import Path

from scienceheartbeat.activity.collect import DEFAULT_LOOPS_DIR, collect_activity
from scienceheartbeat.core.model import HeartbeatDocument
from scienceheartbeat.export.document import build_document
from scienceheartbeat.scan.discover import discover_repos
from scienceheartbeat.scan.git import ScannedRepo, scan_repo

__all__ = ["heartbeat_from_paths", "scan_paths"]


def scan_paths(
    paths: list[str | Path],
    *,
    limit: int | None = None,
    include_merges: bool = False,
    max_depth: int = 3,
) -> list[ScannedRepo]:
    """Discover and scan every repository beneath each of ``paths``.

    Repositories are de-duplicated by resolved path and returned in a
    deterministic (sorted) order.
    """

    discovered: dict[str, Path] = {}
    for path in paths:
        for repo in discover_repos(path, max_depth=max_depth):
            discovered[str(repo.resolve())] = repo

    return [
        scan_repo(repo, limit=limit, include_merges=include_merges)
        for _, repo in sorted(discovered.items())
    ]


def heartbeat_from_paths(
    paths: list[str | Path],
    *,
    limit: int | None = None,
    include_merges: bool = False,
    max_depth: int = 3,
    activity: bool = False,
    loops_dir: str | Path | None = DEFAULT_LOOPS_DIR,
    owner_email: str | None = None,
    sync_limit: int | None = None,
) -> HeartbeatDocument:
    """Build a complete heartbeat document from the repositories under ``paths``.

    With ``activity=True`` the machine-activity stream (repository syncs, plus
    loop runs / messages / sessions from ``loops_dir``) is collected and folded
    into the document. ``owner_email`` names the human messages travel to;
    ``sync_limit`` caps the most-recent syncs kept per repository. This output
    is **private** — it reflects real machine activity and must not be published.
    """

    repos = scan_paths(paths, limit=limit, include_merges=include_merges, max_depth=max_depth)
    if not activity:
        return build_document(repos)
    events = collect_activity(repos, loops_dir=loops_dir, sync_limit=sync_limit)
    return build_document(repos, events, owner_email=owner_email)
