"""Deterministic tests for the canonical ``git_head_sha`` module."""

from __future__ import annotations

import pathlib

from tools.audit.git_sha import UNSTAMPED_PREFIX, git_head_sha


def test_git_head_sha_in_repo_returns_40_hex(tmp_path, monkeypatch):
    """Called with the actual repo root, returns a 40-hex SHA."""

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    sha = git_head_sha(repo_root)
    assert len(sha) == 40
    assert all(c in "0123456789abcdefABCDEF" for c in sha)


def test_git_head_sha_outside_repo_returns_unstamped_sentinel(tmp_path):
    sha = git_head_sha(tmp_path)
    assert sha.startswith(UNSTAMPED_PREFIX)
    assert len(sha) == len(UNSTAMPED_PREFIX) + 12


def test_git_head_sha_unstamped_is_deterministic_per_path(tmp_path):
    """Same tmp_path → same sentinel. Different path → different sentinel."""

    a = git_head_sha(tmp_path)
    b = git_head_sha(tmp_path)
    c = git_head_sha(tmp_path / "other")
    assert a == b
    assert a != c


def test_git_head_sha_default_root_is_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert git_head_sha().startswith(UNSTAMPED_PREFIX)


def test_levin_runner_re_exports_canonical(monkeypatch, tmp_path):
    """The levin_runner re-export must produce the canonical shape.

    Pins that future refactors don't accidentally re-introduce a
    second inline implementation in the bridge runner.
    """

    from substrates.bridge.levin_runner import git_head_sha as levin_shim

    a = levin_shim(tmp_path)
    b = git_head_sha(tmp_path)
    assert a == b
