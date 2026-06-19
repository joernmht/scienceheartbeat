"""Deterministic git history extraction.

We shell out to ``git`` (no third-party dependency) and parse a machine-stable
``git log --numstat`` stream. Author/committer *epoch* timestamps are read with
``%at``/``%ct`` so there is no timezone parsing and no locale dependence — the
extracted :class:`Commit` data is a pure function of the repository state.

The parser uses ASCII record/field separators (``\\x1e``/``\\x1f``) inside the
pretty format so commit subjects cannot break the framing. Filenames
containing newlines are not supported (documented limitation).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from scienceheartbeat.classify.change_kind import classify_path
from scienceheartbeat.core.model import ChangeKind

__all__ = [
    "Commit",
    "FileChange",
    "ScanError",
    "ScannedRepo",
    "scan_repo",
]

_RS = "\x1e"  # record separator: marks the start of a commit header
_US = "\x1f"  # unit separator: separates header fields

_PRETTY = _RS + _US.join(["%H", "%an", "%ae", "%cn", "%ce", "%at", "%ct", "%s"])


class ScanError(RuntimeError):
    """Raised when git is unavailable or a path is not a usable repository."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FileChange(_Frozen):
    """One file touched by a commit, with its insertion/deletion counts."""

    path: str
    insertions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    kind: ChangeKind


class Commit(_Frozen):
    """A single commit's deterministic metadata and file changes."""

    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    author_time: int
    commit_time: int
    subject: str
    files: list[FileChange]

    @property
    def insertions(self) -> int:
        return sum(f.insertions for f in self.files)

    @property
    def deletions(self) -> int:
        return sum(f.deletions for f in self.files)


class ScannedRepo(_Frozen):
    """A repository scanned at its current ``HEAD`` on a single branch."""

    name: str
    path: str
    branch: str
    head: str
    commits: list[Commit]


def _require_git() -> str:
    git = shutil.which("git")
    if git is None:
        raise ScanError("git executable not found on PATH")
    return git


def _git(repo_path: Path, *args: str) -> str:
    git = _require_git()
    result = subprocess.run(
        [git, "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise ScanError(f"git {' '.join(args)} failed in {repo_path}: {result.stderr.strip()}")
    return result.stdout


def _git_ok(repo_path: Path, *args: str) -> bool:
    try:
        _git(repo_path, *args)
        return True
    except ScanError:
        return False


def _resolve_rename(path: str) -> str:
    """Resolve a numstat rename spec to the new path.

    Handles ``old => new`` and the ``dir/{old => new}/file`` brace form.
    """

    if "{" in path and "=>" in path:
        before, _, rest = path.partition("{")
        inner, _, after = rest.partition("}")
        _, _, new = inner.partition("=>")
        return f"{before}{new.strip()}{after}".replace("//", "/")
    if "=>" in path:
        return path.split("=>", 1)[1].strip()
    return path


def _parse_numstat(line: str) -> FileChange | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    raw_ins, raw_del, raw_path = parts[0], parts[1], "\t".join(parts[2:])
    path = _resolve_rename(raw_path.strip())
    insertions = 0 if raw_ins.strip() in {"-", ""} else int(raw_ins)
    deletions = 0 if raw_del.strip() in {"-", ""} else int(raw_del)
    return FileChange(
        path=path,
        insertions=insertions,
        deletions=deletions,
        kind=classify_path(path),
    )


def _parse_commit_chunk(chunk: str) -> Commit | None:
    lines = chunk.split("\n")
    header = lines[0]
    fields = header.split(_US)
    if len(fields) != 8:
        return None
    sha, an, ae, cn, ce, at, ct, subject = fields
    files: list[FileChange] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        change = _parse_numstat(line)
        if change is not None:
            files.append(change)
    return Commit(
        sha=sha,
        author_name=an,
        author_email=ae,
        committer_name=cn,
        committer_email=ce,
        author_time=int(at),
        commit_time=int(ct),
        subject=subject,
        files=files,
    )


def scan_repo(
    path: str | Path,
    *,
    name: str | None = None,
    branch: str | None = None,
    limit: int | None = None,
    include_merges: bool = False,
) -> ScannedRepo:
    """Scan a git repository at ``path`` into a :class:`ScannedRepo`.

    ``name`` defaults to the repository's top-level directory name and
    ``branch`` to the currently checked-out branch. ``limit`` caps the number
    of most-recent commits read; ``include_merges`` keeps merge commits
    (excluded by default because they rarely carry standalone file changes).
    """

    repo_path = Path(path).expanduser()
    if not repo_path.exists():
        raise ScanError(f"path does not exist: {repo_path}")
    if not _git_ok(repo_path, "rev-parse", "--is-inside-work-tree"):
        raise ScanError(f"not a git repository: {repo_path}")

    root = Path(_git(repo_path, "rev-parse", "--show-toplevel").strip())
    repo_name = name or root.name

    # An empty repository (no commits) yields no pulses but is not an error.
    if not _git_ok(repo_path, "rev-parse", "--verify", "HEAD"):
        resolved_branch = branch or "main"
        return ScannedRepo(
            name=repo_name, path=str(root), branch=resolved_branch, head="", commits=[]
        )

    head = _git(repo_path, "rev-parse", "HEAD").strip()
    if branch is None:
        ref = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD").strip()
        branch = head[:12] if ref == "HEAD" else ref

    args = ["log"]
    if limit is not None:
        args += ["-n", str(limit)]
    if not include_merges:
        args.append("--no-merges")
    args += [f"--pretty=format:{_PRETTY}", "--numstat"]

    output = _git(repo_path, *args)
    commits: list[Commit] = []
    for chunk in output.split(_RS):
        if not chunk.strip():
            continue
        commit = _parse_commit_chunk(chunk)
        if commit is not None:
            commits.append(commit)

    return ScannedRepo(name=repo_name, path=str(root), branch=branch, head=head, commits=commits)
