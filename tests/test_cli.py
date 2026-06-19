from __future__ import annotations

import json
from pathlib import Path

import pytest

from scienceheartbeat.cli import main
from scienceheartbeat.dashboard.serve import write_dashboard
from scienceheartbeat.export import build_document
from scienceheartbeat.scan import scan_repo


def test_cli_build_writes_artifacts(sample_repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "dash"
    rc = main(["build", str(sample_repo), "--out", str(out)])
    assert rc == 0
    assert (out / "index.html").exists()
    assert (out / "heartbeat.json").exists()
    data = json.loads((out / "heartbeat.json").read_text(encoding="utf-8"))
    assert len(data["pulses"]) == 3


def test_cli_scan_prints_json(sample_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["scan", str(sample_repo)])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["content_hash"]


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["version"])
    assert rc == 0
    assert "scienceheartbeat" in capsys.readouterr().out


def test_write_dashboard_json_only(sample_repo: Path, tmp_path: Path) -> None:
    doc = build_document([scan_repo(sample_repo)])
    out = write_dashboard(doc, tmp_path / "d", html=False, json=True)
    assert (out / "heartbeat.json").exists()
    assert not (out / "index.html").exists()
