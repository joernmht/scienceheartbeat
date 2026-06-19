from __future__ import annotations

from pathlib import Path

from scienceheartbeat.export import build_document, dumps, render_html
from scienceheartbeat.export.json_io import content_hash
from scienceheartbeat.scan import scan_repo


def _doc(repo: Path):
    return build_document([scan_repo(repo)])


def test_document_json_is_byte_identical(sample_repo: Path) -> None:
    a = dumps(_doc(sample_repo))
    b = dumps(_doc(sample_repo))
    assert a == b


def test_content_hash_matches_and_verifies(sample_repo: Path) -> None:
    doc = _doc(sample_repo)
    assert doc.content_hash
    # Recomputing the hash over the (hash-excluded) content reproduces it.
    assert content_hash(doc) == doc.content_hash


def test_rendered_html_is_deterministic(sample_repo: Path) -> None:
    assert render_html(_doc(sample_repo)) == render_html(_doc(sample_repo))


def test_keys_are_sorted(sample_repo: Path) -> None:
    text = dumps(_doc(sample_repo))
    # Top-level keys appear in sorted order in the serialised form.
    assert text.index('"classifier_version"') < text.index('"schema_version"')
