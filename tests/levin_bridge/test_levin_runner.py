"""Deterministic tests for the Levin bridge runner scaffolding.

These tests exercise the substrate-independent machinery: the CSV
schema (v2) and append-only writer, control-family transforms, plan
construction, dry-run orchestration, v1→v2 migration, and the new
contract split that makes ``P`` optional with explicit ``P_status``.

Concrete substrate wiring is tested in substrate-owned test suites
once the ``execute`` methods land.
"""

from __future__ import annotations

import csv
import math
import pathlib

import numpy as np
import pytest

from substrates.bridge.levin_runner import (
    ADAPTERS,
    SCHEMA_V1_COLUMNS,
    SCHEMA_V2_COLUMNS,
    SCHEMA_VERSION,
    BNSynAdapter,
    ControlFamily,
    KuramotoAdapter,
    MFNPlusAdapter,
    PStatus,
    RunRow,
    SchemaVersionMismatch,
    append_rows,
    apply_post_output_control,
    build_plan,
    git_head_sha,
    migrate_v1_to_v2,
    run_plan,
)

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


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


def test_plan_size_matches_adapter_scope():
    """N(in-scope substrates) × 3 regimes × 5 control families.

    The in-scope substrate set is canonised in
    ``evidence/levin_bridge/horizon_knobs.md §4`` (LLM scoped out) and
    reconciled with ``docs/protocols/levin_bridge_protocol.md §Step 2``.
    Current operational minimum is N=3; aspirational minimum remains
    N≥4 and any LEVIN_BRIDGE_VERDICT.md written at N=3 MUST name this
    as a limitation. Changing ADAPTERS here without updating both
    canonical docs is a contract-code drift and will be rejected at
    review.
    """

    plan = build_plan()
    assert len(plan) == len(ADAPTERS) * 3 * len(ControlFamily)
    assert len(ADAPTERS) == 3, (
        "in-scope substrate count drifted from horizon_knobs.md §4; "
        "update both docs or revert ADAPTERS"
    )
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
# Dry-run orchestration (v2 contract)
# ---------------------------------------------------------------------------


def test_dry_run_emits_nan_metrics_with_p_none_and_not_defined():
    plan = build_plan([BNSynAdapter])
    rows = run_plan(plan, dry_run=True, commit_sha="abc123")
    assert len(rows) == 15  # 3 regimes × 5 controls
    for row in rows:
        assert row.commit_sha.startswith("DRYRUN:")
        assert row.schema_version == SCHEMA_VERSION
        assert math.isnan(row.gamma)
        assert math.isnan(row.H_raw)
        assert row.n_samples == 0
        assert row.P is None, "dry-run has not measured any productivity metric; P must be None"
        assert row.P_status is PStatus.NOT_DEFINED


def test_run_plan_raises_without_wiring():
    plan = build_plan([MFNPlusAdapter])
    with pytest.raises(NotImplementedError):
        run_plan(plan, dry_run=False)


# ---------------------------------------------------------------------------
# RunRow v2 invariants
# ---------------------------------------------------------------------------


def _defined_row(**overrides) -> RunRow:
    base = dict(
        substrate="example_substrate_with_prereg",
        regime="intermediate",
        control_family=ControlFamily.PRODUCTIVE,
        H_raw=0.18,
        H_rank=2.0,
        C=0.973,
        gamma=0.984,
        gamma_ci_lo=0.912,
        gamma_ci_hi=1.047,
        P=0.732,
        P_status=PStatus.DEFINED,
        n_samples=1024,
        commit_sha="0" * 40,
        timestamp_utc="2026-04-14T00:00:00Z",
    )
    base.update(overrides)
    return RunRow(**base)


def _not_defined_row(**overrides) -> RunRow:
    base = dict(
        substrate="example_substrate_no_prereg",
        regime="intermediate",
        control_family=ControlFamily.PRODUCTIVE,
        H_raw=0.18,
        H_rank=2.0,
        C=0.973,
        gamma=0.984,
        gamma_ci_lo=0.912,
        gamma_ci_hi=1.047,
        P=None,
        P_status=PStatus.NOT_DEFINED,
        n_samples=1024,
        commit_sha="0" * 40,
        timestamp_utc="2026-04-14T00:00:00Z",
    )
    base.update(overrides)
    return RunRow(**base)


def test_runrow_accepts_numeric_p_with_defined_status():
    row = _defined_row()
    assert pytest.approx(0.732) == row.P
    assert row.P_status is PStatus.DEFINED
    cells = row.as_csv_row()
    assert cells[0] == SCHEMA_VERSION
    # P column is 11th (index 10), P_status is 12th (index 11)
    assert cells[10] == "0.732"
    assert cells[11] == "defined"


def test_runrow_accepts_none_p_with_not_defined():
    row = _not_defined_row()
    assert row.P is None
    assert row.P_status is PStatus.NOT_DEFINED
    cells = row.as_csv_row()
    assert cells[10] == "", "None P must serialise as an empty CSV cell"
    assert cells[11] == "not_defined"


def test_runrow_accepts_none_p_with_preregistered_pending():
    row = _not_defined_row(P_status=PStatus.PREREGISTERED_PENDING)
    assert row.P is None
    assert row.P_status is PStatus.PREREGISTERED_PENDING
    cells = row.as_csv_row()
    assert cells[10] == ""
    assert cells[11] == "preregistered_pending"


def test_runrow_rejects_numeric_p_with_not_defined_status():
    with pytest.raises(ValueError, match="P_status=DEFINED"):
        _defined_row(P_status=PStatus.NOT_DEFINED)


def test_runrow_rejects_none_p_with_defined_status():
    with pytest.raises(ValueError, match="DEFINED"):
        _not_defined_row(P_status=PStatus.DEFINED)


# ---------------------------------------------------------------------------
# CSV writer (v2 schema enforcement)
# ---------------------------------------------------------------------------


def test_append_rows_writes_v2_header_then_defined_row(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    written = append_rows([_defined_row()], out)
    assert written == 1
    with out.open() as fh:
        reader = csv.reader(fh)
        header = next(reader)
        data = next(reader)
    assert tuple(header) == SCHEMA_V2_COLUMNS
    assert header[0] == "schema_version"
    assert header[-1] == "timestamp_utc"
    assert len(header) == 15
    assert data[0] == SCHEMA_VERSION
    assert data[11] == "defined"


def test_append_rows_writes_none_p_as_empty_cell(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    append_rows([_not_defined_row()], out)
    with out.open() as fh:
        reader = csv.reader(fh)
        next(reader)
        data = next(reader)
    assert data[10] == "", "None P must be written as an empty CSV cell"
    assert data[11] == "not_defined"


def test_append_rows_is_append_only(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    append_rows([_defined_row()], out)
    append_rows([_not_defined_row(regime="expanded")], out)
    with out.open() as fh:
        lines = fh.read().strip().splitlines()
    assert len(lines) == 3  # header + 2 rows
    assert "intermediate" in lines[1]
    assert "expanded" in lines[2]


def test_append_rows_rejects_v1_header(tmp_path: pathlib.Path):
    out = tmp_path / "legacy.csv"
    out.write_text(",".join(SCHEMA_V1_COLUMNS) + "\n", encoding="utf-8")
    with pytest.raises(SchemaVersionMismatch, match="legacy v1 header"):
        append_rows([_defined_row()], out)


def test_append_rows_rejects_unknown_header(tmp_path: pathlib.Path):
    out = tmp_path / "bogus.csv"
    out.write_text("foo,bar,baz\n", encoding="utf-8")
    with pytest.raises(SchemaVersionMismatch, match="unknown header"):
        append_rows([_defined_row()], out)


# ---------------------------------------------------------------------------
# v1 → v2 migration
# ---------------------------------------------------------------------------


def test_migrate_v1_header_only_is_noop_on_v2(tmp_path: pathlib.Path):
    out = tmp_path / "metrics.csv"
    out.write_text(",".join(SCHEMA_V2_COLUMNS) + "\n", encoding="utf-8")
    assert migrate_v1_to_v2(out) == 0
    # header preserved
    assert out.read_text(encoding="utf-8").splitlines()[0] == ",".join(SCHEMA_V2_COLUMNS)


def test_migrate_v1_header_only_rewrites_to_v2(tmp_path: pathlib.Path):
    out = tmp_path / "legacy.csv"
    out.write_text(",".join(SCHEMA_V1_COLUMNS) + "\n", encoding="utf-8")
    assert migrate_v1_to_v2(out) == 0
    assert out.read_text(encoding="utf-8").splitlines()[0] == ",".join(SCHEMA_V2_COLUMNS)


def test_migrate_v1_with_data_refuses_without_opt_in(tmp_path: pathlib.Path):
    out = tmp_path / "legacy.csv"
    legacy_row = [
        "mfn_plus",
        "intermediate",
        "productive",
        "0.18",
        "2",
        "0.9",
        "0.95",
        "0.9",
        "1.0",
        "0.5",  # v1 mandatory P
        "100",
        "0" * 40,
        "2026-04-14T00:00:00Z",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(SCHEMA_V1_COLUMNS)
        writer.writerow(legacy_row)
    with pytest.raises(SchemaVersionMismatch, match="legacy data row"):
        migrate_v1_to_v2(out)


def test_migrate_v1_with_data_opt_in_empties_p_and_flags_pending(tmp_path: pathlib.Path):
    out = tmp_path / "legacy.csv"
    legacy_row = [
        "mfn_plus",
        "intermediate",
        "productive",
        "0.18",
        "2",
        "0.9",
        "0.95",
        "0.9",
        "1.0",
        "0.5",
        "100",
        "0" * 40,
        "2026-04-14T00:00:00Z",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(SCHEMA_V1_COLUMNS)
        writer.writerow(legacy_row)
    n = migrate_v1_to_v2(out, allow_data_rows=True)
    assert n == 1
    with out.open() as fh:
        reader = csv.reader(fh)
        header = next(reader)
        row = next(reader)
    assert tuple(header) == SCHEMA_V2_COLUMNS
    assert row[0] == SCHEMA_VERSION
    assert row[10] == "", "migration must not carry v1 P forward as defined"
    assert row[11] == "preregistered_pending"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_git_head_sha_returns_nonempty():
    sha = git_head_sha()
    assert sha
    # Either a full 40-char SHA or our explicit UNSTAMPED sentinel.
    assert len(sha) == 40 or sha.startswith("UNSTAMPED:")


# ---------------------------------------------------------------------------
# Fixtures — canonical examples of both contract states
# ---------------------------------------------------------------------------


def test_fixture_row_with_p_is_valid_v2():
    path = _FIXTURES / "row_with_P.csv"
    with path.open() as fh:
        reader = csv.reader(fh)
        header = next(reader)
        row = next(reader)
    assert tuple(header) == SCHEMA_V2_COLUMNS
    assert row[0] == SCHEMA_VERSION
    assert row[10] != "", "fixture row_with_P must have numeric P"
    assert row[11] == "defined"
    assert float(row[10]) == pytest.approx(0.732)


def test_fixture_row_without_p_is_valid_v2():
    path = _FIXTURES / "row_without_P.csv"
    with path.open() as fh:
        reader = csv.reader(fh)
        header = next(reader)
        row = next(reader)
    assert tuple(header) == SCHEMA_V2_COLUMNS
    assert row[0] == SCHEMA_VERSION
    assert row[10] == "", "fixture row_without_P must have empty P cell"
    assert row[11] == "not_defined"


def test_canonical_csv_header_is_v2(tmp_path: pathlib.Path):
    """evidence/levin_bridge/cross_substrate_horizon_metrics.csv must be v2."""

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    canonical = repo_root / "evidence" / "levin_bridge" / "cross_substrate_horizon_metrics.csv"
    assert canonical.exists()
    header_line = canonical.read_text(encoding="utf-8").splitlines()[0]
    assert tuple(header_line.split(",")) == SCHEMA_V2_COLUMNS
