# Security Policy

## Supported versions

This project is in alpha (0.x). Security fixes are applied to the latest
released version on the `main` branch.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, open a
private [GitHub security advisory](https://github.com/joernmht/scienceheartbeat/security/advisories/new),
or contact the maintainer via the contact listed on the repository profile.

We will acknowledge your report within a few days and keep you updated on the
fix.

## Scope notes

- `scienceheartbeat` shells out to `git` and reads repository history. It does
  not transmit your data anywhere — the dashboard is a static file generated
  locally.
- The generated dashboard inlines commit subjects and committer names into
  HTML. They are HTML-escaped before display, and `</` sequences in the
  embedded JSON are escaped so untrusted commit text cannot break out of the
  data block.
