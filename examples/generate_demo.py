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

from scienceheartbeat.classify.change_kind import classify_path
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


def main() -> None:
    repos = [
        _make_repo("aurora", "main", 38, 1),
        _make_repo("borealis", "develop", 26, 2),
    ]
    document = build_document(repos)

    out = Path(__file__).resolve().parent / "demo"
    out.mkdir(parents=True, exist_ok=True)
    write(document, out / "heartbeat.json")
    (out / "index.html").write_text(render_html(document), encoding="utf-8")
    print(f"wrote {out}/ — {len(document.pulses)} pulses across {len(document.sources)} repos")


if __name__ == "__main__":
    main()
