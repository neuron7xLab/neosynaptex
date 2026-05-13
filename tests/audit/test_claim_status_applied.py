"""Deterministic tests for the claim-status-applied audit.

These tests exercise the core git-free logic:
``count_labels_in_texts``, ``decide_verdict``, and ``WindowReport``.
The git driver (``_git_log_commits_in_window``, ``run_audit``) is a
thin wrapper and is intentionally not tested here — its only
responsibility is to format git-log output into the core's input shape.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt

import pytest

from tools.audit.claim_status_applied import (
    CANONICAL_LABELS,
    Verdict,
    WindowReport,
    count_labels_in_texts,
    decide_verdict,
)

# ---------------------------------------------------------------------------
# Label counting
# ---------------------------------------------------------------------------


def test_canonical_labels_are_exactly_five():
    assert len(CANONICAL_LABELS) == 5
    assert set(CANONICAL_LABELS) == {
        "measured",
        "derived",
        "hypothesized",
        "unverified analogy",
        "falsified",
    }


def test_empty_input_yields_zero_counts():
    labeled, per_label, distinct = count_labels_in_texts([])
    assert labeled == 0
    assert all(v == 0 for v in per_label.values())
    assert distinct == 0


def test_frontmatter_status_field_is_counted():
    block = """
---
name: sample
status: measured
---
body text
"""
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1
    assert per_label["measured"] == 1
    assert distinct == 1


def test_claim_status_key_variants_all_counted():
    blocks = [
        "claim_status: derived\n",
        "p_status: falsified\n",
        "claim: hypothesized\n",
    ]
    labeled, per_label, distinct = count_labels_in_texts(blocks)
    assert labeled == 3
    assert per_label["derived"] == 1
    assert per_label["falsified"] == 1
    assert per_label["hypothesized"] == 1
    assert distinct == 3


def test_bullet_with_backticked_label_is_counted():
    block = "- `measured` — directly instrumented signal"
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1
    assert per_label["measured"] == 1


def test_bullet_with_plain_label_colon_is_counted():
    block = "- measured: we observed γ ≈ 0.97 ± 0.03"
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1
    assert per_label["measured"] == 1


def test_bare_prose_is_not_counted():
    """`measured` as a verb in prose must not trigger the signal."""

    block = "We measured the gamma exponent across four substrates."
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 0
    assert all(v == 0 for v in per_label.values())


def test_unverified_analogy_multiword_label_is_counted():
    block = "claim_status: unverified analogy\n"
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1
    assert per_label["unverified analogy"] == 1


def test_multiple_labels_same_block_counted_independently():
    block = """
- `measured` — primary
- `derived` — secondary
- `hypothesized` — tertiary
"""
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1  # single block
    assert per_label["measured"] == 1
    assert per_label["derived"] == 1
    assert per_label["hypothesized"] == 1
    assert distinct == 3


def test_case_insensitive_matching():
    block = "status: Measured\n"
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 1
    assert per_label["measured"] == 1


def test_self_reference_block_is_excluded_by_default():
    """The canon doc itself must not trivially satisfy its own audit."""

    block = """
# SYSTEM PROTOCOL — NEOSYNAPTEX MEASUREMENT FRAMEWORK
- `measured`
- `derived`
"""
    labeled, per_label, distinct = count_labels_in_texts([block])
    assert labeled == 0
    assert distinct == 0


def test_self_reference_exclusion_can_be_disabled():
    block = """
# SYSTEM PROTOCOL — NEOSYNAPTEX MEASUREMENT FRAMEWORK
- `measured`
"""
    labeled, per_label, distinct = count_labels_in_texts([block], exclude_self_references=False)
    assert labeled == 1
    assert per_label["measured"] == 1


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def _window(
    end: _dt.date,
    commits: int,
    labeled: int,
    distinct: int,
    *,
    per_label: dict[str, int] | None = None,
) -> WindowReport:
    return WindowReport(
        start=end - _dt.timedelta(days=30),
        end=end,
        total_commits=commits,
        labeled_blocks=labeled,
        per_label_counts=per_label or {label: 0 for label in CANONICAL_LABELS},
        distinct_labels_used=distinct,
    )


def test_verdict_no_signal_when_no_windows():
    v = decide_verdict([])
    assert v.name == "no_signal"


def test_verdict_no_signal_when_all_windows_have_zero_commits():
    windows = [
        _window(_dt.date(2026, 3, 1), commits=0, labeled=0, distinct=0),
        _window(_dt.date(2026, 3, 31), commits=0, labeled=0, distinct=0),
        _window(_dt.date(2026, 4, 30), commits=0, labeled=0, distinct=0),
    ]
    v = decide_verdict(windows)
    assert v.name == "no_signal"


def test_verdict_stopped_on_three_consecutive_unlabeled_windows():
    """The explicit falsifier for kill-criterion taxonomy_disuse."""

    windows = [
        _window(_dt.date(2026, 2, 28), commits=12, labeled=0, distinct=0),
        _window(_dt.date(2026, 3, 30), commits=9, labeled=0, distinct=0),
        _window(_dt.date(2026, 4, 29), commits=7, labeled=0, distinct=0),
    ]
    v = decide_verdict(windows)
    assert v.name == "stopped"
    assert "falsifier" in v.reason.lower()


def test_verdict_applied_when_latest_has_diverse_labels():
    windows = [
        _window(
            _dt.date(2026, 4, 29),
            commits=10,
            labeled=6,
            distinct=3,
        ),
    ]
    v = decide_verdict(windows)
    assert v.name == "applied"


def test_verdict_at_risk_when_only_one_distinct_label():
    """Diversity gate catches ritual-pasting."""

    windows = [
        _window(_dt.date(2026, 4, 29), commits=10, labeled=10, distinct=1),
    ]
    v = decide_verdict(windows)
    assert v.name == "at_risk"
    assert "distinct" in v.reason.lower()


def test_verdict_at_risk_when_rate_drops_sharply():
    windows = [
        _window(_dt.date(2026, 3, 30), commits=10, labeled=8, distinct=3),
        _window(_dt.date(2026, 4, 29), commits=10, labeled=3, distinct=2),
    ]
    v = decide_verdict(windows)
    assert v.name == "at_risk"
    assert "rate" in v.reason.lower()


def test_verdict_at_risk_when_latest_has_zero_labeled_blocks():
    windows = [
        _window(_dt.date(2026, 3, 30), commits=10, labeled=8, distinct=3),
        _window(_dt.date(2026, 4, 29), commits=10, labeled=0, distinct=0),
    ]
    v = decide_verdict(windows)
    assert v.name == "at_risk"


def test_verdict_stopped_takes_priority_over_at_risk():
    """Three-in-a-row zero + some earlier labeled history → stopped."""

    windows = [
        _window(_dt.date(2026, 1, 1), commits=10, labeled=8, distinct=3),
        _window(_dt.date(2026, 2, 28), commits=12, labeled=0, distinct=0),
        _window(_dt.date(2026, 3, 30), commits=9, labeled=0, distinct=0),
        _window(_dt.date(2026, 4, 29), commits=7, labeled=0, distinct=0),
    ]
    v = decide_verdict(windows)
    assert v.name == "stopped"


# ---------------------------------------------------------------------------
# Report fields
# ---------------------------------------------------------------------------


def test_window_labeled_rate_is_ratio():
    w = _window(_dt.date(2026, 4, 29), commits=10, labeled=4, distinct=2)
    assert w.labeled_rate == pytest.approx(0.4)


def test_window_labeled_rate_is_zero_when_no_commits():
    w = _window(_dt.date(2026, 4, 29), commits=0, labeled=0, distinct=0)
    assert w.labeled_rate == 0.0


def test_verdict_is_frozen_dataclass():
    v = Verdict(name="applied", reason="ok")
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.name = "stopped"  # type: ignore[misc]
