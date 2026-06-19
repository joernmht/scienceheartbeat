"""Derive repository sync events from git's remote-tracking reflogs.

When a repository is pushed or pulled, git updates its remote-tracking refs and
logs the change under ``.git/logs/refs/remotes/<remote>/<branch>``::

    <old> <new> Name <email> 1781859656 +0000	update by push
    <old> <new> Name <email> 1781428131 +0000	fetch origin main: fast-forward

That is a precise, deterministic record of every sync with an epoch timestamp.
We classify ``update by push`` as an outbound ``push`` and ``fetch``/``pull``/
``clone`` as an inbound ``pull``. The remote *host* (github vs the Overleaf
bridge) is read from ``.git/config`` and passed through :func:`host_of`, so the
git-bridge **token in the URL is never stored** — only the bare host.
"""

from __future__ import annotations

import re
from pathlib import Path

from scienceheartbeat.activity.model import ActivityEvent, Category
from scienceheartbeat.activity.redact import host_of
from scienceheartbeat.core.model import EventKind, NodeKind

__all__ = ["sync_events"]

_SERVER_KEY = "server"
_SERVER_LABEL = "the box"
_REMOTE_HEADER = re.compile(r'^\[remote "(?P<name>[^"]+)"\]')
_URL_LINE = re.compile(r"^\s*url\s*=\s*(?P<url>.+?)\s*$")


def _remote_hosts(git_dir: Path) -> dict[str, str]:
    """Map each remote name to its bare host (token-free); ``{}`` if unreadable."""

    config = git_dir / "config"
    try:
        lines = config.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    hosts: dict[str, str] = {}
    current = ""
    for line in lines:
        header = _REMOTE_HEADER.match(line)
        if header:
            current = header.group("name")
            continue
        if current:
            url = _URL_LINE.match(line)
            if url:
                hosts[current] = host_of(url.group("url"))
    return hosts


def _classify(message: str) -> str | None:
    msg = message.strip()
    if msg.startswith("update by push"):
        return Category.PUSH
    if msg.startswith(("fetch", "pull", "clone")):
        return Category.PULL
    return None


def _parse_line(header: str) -> tuple[str, int] | None:
    """Return ``(new_sha, epoch)`` from a reflog line's pre-tab header."""

    parts = header.split()
    if len(parts) < 5:
        return None
    try:
        epoch = int(parts[-2])
    except ValueError:
        return None
    return parts[1], epoch


def sync_events(
    repo_path: str | Path,
    repo_name: str,
    *,
    limit: int | None = None,
) -> list[ActivityEvent]:
    """Return push/pull ``SYNC`` events for the repo at ``repo_path``, sorted.

    ``repo_name`` is the scanned repository's display name (used to wire the
    pulse to its repo node). ``limit`` keeps only the most-recent events. A repo
    without a ``.git`` directory (or without remote reflogs) yields none.
    """

    git_dir = Path(repo_path).expanduser() / ".git"
    if not git_dir.is_dir():
        return []
    remotes_dir = git_dir / "logs" / "refs" / "remotes"
    if not remotes_dir.is_dir():
        return []

    hosts = _remote_hosts(git_dir)
    events: list[ActivityEvent] = []
    for log_file in sorted(remotes_dir.rglob("*")):
        if not log_file.is_file():
            continue
        rel = log_file.relative_to(remotes_dir).parts
        remote = rel[0] if rel else "origin"
        branch = "/".join(rel[1:]) or remote
        host = hosts.get(remote, "")
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines()):
            if "\t" not in line:
                continue
            head, _, message = line.partition("\t")
            category = _classify(message)
            if category is None:
                continue
            parsed = _parse_line(head)
            if parsed is None:
                continue
            new_sha, epoch = parsed
            arrow = "→" if category == Category.PUSH else "←"
            where = host or remote
            events.append(
                ActivityEvent(
                    event=EventKind.SYNC,
                    t=epoch,
                    uid=f"{'/'.join(rel)}:{lineno}:{new_sha}",
                    actor_kind=NodeKind.SERVER,
                    actor_key=_SERVER_KEY,
                    actor_label=_SERVER_LABEL,
                    category=category,
                    title=f"{category} {arrow} {where}",
                    detail=f"{branch} · {new_sha[:7]}",
                    repo=repo_name,
                    intensity=0.5 if category == Category.PUSH else 0.4,
                )
            )

    events.sort(key=lambda e: (e.t, e.uid))
    if limit is not None and limit >= 0:
        events = events[-limit:]
    return events
