"""Discover git repositories under a path.

Pointing the tool at a single repo scans that repo; pointing it at a parent
folder finds the git repositories beneath it. Results are sorted for
determinism, and nested work trees are not descended into.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["discover_repos", "is_git_repo"]

_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build"}


def is_git_repo(path: Path) -> bool:
    """Return whether ``path`` contains a ``.git`` entry (dir or file)."""

    return (path / ".git").exists()


def discover_repos(root: str | Path, *, max_depth: int = 3) -> list[Path]:
    """Return git repositories at or beneath ``root``, sorted by path.

    If ``root`` itself is a repository it is returned directly. Otherwise the
    tree is walked up to ``max_depth`` levels; once a repository is found its
    subtree is not descended into.
    """

    base = Path(root).expanduser().resolve()
    if is_git_repo(base):
        return [base]

    found: list[Path] = []

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(p for p in directory.iterdir() if p.is_dir())
        except (PermissionError, FileNotFoundError):
            return
        for entry in entries:
            if entry.name in _SKIP_DIRS:
                continue
            if is_git_repo(entry):
                found.append(entry)
                continue  # do not descend into a discovered repo
            _walk(entry, depth + 1)

    _walk(base, 1)
    return sorted(found)
