"""Generate the committed demo dashboard from synthetic, deterministic data.

This fabricates a couple of repositories' worth of commits (seeded RNG, so the
output is reproducible and free of machine-specific paths) and renders them
through the real pipeline. Run it from the repository root::

    python examples/generate_demo.py

It writes ``examples/demo/heartbeat.json`` and ``examples/demo/index.html``.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

from scienceheartbeat.activity.model import ActivityEvent, Category
from scienceheartbeat.classify.change_kind import classify_path
from scienceheartbeat.core.model import EventKind, NodeKind
from scienceheartbeat.export.document import build_document
from scienceheartbeat.export.html import render_html
from scienceheartbeat.export.json_io import write
from scienceheartbeat.scan.git import Commit, FileChange, ScannedRepo

SEED = 7
DAY = 86_400
START = 1_716_000_000  # fixed epoch so the demo never drifts

AUTHORS = [
    ("Ada Lovelace", "ada@example.com"),
    ("Bob Bits", "bob@example.com"),
    ("Carol Compiler", "carol@example.com"),
]

# (path template, typical insertions, weight)
FILE_MENU = [
    ("src/engine/{}.py", 80, 5),
    ("src/api/{}.py", 60, 4),
    ("tests/test_{}.py", 40, 4),
    ("docs/{}.md", 25, 3),
    ("README.md", 12, 1),
    ("pyproject.toml", 6, 1),
    (".github/workflows/{}.yml", 18, 1),
    ("assets/{}.svg", 4, 1),
    ("data/{}.csv", 200, 1),
]

SUBJECTS = [
    "feat: {}",
    "fix: handle {} edge case",
    "refactor: simplify {}",
    "test: cover {}",
    "docs: explain {}",
    "chore: bump {}",
]
TOPICS = ["scheduler", "parser", "cache", "auth", "graph", "loader", "metrics", "export"]


def _sha(repo: str, n: int) -> str:
    return hashlib.sha1(f"{repo}:{n}:{SEED}".encode()).hexdigest()


def _make_commit(rng: random.Random, repo: str, n: int, ts: int) -> Commit:
    author, email = rng.choice(AUTHORS)
    topic = rng.choice(TOPICS)
    count = rng.randint(1, 4)
    files: list[FileChange] = []
    for _ in range(count):
        template, base, _weight = rng.choices(FILE_MENU, weights=[m[2] for m in FILE_MENU], k=1)[0]
        path = template.format(rng.choice(TOPICS)) if "{}" in template else template
        ins = max(1, int(rng.gauss(base, base * 0.4)))
        dels = max(0, int(rng.gauss(base * 0.3, base * 0.2)))
        files.append(
            FileChange(path=path, insertions=ins, deletions=dels, kind=classify_path(path))
        )
    subject = rng.choice(SUBJECTS).format(topic)
    return Commit(
        sha=_sha(repo, n),
        author_name=author,
        author_email=email,
        committer_name=author,
        committer_email=email,
        author_time=ts,
        commit_time=ts,
        subject=subject,
        files=files,
    )


def _make_repo(name: str, branch: str, n_commits: int, seed_offset: int) -> ScannedRepo:
    rng = random.Random(SEED + seed_offset)
    ts = START
    commits: list[Commit] = []
    for i in range(n_commits):
        ts += rng.randint(DAY // 4, DAY * 3)
        commits.append(_make_commit(rng, name, i, ts))
    return ScannedRepo(
        name=name,
        path=f"~/code/{name}",
        branch=branch,
        head=_sha(name, n_commits - 1),
        commits=commits,
    )


# --- synthetic machine activity (all fabricated; nothing from a real machine) -
LOOPS = ["standup", "radio", "quality", "coherence", "directions"]
PROMPTS = [
    "summarise what changed in {} this week",
    "is the {} pipeline still deterministic?",
    "draft release notes for {}",
    "explain the {} module to a newcomer",
    "what is the test coverage of {}?",
]
MESSAGES = [
    "morning briefing please",
    "did the nightly run pass?",
    "push the latest docs",
    "what's the headline today?",
    "any failing checks?",
]


def _make_activity(repo_names: list[str], t0: int, t1: int) -> list[ActivityEvent]:
    """Fabricate a deterministic activity stream spanning ``[t0, t1]``."""

    rng = random.Random(SEED + 99)
    events: list[ActivityEvent] = []
    span = max(1, t1 - t0)

    # Loop runs: a steady cron-like beat, with the occasional failure.
    for li, name in enumerate(LOOPS):
        n = 18 + li * 4
        for i in range(n):
            t = t0 + int((i + 0.5) / n * span) + li * 137
            ok = rng.random() > 0.08
            dur = rng.randint(40, 800)
            events.append(
                ActivityEvent(
                    event=EventKind.LOOP_RUN,
                    t=t,
                    uid=f"loop-{name}-{i}",
                    actor_kind=NodeKind.LOOP,
                    actor_key=name,
                    actor_label=name,
                    category=Category.LOOP_OK if ok else Category.LOOP_FAIL,
                    title=f"{name} loop",
                    detail=f"exit {0 if ok else 1} · {dur}s",
                    intensity=0.55 if ok else 0.85,
                )
            )

    # Repository syncs: pushes (outbound) and the odd pull (inbound).
    for ri, name in enumerate(repo_names):
        for i in range(14):
            t = t0 + int((i + 0.3) / 14 * span) + ri * 53
            push = rng.random() > 0.25
            events.append(
                ActivityEvent(
                    event=EventKind.SYNC,
                    t=t,
                    uid=f"sync-{name}-{i}",
                    actor_kind=NodeKind.SERVER,
                    actor_key="server",
                    actor_label="the box",
                    category=Category.PUSH if push else Category.PULL,
                    title=("push → github.com" if push else "pull ← github.com"),
                    detail=f"main · {_sha(name, i)[:7]}",
                    repo=name,
                    intensity=0.5 if push else 0.4,
                )
            )

    # Inbound remote messages on the bot.
    for i in range(22):
        t = t0 + int(rng.random() * span)
        events.append(
            ActivityEvent(
                event=EventKind.MESSAGE,
                t=t,
                uid=f"msg-{i}",
                actor_kind=NodeKind.BOT,
                actor_key="telegram",
                actor_label="telegram bot",
                category=Category.MSG_IN,
                title=rng.choice(MESSAGES),
                detail=rng.choice(["voice·en", "ask·en", "ask·de"]),
                direction="in",
                intensity=0.6,
            )
        )

    # Remote sessions, some of which touch a repo (an access edge).
    for i in range(9):
        t = t0 + int(rng.random() * span)
        repo = rng.choice(repo_names)
        label = f"session #{i + 1}"
        events.append(
            ActivityEvent(
                event=EventKind.SESSION,
                t=t,
                uid=f"sess-{i}",
                actor_kind=NodeKind.AGENT,
                actor_key=f"sess-{i}",
                actor_label=label,
                category=Category.SESSION,
                title=rng.choice(PROMPTS).format(repo),
                detail=rng.choice(["question·en", "change·en"]),
                intensity=0.7,
            )
        )
        if rng.random() > 0.4:
            events.append(
                ActivityEvent(
                    event=EventKind.ACCESS,
                    t=t,
                    uid=f"sess-{i}:{repo}",
                    actor_kind=NodeKind.AGENT,
                    actor_key=f"sess-{i}",
                    actor_label=label,
                    category=Category.ACCESS,
                    title=f"{label} touched {repo}",
                    detail="change",
                    repo=repo,
                    intensity=0.5,
                )
            )

    events.sort(key=lambda e: (e.t, e.event, e.uid))
    return events


def main() -> None:
    repos = [
        _make_repo("aurora", "main", 38, 1),
        _make_repo("borealis", "develop", 26, 2),
    ]
    times = [c.author_time for r in repos for c in r.commits]
    events = _make_activity([r.name for r in repos], min(times), max(times))
    document = build_document(repos, events, owner_email="ada@example.com")

    out = Path(__file__).resolve().parent / "demo"
    out.mkdir(parents=True, exist_ok=True)
    write(document, out / "heartbeat.json")
    (out / "index.html").write_text(render_html(document), encoding="utf-8")
    print(
        f"wrote {out}/ — {len(document.pulses)} pulses "
        f"({len(events)} activity events) across {len(document.sources)} repos"
    )


if __name__ == "__main__":
    main()
