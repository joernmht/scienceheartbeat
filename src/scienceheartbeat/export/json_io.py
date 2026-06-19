"""Canonical, deterministic JSON serialisation for heartbeat documents.

All output is emitted with sorted keys and a stable separator so the bytes are
reproducible. ``content_hash`` is a SHA-256 over the canonical JSON of every
field *except* the hash itself, which lets a consumer verify integrity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scienceheartbeat.core.model import HeartbeatDocument

__all__ = ["content_hash", "dumps", "loads", "read", "to_jsonable", "write"]


def to_jsonable(document: HeartbeatDocument) -> dict[str, Any]:
    """Return the document as plain JSON-able data (enums as their values)."""

    return document.model_dump(mode="json")


def content_hash(document: HeartbeatDocument) -> str:
    """SHA-256 over the canonical JSON of the document sans ``content_hash``."""

    payload = to_jsonable(document)
    payload.pop("content_hash", None)
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def stamp_hash(document: HeartbeatDocument) -> HeartbeatDocument:
    """Return a copy of ``document`` with its ``content_hash`` populated."""

    return document.model_copy(update={"content_hash": content_hash(document)})


def dumps(document: HeartbeatDocument, *, indent: int | None = 2) -> str:
    """Serialise to canonical JSON text (sorted keys; stable across runs)."""

    return json.dumps(
        to_jsonable(document),
        sort_keys=True,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ": ") if indent is not None else (",", ":"),
    )


def compact(document: HeartbeatDocument) -> str:
    """Serialise to compact canonical JSON (for embedding in HTML)."""

    return dumps(document, indent=None)


def write(document: HeartbeatDocument, path: str | Path) -> Path:
    """Write canonical JSON (with a trailing newline) to ``path``."""

    out = Path(path)
    out.write_text(dumps(document) + "\n", encoding="utf-8")
    return out


def loads(text: str) -> HeartbeatDocument:
    """Parse a heartbeat document from JSON text."""

    return HeartbeatDocument.model_validate(json.loads(text))


def read(path: str | Path) -> HeartbeatDocument:
    """Read a heartbeat document from a JSON file."""

    return loads(Path(path).read_text(encoding="utf-8"))
