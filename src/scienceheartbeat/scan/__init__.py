"""Deterministic source scanning (git history, repo discovery)."""

from __future__ import annotations

from scienceheartbeat.scan.discover import discover_repos, is_git_repo
from scienceheartbeat.scan.git import (
    Commit,
    FileChange,
    ScanError,
    ScannedRepo,
    scan_repo,
)

__all__ = [
    "Commit",
    "FileChange",
    "ScanError",
    "ScannedRepo",
    "discover_repos",
    "is_git_repo",
    "scan_repo",
]
