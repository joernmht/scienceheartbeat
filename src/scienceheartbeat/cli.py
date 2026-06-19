"""Command-line interface for science heartbeat.

Subcommands
-----------
``build``  scan repositories and write the dashboard (``index.html``) and
           ``heartbeat.json`` to a directory.
``serve``  build into a directory and serve it over HTTP.
``scan``   print the canonical ``heartbeat.json`` to stdout.
``version``  print the package and resource versions.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from scienceheartbeat.activity.collect import DEFAULT_LOOPS_DIR
from scienceheartbeat.core.model import HeartbeatDocument
from scienceheartbeat.export.json_io import dumps
from scienceheartbeat.pipeline import heartbeat_from_paths
from scienceheartbeat.versions import (
    CLASSIFIER_VERSION,
    LAYOUT_VERSION,
    PACKAGE_VERSION,
    PALETTE_VERSION,
    SCHEMA_VERSION,
)

__all__ = ["build_parser", "main"]

#: Default output directory when machine activity is ingested. It is separate
#: from the public default and gitignored, because the artifact is private.
_PRIVATE_OUT = "heartbeat-private"
_PUBLIC_OUT = "heartbeat-dashboard"


def _add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="+", help="Repositories or folders to scan.")
    parser.add_argument(
        "--limit", type=int, default=None, help="Max commits per repo (most recent)."
    )
    parser.add_argument(
        "--merges", action="store_true", help="Include merge commits (excluded by default)."
    )
    parser.add_argument(
        "--max-depth", type=int, default=3, help="How deep to search folders for repos."
    )
    group = parser.add_argument_group("machine activity (PRIVATE — do not publish)")
    group.add_argument(
        "--activity",
        action="store_true",
        help="Also ingest machine activity (syncs, loop runs, messages, sessions).",
    )
    group.add_argument(
        "--loops-dir",
        default=DEFAULT_LOOPS_DIR,
        help="Loops directory for loop/message/session logs (default: %(default)s).",
    )
    group.add_argument(
        "--no-loops",
        action="store_true",
        help="With --activity, ingest repository syncs only (skip the loops dir).",
    )
    group.add_argument(
        "--owner-email", default=None, help="Owner identity that messages travel to/from."
    )
    group.add_argument(
        "--sync-limit", type=int, default=None, help="Max recent syncs kept per repo."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scienceheartbeat",
        description="Deterministic heartbeat dashboard for your repositories.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Write the dashboard and data to a directory.")
    _add_scan_options(p_build)
    p_build.add_argument(
        "--out",
        default=None,
        help=f"Output directory (default: {_PUBLIC_OUT}/, or {_PRIVATE_OUT}/ with --activity).",
    )
    p_build.add_argument("--json-only", action="store_true", help="Write only heartbeat.json.")
    p_build.add_argument("--html-only", action="store_true", help="Write only index.html.")

    p_serve = sub.add_parser("serve", help="Build and serve the dashboard over HTTP.")
    _add_scan_options(p_serve)
    p_serve.add_argument("--out", default=None, help="Output directory.")
    p_serve.add_argument("--host", default="127.0.0.1", help="Bind host.")
    p_serve.add_argument("--port", type=int, default=8765, help="Bind port.")
    p_serve.add_argument("--no-open", action="store_true", help="Do not open a browser.")

    p_scan = sub.add_parser("scan", help="Print canonical heartbeat.json to stdout.")
    _add_scan_options(p_scan)

    sub.add_parser("version", help="Print package and resource versions.")
    return parser


def _print_summary(document: HeartbeatDocument) -> None:
    repos = len(document.sources)
    print(
        f"scanned {repos} repo(s): "
        f"{len(document.nodes)} nodes, {len(document.edges)} edges, "
        f"{len(document.pulses)} pulses.",
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"scienceheartbeat {PACKAGE_VERSION}")
        print(
            f"schema={SCHEMA_VERSION} palette={PALETTE_VERSION} "
            f"classifier={CLASSIFIER_VERSION} layout={LAYOUT_VERSION}"
        )
        return 0

    if args.activity:
        print(
            "scienceheartbeat: ingesting PRIVATE machine activity — do not publish this artifact.",
            file=sys.stderr,
        )

    document = heartbeat_from_paths(
        list(args.paths),
        limit=args.limit,
        include_merges=args.merges,
        max_depth=args.max_depth,
        activity=args.activity,
        loops_dir=None if args.no_loops else args.loops_dir,
        owner_email=args.owner_email,
        sync_limit=args.sync_limit,
    )

    if args.command == "scan":
        print(dumps(document))
        return 0

    from scienceheartbeat.dashboard.serve import serve, write_dashboard

    out = args.out or (_PRIVATE_OUT if args.activity else _PUBLIC_OUT)

    if args.command == "build":
        write_dashboard(
            document,
            out,
            html=not args.json_only,
            json=not args.html_only,
        )
        _print_summary(document)
        print(f"wrote dashboard to {out}/")
        return 0

    if args.command == "serve":
        _print_summary(document)
        serve(
            document,
            out,
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
        )
        return 0

    return 1  # pragma: no cover - argparse enforces a valid command


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
