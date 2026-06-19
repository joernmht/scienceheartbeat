from __future__ import annotations

from pathlib import Path

import pytest

from scienceheartbeat.activity.model import ActivityEvent
from scienceheartbeat.export import build_document
from scienceheartbeat.export.json_io import to_jsonable
from scienceheartbeat.scan import scan_repo

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "heartbeat.schema.json"


def test_document_validates_against_schema(sample_repo: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    import json

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document = to_jsonable(build_document([scan_repo(sample_repo)]))
    jsonschema.validate(instance=document, schema=schema)


def test_empty_document_validates(empty_repo: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    import json

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document = to_jsonable(build_document([scan_repo(empty_repo)]))
    jsonschema.validate(instance=document, schema=schema)


def test_activity_document_validates(sample_repo: Path, sample_events: list[ActivityEvent]) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    import json

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    document = to_jsonable(build_document([scan_repo(sample_repo)], sample_events))
    jsonschema.validate(instance=document, schema=schema)
