from __future__ import annotations

import json
import re
from pathlib import Path

from scienceheartbeat.export import build_document, render_html
from scienceheartbeat.scan import scan_repo


def test_html_is_self_contained(sample_repo: Path) -> None:
    html = render_html(build_document([scan_repo(sample_repo)]))

    # No template markers survive rendering.
    assert "__HEARTBEAT_DATA__" not in html
    assert "/*__STYLE__*/" not in html
    assert "/*__APP__*/" not in html

    # Inlined assets and data are present.
    assert '<canvas id="stage">' in html
    assert "mulberry32" in html  # the engine script
    assert "hb-data" in html


def test_embedded_json_round_trips(sample_repo: Path) -> None:
    html = render_html(build_document([scan_repo(sample_repo)]))
    match = re.search(
        r'<script id="hb-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match is not None
    # Undo the </ escaping applied during embedding, then parse.
    payload = match.group(1).replace("<\\/", "</")
    data = json.loads(payload)
    assert data["schema_version"]
    assert len(data["pulses"]) == 3
