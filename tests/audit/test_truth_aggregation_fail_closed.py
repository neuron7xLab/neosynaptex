"""Fail-closed discipline for the global truth verdict.

The previous aggregator skipped NaN-gamma domains, then ran
``all(v == "VERIFIED" for v in verdicts)`` on the remainder. Because
``all([])`` is ``True`` in Python, an engine with zero valid domains
could emit ``global_verdict == "VERIFIED"``. The new aggregator
(``contracts.fail_closed.aggregate_verdicts``) is strict: empty
collections and MISSING entries can never upgrade a verdict.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from contracts.fail_closed import (
    DomainAssessment,
    Verdict,
    aggregate_verdicts,
    parse_verdict,
)


def test_empty_domain_set_does_not_produce_verified() -> None:
    # The previous bug: all([]) is True, so zero domains produced VERIFIED.
    assert aggregate_verdicts([], {}) == Verdict.INCONCLUSIVE


def test_any_missing_domain_fails_closed() -> None:
    assert (
        aggregate_verdicts(
            ["A", "B"],
            {"A": Verdict.VERIFIED, "B": Verdict.MISSING},
        )
        == Verdict.FAIL_CLOSED
    )


def test_nan_domain_contributes_missing_not_skip() -> None:
    # Parse path: NaN / None / unknown label -> MISSING (not a silent pass).
    assert parse_verdict(None) == Verdict.MISSING
    assert parse_verdict("???") == Verdict.MISSING


def test_unknown_domain_entry_fails_closed() -> None:
    # Domain listed in order but absent from the mapping -> MISSING -> FAIL_CLOSED.
    assert (
        aggregate_verdicts(
            ["A", "B"],
            {"A": Verdict.VERIFIED},  # B missing entirely
        )
        == Verdict.FAIL_CLOSED
    )


def test_constructed_poisons_global() -> None:
    assert (
        aggregate_verdicts(
            ["A", "B", "C"],
            {
                "A": Verdict.VERIFIED,
                "B": Verdict.VERIFIED,
                "C": Verdict.CONSTRUCTED,
            },
        )
        == Verdict.CONSTRUCTED
    )


def test_fragile_poisons_global() -> None:
    assert (
        aggregate_verdicts(
            ["A", "B"],
            {"A": Verdict.VERIFIED, "B": Verdict.FRAGILE},
        )
        == Verdict.FRAGILE
    )


def test_inconclusive_poisons_global() -> None:
    assert (
        aggregate_verdicts(
            ["A", "B"],
            {"A": Verdict.VERIFIED, "B": Verdict.INCONCLUSIVE},
        )
        == Verdict.INCONCLUSIVE
    )


def test_verified_only_when_every_domain_verified() -> None:
    assert (
        aggregate_verdicts(
            ["A", "B", "C"],
            {name: Verdict.VERIFIED for name in ["A", "B", "C"]},
        )
        == Verdict.VERIFIED
    )


def test_domain_assessment_is_accepted() -> None:
    assess = DomainAssessment(domain="A", status=Verdict.VERIFIED)
    assert aggregate_verdicts(["A"], {"A": assess}) == Verdict.VERIFIED


def test_fail_closed_dominates_everything() -> None:
    # Even if one domain is VERIFIED and another CONSTRUCTED, a single
    # FAIL_CLOSED entry demotes the whole aggregation.
    assert (
        aggregate_verdicts(
            ["A", "B", "C"],
            {
                "A": Verdict.VERIFIED,
                "B": Verdict.CONSTRUCTED,
                "C": Verdict.FAIL_CLOSED,
            },
        )
        == Verdict.FAIL_CLOSED
    )


@given(
    statuses=st.lists(
        st.sampled_from(list(Verdict)),
        min_size=1,
        max_size=6,
    )
)
@settings(max_examples=60, deadline=None)
def test_hypothesis_aggregator_is_fail_closed(statuses: list[Verdict]) -> None:
    names = [f"d{i}" for i in range(len(statuses))]
    mapping = dict(zip(names, statuses))
    verdict = aggregate_verdicts(names, mapping)

    # Every VERIFIED outcome requires every domain to be VERIFIED.
    if verdict == Verdict.VERIFIED:
        assert all(s == Verdict.VERIFIED for s in statuses)

    # Any FAIL_CLOSED or MISSING entry forces FAIL_CLOSED.
    if any(s == Verdict.FAIL_CLOSED for s in statuses) or any(
        s == Verdict.MISSING for s in statuses
    ):
        assert verdict == Verdict.FAIL_CLOSED


class _NoopAdapter:
    """DomainAdapter that never produces usable topo/cost (gamma is NaN)."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def domain(self) -> str:
        return self._name

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 0.0}

    def topo(self) -> float:
        return float("nan")

    def thermo_cost(self) -> float:
        return float("nan")


def test_engine_truth_function_never_returns_verified_with_all_nan_domains() -> None:
    # End-to-end: zero valid gammas in registered adapters -> NOT VERIFIED.
    from neosynaptex import Neosynaptex

    engine = Neosynaptex(window=8)
    engine.register(_NoopAdapter("A"))
    engine.register(_NoopAdapter("B"))
    for _ in range(12):
        engine.observe()
    verdict = engine.truth_function()
    assert verdict["global_verdict"] != Verdict.VERIFIED.value
    assert verdict["global_verdict"] in {
        Verdict.INCONCLUSIVE.value,
        Verdict.FAIL_CLOSED.value,
    }
    assert verdict["n_domains_verified"] == 0
    assert verdict["n_domains_total"] == 2


def test_engine_truth_function_empty_history_is_inconclusive() -> None:
    from neosynaptex import Neosynaptex

    engine = Neosynaptex(window=8)
    verdict = engine.truth_function()
    assert verdict["global_verdict"] == Verdict.INCONCLUSIVE.value
