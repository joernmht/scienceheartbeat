"""Write and serve the dashboard.

The dashboard is a single self-contained HTML file, so serving is only a
convenience for opening it in a browser. We also write ``heartbeat.json``
alongside it so the underlying data is easy to inspect or reuse.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import socketserver
import webbrowser
from pathlib import Path

from scienceheartbeat.core.model import HeartbeatDocument
from scienceheartbeat.export.html import render_html
from scienceheartbeat.export.json_io import write as write_json

__all__ = ["serve", "write_dashboard"]


def write_dashboard(
    document: HeartbeatDocument,
    out_dir: str | Path,
    *,
    html: bool = True,
    json: bool = True,
) -> Path:
    """Write ``index.html`` and/or ``heartbeat.json`` into ``out_dir``.

    Returns the directory. Both artifacts are deterministic.
    """

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if html:
        (out / "index.html").write_text(render_html(document), encoding="utf-8")
    if json:
        write_json(document, out / "heartbeat.json")
    return out


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        """Silence the per-request access log."""


def serve(
    document: HeartbeatDocument,
    out_dir: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Build the dashboard into ``out_dir`` and serve it until interrupted."""

    out = write_dashboard(document, out_dir)
    handler = functools.partial(_QuietHandler, directory=str(out))
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((host, port), handler) as httpd:
        url = f"http://{host}:{port}/index.html"
        print(f"science heartbeat serving {out} at {url}")
        print("Press Ctrl+C to stop.")
        if open_browser:
            with contextlib.suppress(Exception):  # pragma: no cover - headless
                webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - interactive
            print("\nstopped.")
