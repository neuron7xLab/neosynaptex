"""Deterministic tests for the Levin bridge runner scaffolding.

These tests exercise the substrate-independent machinery: the CSV
schema and append-only writer, control-family transforms, plan
construction, and dry-run orchestration. Concrete substrate wiring is
tested in substrate-owned test suites once the ``execute`` methods land.
"""

from __future__ import annotations

import csv
import math
import pathlib

import numpy as np
import pytest

from substrates.bridge.levin_runner import (
    ADAPTERS,
    BNSynAdapter,
    ControlFamily,
    KuramotoAdapter,
    MFNPlusAdapter,
    RunRow,
    append_rows,
    apply_post_output_control,
    build_plan,
    git_head_sha,
    run_plan,
)

# ---------------------------------------------------------------------------
# Adapter shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls", ADAPTERS)
def test_adapter_declares_three_regimes(adapter_cls):
    adapter = adapter_cls()
    assert len(adapter.regimes) == 3, f"{adapter.name}: expected 3 regimes"
    names = [r.name for r in adapter.regimes]
    assert names == ["compressed", "intermediate", "expanded"], (
        f"{adapter.name}: regime order/names drift: {names}"
    )


@pytest.mark.parametrize("adapter_cls", ADAPTERS)
def test_adapter_declares_over_and_undercoupled(adapter_cls):
    adapter = adapter_cls()
    assert adapter.overcoupled_knobs, f"{adapter.name}: missing overcoupled_knobs"
    assert adapter.undercoupled_knobs, f"{adapter.name}: missing undercoupled_knobs"
    compressed_knobs = adapter.regime_by_name("compressed").knobs
    expanded_knobs = adapter.regime_by_name("expanded").knobs
    assert set(adapter.overcoupled_knobs) == set(expanded_knobs), (
        f"{adapter.name}: overcoupled_knobs keys must match regime knob keys"
    )
    assert set(adapter.undercoupled_knobs) == set(compressed_knobs), (
        f"{adapter.name}: undercoupled_knobs keys must match regime knob keys"
    )


def test_adapter_names_unique():
    names = [cls().name for cls in ADAPTERS]
    assert len(set(names)) == len(names), f"duplicate adapter names: {names}"


def test_llm_substrate_not_present():
    """LLM multi-agent is scoped out per horizon_knobs.md §4."""

    names = {cls().name for cls in ADAPTERS}
    forbidden = {"llm", "lm_substrate", "llm_multi_agent"}
    assert not (names & forbidden), (
        "LLM substrate was re-added without a closed-loop harness; "
        "see horizon_knobs.md §4 for re-entry conditions."
    )


def test_execute_without_wiring_raises():
    for cls in ADAPTERS:
        adapter = cls()
        with pytest.raises(NotImplementedError):
            adapter.execute(adapter.regimes[0].knobs, seed=0)


# ---------------------------------------------------------------------------
# Control-family transforms
# ---------------------------------------------------------------------------


def test_productive_is_identity():
    x = np.arange(10, dtype=float)
    out = apply_post_output_control(x, ControlFamily.PRODUCTIVE, seed=0)
    np.testing.assert_array_equal(out, x)


def test_shuffle_is_permutation_and_seeded():
    x = np.arange(100, dtype=float)
    a = apply_post_output_control(x, ControlFamily.SHUFFLE, seed=42)
    b = apply_post_output_control(x, ControlFamily.SHUFFLE, seed=42)
    c = apply_post_output_control(x, ControlFamily.SHUFFLE, seed=43)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)
    assert set(a.tolist()) == set(x.tolist()), "shuffle must be a permutation"
    assert not np.array_equal(a, x), "shuffle must change order (probabilistically)"


def test_matched_noise_preserves_moments():
    rng = np.random.default_rng(0)
    x = rng.normal(loc=5.0, scale=2.0, size=10_000)
    y = apply_post_output_control(x, ControlFamily.MATCHED_NOISE, seed=1)
    assert math.isclose(np.mean(y), np.mean(x), abs_tol=0.1)
    assert math.isclose(np.std(y), np.std(x), abs_tol=0.1)
    # Distinct realisation, not a permutation.
    assert not np.array_equal(np.sort(y), np.sort(x))


def test_knob_level_controls_raise_on_post_output_call():
    x = np.arange(10, dtype=float)
    with pytest.raises(ValueError):
        apply_post_output_control(x, ControlFamily.OVERCOUPLED_COLLAPSE, seed=0)
    with pytest.raises(ValueError):
        apply_post_output_control(x, ControlFamily.UNDERCOUPLED_FRAGMENTATION, seed=0)


# ---------------------------------------------------------------------------
# Plan matrix
# ---------------------------------------------------------------------------


def test_plan_size_matches_protocol():
    """N(substrates=3) × 3 regimes × 5 control families = 45 cells."""

    plan = build_plan()
    assert len(plan) == len(ADAPTERS) * 3 * len(ControlFamily)
    assert len(plan) == 45


def test_plan_uses_adapter_knobs_for_knob_level_controls():
    plan = build_plan([MFNPlusAdapter])
    over = [c for c in plan if c.control_family is ControlFamily.OVERCOUPLED_COLLAPSE]
    under = [c for c in plan if c.control_family is ControlFamily.UNDERCOUPLED_FRAGMENTATION]
    assert all(c.knobs == MFNPlusAdapter.overcoupled_knobs for c in over)
    assert all(c.knobs == MFNPlusAdapter.undercoupled_knobs for c in under)


def test_plan_uses_regime_knobs_for_output_level_controls():
    plan = build_plan([KuramotoAdapter])
    adapter = KuramotoAdapter()
    for cell in plan:
        if cell.control_family in (
            ControlFamily.PRODUCTIVE,
            ControlFamily.SHUFFLE,
            ControlFamily.MATCHED_NOISE,
        ):
            assert cell.knobs == adapter.regime_by_name(cell.regime).knobs


# ---------------------------------------------------------------------------
# Dry-run orchestration
# ---------------------------------------------------------------------------


def test_dry_run_emits_nan_metrics_and_dry_sha():
    plan = build_plan([BNSynAdapter])
    rows = run_plan(plan, dry_run=True, commit_sha="abc123")
    assert len(rows) == 15  # 3 regimes × 5 controls
    for row in rows:
        assert row.commit_sha.startswith("DRYRUN:")
        assert math.isnan(row.gamma)
        assert math.isnan(row.H_raw)
        assert row.n_samples == 0


def test_run_plan_raises_without_wiring():
    plan = build_plan([MFNPlusAdapter])
    with pytest.raises(NotImplementedError):
        run_plan(plan, dry_run=False)


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def _make_row(**overrides) -> RunRow:
    base = dict(
        substrate="mfn_plus",
        regime="intermediate",
        control_family=ControlFamily.PRODUCTIVE,
        H_raw=0.18,
        H_rank=2.0,
        C=0.5,
        gamma=0.97,
        gamma_ci_lo=0.90,
        gamma_ci_hi=1.04,
        P=42.0,
        n_samples=1000,
        commit_sha="abc123",
        timestamp_utc="2026-04-14T00:00:00Z",
    )
    base.update(overrides)
    return RunRow(**base)


def test_append_rows_writes_header_then_row(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    written = append_rows([_make_row()], out)
    assert written == 1
    with out.open() as fh:
        reader = csv.reader(fh)
        header = next(reader)
        data = next(reader)
    assert header[0] == "substrate"
    assert header[-1] == "timestamp_utc"
    assert len(header) == 13
    assert data[0] == "mfn_plus"
    assert data[2] == "productive"


def test_append_rows_is_append_only(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    append_rows([_make_row()], out)
    append_rows([_make_row(regime="expanded")], out)
    with out.open() as fh:
        lines = fh.read().strip().splitlines()
    assert len(lines) == 3  # header + 2 rows
    assert "intermediate" in lines[1]
    assert "expanded" in lines[2]


def test_append_rows_rejects_schema_drift(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    out.write_text("bogus,header\n")
    with pytest.raises(ValueError, match="schema drift"):
        append_rows([_make_row()], out)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_git_head_sha_returns_nonempty():
    sha = git_head_sha()
    assert sha
    # Either a full 40-char SHA or our explicit UNSTAMPED sentinel.
    assert len(sha) == 40 or sha.startswith("UNSTAMPED:")
