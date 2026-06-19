from __future__ import annotations

import pytest

from scienceheartbeat.classify import PALETTE, classify_commit, classify_path, primary_kind
from scienceheartbeat.core.model import ChangeKind


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/app.py", ChangeKind.CODE),
        ("lib/widget.tsx", ChangeKind.CODE),
        ("tests/test_app.py", ChangeKind.TESTS),
        ("pkg/foo_test.go", ChangeKind.TESTS),
        ("frontend/Button.spec.ts", ChangeKind.TESTS),
        ("README.md", ChangeKind.DOCS),
        ("docs/guide.rst", ChangeKind.DOCS),
        (".github/workflows/ci.yml", ChangeKind.BUILD),
        ("Dockerfile", ChangeKind.BUILD),
        ("Makefile", ChangeKind.BUILD),
        ("poetry.lock", ChangeKind.DEPS),
        ("package-lock.json", ChangeKind.DEPS),
        ("pyproject.toml", ChangeKind.CONFIG),
        ("config/settings.yaml", ChangeKind.CONFIG),
        (".gitignore", ChangeKind.CONFIG),
        ("data/results.csv", ChangeKind.DATA),
        ("assets/logo.png", ChangeKind.ASSETS),
        ("weird.unknownext", ChangeKind.OTHER),
        ("LICENSE", ChangeKind.OTHER),
    ],
)
def test_classify_path(path: str, expected: ChangeKind) -> None:
    assert classify_path(path) == expected


def test_palette_covers_every_kind() -> None:
    assert set(PALETTE) == set(ChangeKind)
    for color in PALETTE.values():
        assert color.startswith("#") and len(color) == 7


def test_primary_kind_tie_breaks_by_declaration_order() -> None:
    # code and docs tie at 1 file each; code is declared first, so it wins.
    primary, breakdown = classify_commit(["src/app.py", "README.md"])
    assert primary == ChangeKind.CODE
    assert {kc.kind for kc in breakdown} == {ChangeKind.CODE, ChangeKind.DOCS}


def test_primary_kind_empty() -> None:
    assert primary_kind({}) == ChangeKind.OTHER


def test_classify_commit_counts() -> None:
    primary, breakdown = classify_commit(["a.py", "b.py", "c.py", "README.md"])
    assert primary == ChangeKind.CODE
    counts = {kc.kind: kc.files for kc in breakdown}
    assert counts[ChangeKind.CODE] == 3
    assert counts[ChangeKind.DOCS] == 1
