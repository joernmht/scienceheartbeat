from __future__ import annotations

import json
from pathlib import Path

from scienceheartbeat.activity.collect import collect_activity
from scienceheartbeat.activity.loops import loop_events
from scienceheartbeat.activity.redact import host_of, preview, redact
from scienceheartbeat.activity.sessions import session_events
from scienceheartbeat.activity.syncs import sync_events
from scienceheartbeat.activity.telegram import telegram_events
from scienceheartbeat.core.model import EventKind, NodeKind
from scienceheartbeat.scan.git import ScannedRepo

# --- redaction (security-critical) ----------------------------------------


def test_redact_masks_tokens_and_credentials() -> None:
    assert "olp_" not in redact("token olp_2cSQXfDrEZxwJpPj6AaY4zLFZqUbml45Xfoy here")
    assert "ghp_" not in redact("ghp_ABCDEFG1234567890abcdefg leaked")
    assert redact("clone https://git:olp_secret@tex.example.de/x") == (
        "clone https://tex.example.de/x"
    )
    assert "@" not in redact("mail me at someone@example.com")


def test_preview_truncates() -> None:
    long = "word " * 50
    out = preview(long, limit=20)
    assert len(out) <= 20
    assert out.endswith("…")


def test_host_of_strips_token() -> None:
    assert host_of("https://git:olp_tok@tex.zih.tu-dresden.de/git/abc") == "tex.zih.tu-dresden.de"
    assert host_of("git@github.com:joernmht/lp2graph.git") == "github.com"
    assert host_of("not a url") == ""


# --- loop runs -------------------------------------------------------------


def _write_log(logs: Path, name: str, body: str) -> None:
    (logs / name).write_text(body, encoding="utf-8")


def test_loop_events_parse_status_and_duration(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    _write_log(
        logs,
        "01-standup-2026-06-19T09-00-01.log",
        "=== loop:01-standup start:2026-06-19T09:00:01+00:00 ===\n"
        "secret body line that must never be embedded\n"
        "=== loop:01-standup end:2026-06-19T09:02:05+00:00 rc:0 ===\n",
    )
    _write_log(
        logs,
        "02-quality-2026-06-19T02-00-01.log",
        "=== loop:02-quality start:2026-06-19T02:00:01+00:00 ===\n"
        "=== loop:02-quality end:2026-06-19T02:01:01+00:00 rc:1 ===\n",
    )
    events = loop_events(logs)
    assert [e.t for e in events] == sorted(e.t for e in events)
    by_label = {e.actor_label: e for e in events}
    assert by_label["standup"].category == "loop-ok"
    assert by_label["standup"].detail == "exit 0 · 124s"
    assert by_label["quality"].category == "loop-fail"
    # The run body is never carried into the event.
    assert all("secret body" not in e.title and "secret body" not in e.detail for e in events)


def test_loop_events_missing_dir(tmp_path: Path) -> None:
    assert loop_events(tmp_path / "nope") == []


# --- telegram --------------------------------------------------------------


def test_telegram_events_inbound_only_and_redacted(tmp_path: Path) -> None:
    audit = tmp_path / "tg_audit.log"
    audit.write_text(
        "2026-06-19T08:50:25 VOICE[de]: Was ist die letzte Änderung?\n"
        "2026-06-19T06:34:01 ASK[en] #11: token olp_2cSQXfDrEZxwJpPj6AaY4zLFZ leaked\n"
        "2026-06-19T01:03:51 poll err The read operation timed out\n"
        "2026-06-19T07:00:00 START (no PIN set yet)\n"
        "2026-06-19T07:10:00 UNLOCK ok\n",
        encoding="utf-8",
    )
    events = telegram_events(audit)
    # poll / START dropped; ASK + VOICE + UNLOCK kept.
    assert len(events) == 3
    assert all(e.event == EventKind.MESSAGE and e.direction == "in" for e in events)
    assert all(e.actor_kind == NodeKind.BOT for e in events)
    assert all("olp_" not in e.title for e in events)
    assert any(e.title == "/unlock" for e in events)


# --- sessions --------------------------------------------------------------


def test_session_events_and_access_detection(tmp_path: Path) -> None:
    store = tmp_path / ".sessions.json"
    store.write_text(
        json.dumps(
            {
                "sessions": {
                    "1": {
                        "id": "1",
                        "sid": "aaa",
                        "kind": "question",
                        "lang": "en",
                        "prompt": "what is aurora about?",
                        "ts": 1_700_000_000,
                    },
                    "2": {
                        "id": "2",
                        "sid": "bbb",
                        "kind": "change",
                        "lang": "de",
                        "prompt": "no repo mention here",
                        "ts": 1_700_100_000,
                    },
                },
                "counter": 2,
            }
        ),
        encoding="utf-8",
    )
    events = session_events(store, repo_names=["aurora", "borealis"])
    sessions = [e for e in events if e.event == EventKind.SESSION]
    accesses = [e for e in events if e.event == EventKind.ACCESS]
    assert len(sessions) == 2
    assert len(accesses) == 1
    assert accesses[0].repo == "aurora"
    assert accesses[0].actor_kind == NodeKind.AGENT


def test_session_events_malformed(tmp_path: Path) -> None:
    bad = tmp_path / ".sessions.json"
    bad.write_text("not json", encoding="utf-8")
    assert session_events(bad) == []


# --- syncs (fabricated .git reflog, no git binary needed) ------------------


def _fake_repo(tmp_path: Path, host_url: str) -> Path:
    repo = tmp_path / "repo"
    remotes = repo / ".git" / "logs" / "refs" / "remotes" / "origin"
    remotes.mkdir(parents=True)
    (repo / ".git" / "config").write_text(
        f'[remote "origin"]\n\turl = {host_url}\n', encoding="utf-8"
    )
    (remotes / "main").write_text(
        "0000000000000000000000000000000000000000 "
        "abc1234000000000000000000000000000000000 "
        "Dev <dev@example.com> 1700000000 +0000\tupdate by push\n"
        "abc1234000000000000000000000000000000000 "
        "def5678000000000000000000000000000000000 "
        "Dev <dev@example.com> 1700100000 +0000\tfetch origin main: fast-forward\n",
        encoding="utf-8",
    )
    return repo


def test_sync_events_classify_and_hide_token(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path, "https://git:olp_secrettoken@tex.example.de/git/x")
    events = sync_events(repo, "x")
    assert [e.category for e in events] == ["push", "pull"]
    assert all(e.event == EventKind.SYNC and e.repo == "x" for e in events)
    # Host is surfaced but the token never is.
    assert any("tex.example.de" in e.title for e in events)
    assert all("olp_" not in e.title and "olp_" not in e.detail for e in events)


def test_sync_events_limit(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path, "git@github.com:me/x.git")
    assert len(sync_events(repo, "x", limit=1)) == 1


def test_sync_events_no_git(tmp_path: Path) -> None:
    assert sync_events(tmp_path, "x") == []


# --- collect (integration) -------------------------------------------------


def test_collect_activity_merges_sources(tmp_path: Path) -> None:
    loops = tmp_path / "loops"
    (loops / "logs").mkdir(parents=True)
    _write_log(
        loops / "logs",
        "01-standup-2026-06-19T09-00-01.log",
        "=== loop:01-standup start:2026-06-19T09:00:01+00:00 ===\n"
        "=== loop:01-standup end:2026-06-19T09:02:05+00:00 rc:0 ===\n",
    )
    (loops / "tg_audit.log").write_text("2026-06-19T08:50:25 ASK: hi\n", encoding="utf-8")
    (loops / ".sessions.json").write_text(
        json.dumps(
            {
                "sessions": {
                    "1": {
                        "id": "1",
                        "sid": "a",
                        "kind": "q",
                        "lang": "en",
                        "prompt": "x",
                        "ts": 1_700_000_000,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    repo = _fake_repo(tmp_path, "git@github.com:me/x.git")
    scanned = ScannedRepo(name="x", path=str(repo), branch="main", head="def5678", commits=[])

    events = collect_activity([scanned], loops_dir=loops)
    kinds = {e.event for e in events}
    assert EventKind.LOOP_RUN in kinds
    assert EventKind.MESSAGE in kinds
    assert EventKind.SESSION in kinds
    assert EventKind.SYNC in kinds
    # Deterministic ordering.
    assert events == sorted(events, key=lambda e: (e.t, e.event, e.uid))
