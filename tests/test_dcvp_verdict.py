"""Verdict aggregation + reproducibility hash."""

from __future__ import annotations

from formal.dcvp.protocol import (
    CausalityRow,
    DCVPConfig,
    PairSpec,
    PerturbationSpec,
)
from formal.dcvp.verdict import (
    aggregate_verdict,
    data_hash,
    reproducibility_hash,
    score_row,
)


def _row(passes: bool) -> CausalityRow:
    return CausalityRow(
        seed=1,
        perturbation=PerturbationSpec("noise", sigma=0.1),
        granger_p=0.001 if passes else 0.5,
        granger_lag=2,
        te_z=5.0 if passes else 0.5,
        te_value=0.1,
        cascade_lag=2,
        cascade_lag_cv=0.05 if passes else 0.5,
        jitter_survival=0.9 if passes else 0.1,
        alignment_sensitivity=0.05 if passes else 0.5,
        effect_size=0.3 if passes else 0.01,
        baseline_drift=0.02,
        passes=passes,
        fail_reasons=() if passes else ("mock",),
    )


def test_verdict_all_pass_no_controls() -> None:
    rows = tuple(_row(True) for _ in range(5))
    v = aggregate_verdict(rows, {"randomized_source": False, "synthetic_noise_only": False})
    assert v.label == "CAUSAL_INVARIANT"
    assert v.positive_frac == 1.0


def test_verdict_partial_becomes_conditional() -> None:
    rows = (_row(True), _row(True), _row(False))
    v = aggregate_verdict(rows, {"x": False})
    assert v.label == "CONDITIONAL"


def test_verdict_contaminated_control_is_artifact() -> None:
    rows = tuple(_row(True) for _ in range(5))
    v = aggregate_verdict(rows, {"randomized_source": True, "other": False})
    assert v.label == "ARTIFACT"
    assert v.controls_all_failed is False


def test_score_row_lists_every_failure() -> None:
    row = score_row(
        seed=0,
        perturbation=PerturbationSpec("noise", sigma=0.1),
        granger_p=0.5,
        granger_lag=1,
        te_obs=0.0,
        te_null_mean=0.0,
        te_null_std=1.0,
        cascade_mean_lag=0,
        cascade_cv=1.0,
        jitter_surv=0.0,
        alignment_sens=0.9,
        effect=0.0,
        drift=0.5,
    )
    assert row.passes is False
    assert len(row.fail_reasons) >= 5


def test_reproducibility_hash_deterministic() -> None:
    cfg = DCVPConfig(
        pair=PairSpec("causal_linear", "a", "b"),
        seeds=(1, 2, 3),
        perturbations=(PerturbationSpec("noise", sigma=0.1),),
        n_ticks=64,
    )
    h1 = reproducibility_hash(cfg, "code", "data")
    h2 = reproducibility_hash(cfg, "code", "data")
    assert h1 == h2
    assert len(h1) == 64


def test_reproducibility_hash_changes_with_config() -> None:
    cfg1 = DCVPConfig(
        pair=PairSpec("causal_linear", "a", "b"),
        seeds=(1,),
        perturbations=(PerturbationSpec("noise", sigma=0.1),),
    )
    cfg2 = DCVPConfig(
        pair=PairSpec("causal_linear", "a", "b"),
        seeds=(2,),
        perturbations=(PerturbationSpec("noise", sigma=0.1),),
    )
    assert reproducibility_hash(cfg1, "c", "d") != reproducibility_hash(cfg2, "c", "d")


def test_data_hash_stable() -> None:
    a = {1: (0.1, 0.2, 0.3)}
    b = {1: (0.4, 0.5, 0.6)}
    h1 = data_hash(a, b)
    h2 = data_hash(a, b)
    assert h1 == h2
