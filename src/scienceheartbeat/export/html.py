"""Render a self-contained dashboard HTML page for a heartbeat document.

The page inlines the stylesheet, the engine script and the document JSON, so it
can be opened directly from disk (``file://``) with no server and no network.
Rendering is deterministic: byte-identical for identical inputs.
"""

from __future__ import annotations

import importlib.resources as resources

from scienceheartbeat.core.model import HeartbeatDocument
from scienceheartbeat.export.json_io import compact

__all__ = ["render_html"]

_PACKAGE = "scienceheartbeat.dashboard"


def _asset(name: str) -> str:
    return resources.files(_PACKAGE).joinpath("assets", name).read_text(encoding="utf-8")


def render_html(document: HeartbeatDocument) -> str:
    """Return a self-contained HTML page visualising ``document``."""

    template = _asset("index.html")
    style = _asset("style.css")
    app = _asset("app.js")

    # Escape ``</`` inside the embedded JSON so a commit subject containing
    # ``</script>`` cannot terminate the script element. ``<\/`` round-trips
    # through JSON.parse to the original text.
    data = compact(document).replace("</", "<\\/")

    html = template.replace("/*__STYLE__*/", style)
    html = html.replace("/*__APP__*/", app)
    html = html.replace("__HEARTBEAT_DATA__", data)
    return html
