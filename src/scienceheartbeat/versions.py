"""Versioned, frozen resources stamped into every emitted document.

Bumping one of these constants signals that a derived artifact may change even
though the input repository history did not. Stamping them into the
:class:`~scienceheartbeat.core.model.HeartbeatDocument` keeps old artifacts
self-describing and reproducible.
"""

from __future__ import annotations

__all__ = [
    "CLASSIFIER_VERSION",
    "LAYOUT_VERSION",
    "PACKAGE_VERSION",
    "PALETTE_VERSION",
    "SCHEMA_VERSION",
]

#: Distribution version (kept in sync with ``pyproject.toml``).
PACKAGE_VERSION = "0.1.0"

#: Version of ``schema/heartbeat.schema.json`` and the document shape.
SCHEMA_VERSION = "1"

#: Version of the change-kind → colour palette.
PALETTE_VERSION = "1"

#: Version of the path → change-kind classification rules.
CLASSIFIER_VERSION = "1"

#: Version of the deterministic graph-layout algorithm.
LAYOUT_VERSION = "1"
