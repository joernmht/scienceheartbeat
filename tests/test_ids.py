from __future__ import annotations

from scienceheartbeat.core.ids import (
    branch_id,
    committer_id,
    edge_id,
    pulse_id,
    repo_id,
    slug,
)


def test_slug_is_stable_and_safe() -> None:
    assert slug("My Repo!") == "my-repo"
    assert slug("a/b c") == "a-b-c"
    assert slug("") == "x"


def test_ids_are_deterministic() -> None:
    assert repo_id("My Repo") == repo_id("My Repo")
    assert branch_id("r", "main") == branch_id("r", "main")
    assert committer_id("A@B.com", "A") == committer_id("a@b.com", "anything")
    assert pulse_id("r", "abcdef1234567890") == "pulse:r:abcdef123456"


def test_committer_identity_keys_on_email() -> None:
    # Same email, different display names -> same identity.
    assert committer_id("ada@x.io", "Ada") == committer_id("ADA@x.io", "A. Lovelace")
    # Different email -> different identity.
    assert committer_id("ada@x.io", "Ada") != committer_id("bob@x.io", "Ada")


def test_edge_ids_distinguish_direction() -> None:
    assert edge_id("authored", "a", "b") != edge_id("authored", "b", "a")
