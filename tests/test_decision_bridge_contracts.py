"""Tests for the contract ↔ test consistency auditor.

Invariant I-DB-CNTR-1 (meta): the auditor itself is green on the
current repository. If this test fails, either a YAML entry has
gone stale or the source tree mentions a new I-DB-* identifier
that nobody registered.
"""

from __future__ import annotations

from tools.audit.decision_bridge_contracts import check


def test_registered_contracts_all_resolve_to_real_tests() -> None:
    report = check()
    assert report.yaml_error is None, report.yaml_error
    assert report.missing_tests == [], "\n".join(
        f"{i}: {f}::{s}" for i, f, s in report.missing_tests
    )
    assert report.unregistered_ids == [], (
        "Source cites unregistered invariant ids: "
        f"{report.unregistered_ids}. Register them in "
        "docs/contracts/decision_bridge.yaml."
    )
