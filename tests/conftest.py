"""Shared fixtures: a deterministic in-memory git repository.

Commits are made with pinned author/committer identities and pinned
author/committer dates, so the repository — and therefore everything derived
from it — is reproducible across runs and machines.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


def _run(args: list[str], cwd: Path, env: Mapping[str, str] | None = None) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=dict(env) if env is not None else None,
    )


def _commit(
    repo: Path,
    files: dict[str, str],
    *,
    name: str,
    email: str,
    ts: int,
    msg: str,
) -> None:
    for rel, content in files.items():
        full = repo / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        _run(["add", rel], repo)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": f"{ts} +0000",
        "GIT_COMMITTER_DATE": f"{ts} +0000",
    }
    _run(["commit", "-m", msg, "--no-gpg-sign"], repo, env)


def _lines(n: int, prefix: str = "x") -> str:
    return "\n".join(f"{prefix}{i}" for i in range(n)) + "\n"


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """A small repo with two committers across several change kinds."""

    repo = tmp_path / "sample"
    repo.mkdir()
    _run(["init", "-q"], repo)

    _commit(
        repo,
        {"src/app.py": _lines(20, "code"), "README.md": _lines(5, "doc")},
        name="Ada Lovelace",
        email="ada@example.com",
        ts=1_700_000_000,
        msg="feat: initial app and readme",
    )
    _commit(
        repo,
        {"tests/test_app.py": _lines(10, "test")},
        name="Ada Lovelace",
        email="ada@example.com",
        ts=1_700_050_000,
        msg="test: add app tests",
    )
    _commit(
        repo,
        {"src/app.py": _lines(120, "code"), "docs/guide.md": _lines(8, "doc")},
        name="Bob Bits",
        email="bob@example.com",
        ts=1_700_100_000,
        msg="feat: grow app and document it",
    )
    _run(["branch", "-M", "main"], repo)
    return repo


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """An initialised repo with no commits."""

    repo = tmp_path / "empty"
    repo.mkdir()
    _run(["init", "-q"], repo)
    return repo
