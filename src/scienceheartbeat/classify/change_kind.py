"""Deterministic classification of changed files into a :class:`ChangeKind`.

A single file path maps to exactly one kind via a fixed, ordered sequence of
rules, so the result never depends on dict or set iteration order. A commit
touches many files; :func:`classify_commit` tallies the per-kind file counts
and picks a *primary* kind (most files, ties broken by the declaration order
of :class:`ChangeKind`).

The palette assigns each kind a hex colour chosen to read well as a soft glow
on the dashboard's dark background. The palette is versioned in
:mod:`scienceheartbeat.versions`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from scienceheartbeat.core.model import ChangeKind, KindCount

__all__ = [
    "PALETTE",
    "classify_commit",
    "classify_path",
    "classify_paths",
    "primary_kind",
]

#: Change-kind → hex colour. Versioned by ``PALETTE_VERSION``.
PALETTE: dict[ChangeKind, str] = {
    ChangeKind.CODE: "#4fd1ff",
    ChangeKind.TESTS: "#7cffb2",
    ChangeKind.DOCS: "#ffd166",
    ChangeKind.BUILD: "#ff8fa3",
    ChangeKind.DEPS: "#f78c6c",
    ChangeKind.CONFIG: "#c792ea",
    ChangeKind.DATA: "#82aaff",
    ChangeKind.ASSETS: "#c3e88d",
    ChangeKind.OTHER: "#9fb0c0",
}

# --- rule tables (all comparisons are lower-cased) ------------------------

_CODE_EXT = {
    ".py",
    ".pyi",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".cxx",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".lua",
    ".r",
    ".jl",
    ".m",
    ".mm",
    ".sql",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".htm",
    ".vue",
    ".svelte",
    ".dart",
    ".ex",
    ".exs",
    ".clj",
    ".pl",
    ".pm",
    ".hs",
    ".ml",
    ".fs",
    ".elm",
    ".nim",
    ".zig",
}
_DOCS_EXT = {".md", ".markdown", ".rst", ".adoc", ".asciidoc", ".txt", ".tex"}
_DATA_EXT = {
    ".csv",
    ".tsv",
    ".parquet",
    ".npy",
    ".npz",
    ".pkl",
    ".pickle",
    ".h5",
    ".hdf5",
    ".xlsx",
    ".xls",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".feather",
    ".arrow",
}
_ASSET_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".bmp",
    ".tiff",
    ".mp4",
    ".mov",
    ".webm",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".pdf",
}
_CONFIG_EXT = {
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".jsonc",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".env",
    ".editorconfig",
    ".tfvars",
    ".tf",
}

_DOCS_NAMES = {"readme", "changelog", "contributing", "code_of_conduct", "authors", "notice"}
_BUILD_NAMES = {
    "dockerfile",
    "makefile",
    "rakefile",
    "justfile",
    "procfile",
    "containerfile",
    ".dockerignore",
    ".gitlab-ci.yml",
    "tox.ini",
    "noxfile.py",
    "build.gradle",
    "pom.xml",
    "cmakelists.txt",
    ".pre-commit-config.yaml",
}
_DEPS_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.sum",
    "go.mod",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
    "uv.lock",
    "pdm.lock",
}


def _is_test(p: PurePosixPath, name: str, stem: str) -> bool:
    parts = {seg.lower() for seg in p.parts}
    if parts & {"tests", "test", "__tests__", "spec", "specs"}:
        return True
    if stem.startswith("test_") or stem.endswith("_test"):
        return True
    return ".test." in name or ".spec." in name  # foo.test.ts, foo.spec.js


def classify_path(path: str) -> ChangeKind:
    """Classify a single repository-relative path into a :class:`ChangeKind`.

    Rules are applied in a fixed precedence so the mapping is deterministic.
    """

    p = PurePosixPath(path.replace("\\", "/"))
    name = p.name.lower()
    stem = p.stem.lower()
    ext = p.suffix.lower()
    parts_lower = [seg.lower() for seg in p.parts]

    # CI / packaging live under .github/ regardless of extension.
    if ".github" in parts_lower:
        return ChangeKind.BUILD
    if name in _BUILD_NAMES or ext == ".mk":
        return ChangeKind.BUILD
    if name in _DEPS_NAMES:
        return ChangeKind.DEPS

    # Tests take precedence over their underlying language extension.
    if _is_test(p, name, stem):
        return ChangeKind.TESTS

    if "docs" in parts_lower or "doc" in parts_lower or ext in _DOCS_EXT or stem in _DOCS_NAMES:
        return ChangeKind.DOCS
    if ext in _CODE_EXT:
        return ChangeKind.CODE
    if ext in _DATA_EXT:
        return ChangeKind.DATA
    if ext in _ASSET_EXT:
        return ChangeKind.ASSETS
    if ext in _CONFIG_EXT or (ext == "" and name.startswith(".")):
        return ChangeKind.CONFIG
    return ChangeKind.OTHER


def classify_paths(paths: list[str]) -> dict[ChangeKind, int]:
    """Tally how many of ``paths`` fall into each :class:`ChangeKind`."""

    counter: Counter[ChangeKind] = Counter()
    for path in paths:
        counter[classify_path(path)] += 1
    return dict(counter)


def primary_kind(counts: dict[ChangeKind, int]) -> ChangeKind:
    """Pick the dominant kind: most files, ties broken by declaration order."""

    if not counts:
        return ChangeKind.OTHER
    order = {kind: index for index, kind in enumerate(ChangeKind)}
    return max(counts.items(), key=lambda item: (item[1], -order[item[0]]))[0]


def classify_commit(paths: list[str]) -> tuple[ChangeKind, list[KindCount]]:
    """Return the primary kind and the per-kind breakdown for a commit.

    The breakdown is sorted by declaration order of :class:`ChangeKind` so the
    emitted list is deterministic.
    """

    counts = classify_paths(paths)
    primary = primary_kind(counts)
    breakdown = [
        KindCount(kind=kind, files=counts[kind]) for kind in ChangeKind if counts.get(kind, 0) > 0
    ]
    return primary, breakdown
