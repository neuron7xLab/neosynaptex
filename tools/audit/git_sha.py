"""Canonical ``git_head_sha`` — single source of truth for commit-SHA stamping.

Signal contract
---------------

Every audit tool, bridge runner, and telemetry emitter that stamps a
commit SHA onto a produced artefact MUST go through this function.
Shape and sentinel convention are invariant and referenced by:

* ``substrates/bridge/levin_runner.py::git_head_sha`` —
  re-exports from here (see that module for historical context on
  the inline copy that used to live there).
* ``tools/telemetry/emit.py::stamp_commit_sha`` —
  re-exports from here (after PR #84 merges).
* ``docs/protocols/telemetry_spine_spec.md §8`` — cites this
  function as the single source of truth; a prior revision of that
  spec cited ``tools/audit/claim_status_applied.py::git_head_sha``
  which never existed, a spec↔code drift fixed in this PR.

Contract
--------

* **Input.** Optional ``repo_root: Path`` (defaults to
  ``Path.cwd()``).
* **Output.** Either the canonical 40-hex HEAD SHA when a git
  checkout is resolvable at ``repo_root``, or the string
  ``UNSTAMPED:<12hex>`` where the 12 hex chars are the first 12
  of ``sha1(str(repo_root).encode()).hexdigest()``. The sentinel
  shape is verifiable and distinguishable from a real SHA; rows or
  events stamped with it MUST be rejected at review.

* **Never raises.** git-subprocess failures, missing binaries, and
  OS errors all collapse to the sentinel path. The caller always
  gets a stable string.

Scope
-----

Deliberately narrow: no caching, no environment overrides, no alt
commit-ref lookup. Consolidation is the point; adding features here
re-introduces the divergence risk this module exists to kill.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess

__all__ = ["UNSTAMPED_PREFIX", "git_head_sha"]

UNSTAMPED_PREFIX: str = "UNSTAMPED:"


def git_head_sha(repo_root: pathlib.Path | None = None) -> str:
    """Return the current HEAD SHA or the ``UNSTAMPED:<12hex>`` sentinel."""

    root = repo_root if repo_root is not None else pathlib.Path.cwd()
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        fake = hashlib.sha1(str(root).encode()).hexdigest()
        return f"{UNSTAMPED_PREFIX}{fake[:12]}"
