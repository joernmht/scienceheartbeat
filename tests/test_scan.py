from __future__ import annotations

from pathlib import Path

import pytest

from scienceheartbeat.core.model import ChangeKind
from scienceheartbeat.scan import ScanError, discover_repos, scan_repo


def test_scan_sample_repo(sample_repo: Path) -> None:
    scanned = scan_repo(sample_repo)
    assert scanned.name == "sample"
    assert scanned.branch == "main"
    assert scanned.head  # non-empty sha
    assert len(scanned.commits) == 3

    # Commits come back newest-first from git log.
    subjects = [c.subject for c in scanned.commits]
    assert subjects[0] == "feat: grow app and document it"
    assert subjects[-1] == "feat: initial app and readme"

    authors = {c.author_email for c in scanned.commits}
    assert authors == {"ada@example.com", "bob@example.com"}

    # The deterministic author timestamps survive the round trip.
    times = sorted(c.author_time for c in scanned.commits)
    assert times == [1_700_000_000, 1_700_050_000, 1_700_100_000]


def test_scan_classifies_files(sample_repo: Path) -> None:
    scanned = scan_repo(sample_repo)
    by_subject = {c.subject: c for c in scanned.commits}
    test_commit = by_subject["test: add app tests"]
    assert [f.kind for f in test_commit.files] == [ChangeKind.TESTS]
    assert test_commit.insertions == 10


def test_scan_limit(sample_repo: Path) -> None:
    assert len(scan_repo(sample_repo, limit=1).commits) == 1


def test_scan_empty_repo(empty_repo: Path) -> None:
    scanned = scan_repo(empty_repo)
    assert scanned.commits == []
    assert scanned.head == ""


def test_scan_non_repo(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ScanError):
        scan_repo(plain)


def test_discover_single_and_nested(sample_repo: Path, tmp_path: Path) -> None:
    assert discover_repos(sample_repo) == [sample_repo.resolve()]
    # Parent folder discovery finds the repo beneath it.
    found = discover_repos(tmp_path)
    assert sample_repo.resolve() in found
