"""End-to-end DCVP integration tests with mock substrate pairs.

These tests spawn real subprocesses via multiprocessing.get_context("spawn")
and therefore exercise the full isolation path. They are kept small so
CI stays under a few seconds per test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formal.dcvp.pairs import list_pairs
from formal.dcvp.protocol import (
    DCVPConfig,
    PairSpec,
    PerturbationSpec,
)
from formal.dcvp.runner import run_dcvp

PAIRS_REQUIRED = {"causal_linear", "independent", "shared_driver"}


def test_mock_pairs_registered() -> None:
    assert PAIRS_REQUIRED.issubset(set(list_pairs()))


def _cfg(pair_name: str) -> DCVPConfig:
    return DCVPConfig(
        pair=PairSpec(name=pair_name, a=pair_name + "_a", b=pair_name + "_b"),
        seeds=(11, 22),
        perturbations=(
            PerturbationSpec(kind="noise", sigma=0.1),
            PerturbationSpec(kind="noise", sigma=0.3),
            PerturbationSpec(kind="delay", sigma=0.0, delay_ticks=1),
        ),
        n_ticks=96,
        te_null_n=40,
        granger_max_lag=4,
    )


@pytest.mark.timeout(60)
def test_end_to_end_causal_pair_produces_report(tmp_path: Path) -> None:
    cfg = _cfg("causal_linear")
    report = run_dcvp(cfg, workdir=tmp_path)
    assert report.verdict.label in {"CAUSAL_INVARIANT", "CONDITIONAL", "ARTIFACT"}
    assert len(report.causality_matrix) == len(cfg.seeds) * len(cfg.perturbations)
    assert set(report.gamma_a.keys()) == set(cfg.seeds)
    assert set(report.gamma_b.keys()) == set(cfg.seeds)
    # Raw γ series exist and are the right length.
    for s in cfg.seeds:
        assert len(report.gamma_a[s]) == cfg.n_ticks
        assert len(report.gamma_b[s]) == cfg.n_ticks
    assert len(report.reproducibility_hash) == 64
    assert len(report.code_hash) == 64
    assert len(report.data_hash) == 64
    # Controls dict has the four required keys.
    expected = {
        "randomized_source",
        "time_reversed",
        "cross_run_mismatch",
        "synthetic_noise_only",
    }
    assert expected == set(report.controls)


@pytest.mark.timeout(60)
def test_independent_pair_not_causal_invariant(tmp_path: Path) -> None:
    cfg = _cfg("independent")
    report = run_dcvp(cfg, workdir=tmp_path)
    # Independent data must NOT be declared a clean causal invariant.
    assert report.verdict.label != "CAUSAL_INVARIANT"


@pytest.mark.timeout(60)
def test_report_is_deterministic_across_runs(tmp_path: Path) -> None:
    cfg = _cfg("causal_linear")
    r1 = run_dcvp(cfg, workdir=tmp_path / "run1")
    r2 = run_dcvp(cfg, workdir=tmp_path / "run2")
    # Same config, same seeds → identical γ streams → identical data hash.
    assert r1.data_hash == r2.data_hash
    assert r1.reproducibility_hash == r2.reproducibility_hash
