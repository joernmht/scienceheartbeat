"""Scrub secrets and trim free text before it can reach an artifact.

The activity sources read real log files that may contain access tokens (the
Overleaf git-bridge tokens live in remote URLs), e-mail addresses and long
prompts. Everything user-visible passes through :func:`redact` so a token can
never be embedded in a heartbeat document, and through :func:`preview` so only a
short, single-line snippet survives. The functions are pure (regex only), so
they do not affect determinism.
"""

from __future__ import annotations

import re

__all__ = ["host_of", "preview", "redact"]

# Token shapes seen in practice plus a generic long-secret catch-all. Order
# matters only for readability; each pattern is independent.
_TOKEN_PATTERNS = [
    re.compile(r"\bolp_[A-Za-z0-9]+"),  # Overleaf git-bridge tokens
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]+"),  # GitHub tokens
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+"),  # Slack tokens
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),  # long hex blobs (hashes, secrets)
    re.compile(r"\b[A-Za-z0-9_-]{40,}\b"),  # long opaque base64-ish blobs
]
_CREDENTIALS_IN_URL = re.compile(r"(https?://)[^/@\s]+@")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_WS = re.compile(r"\s+")


def redact(text: str) -> str:
    """Return ``text`` with tokens, URL credentials and e-mails masked.

    Whitespace is collapsed to single spaces so the result is one clean line.
    """

    out = _CREDENTIALS_IN_URL.sub(r"\1", text)
    for pat in _TOKEN_PATTERNS:
        out = pat.sub("[redacted]", out)
    out = _EMAIL.sub("[email]", out)
    return _WS.sub(" ", out).strip()


def preview(text: str, limit: int = 80) -> str:
    """Redact ``text`` and truncate it to ``limit`` characters with an ellipsis."""

    clean = redact(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def host_of(url: str) -> str:
    """Extract the bare host from a remote URL, dropping any credentials/token.

    Handles ``https://user:tok@host/path`` and ``git@host:path`` (scp) forms.
    Returns ``""`` if no host can be found. The token is never returned.
    """

    text = url.strip()
    scp = re.match(r"^[\w.+-]+@([^:/\s]+):", text)
    if scp:
        return scp.group(1)
    https = re.match(r"^[a-z]+://(?:[^/@\s]+@)?([^/:\s]+)", text)
    if https:
        return https.group(1)
    return ""
