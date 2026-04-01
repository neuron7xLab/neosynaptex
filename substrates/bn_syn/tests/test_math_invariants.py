from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

try:
    import hypothesis.extra.numpy as hnp
    from hypothesis import given, strategies as st

    _HYPOTHESIS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - exercised in subprocess contract test
    _HYPOTHESIS_AVAILABLE = False

from scripts.math_validate import build_manifest, iter_scope_files, validate_manifest
from contracts import (
    assert_adjacency_binary,
    assert_column_ranges,
    assert_coupling_matrix_properties,
    assert_dt_stability,
    assert_dtype_consistency,
    assert_energy_bounded,
    assert_integration_tolerance_consistency,
    assert_no_catastrophic_cancellation,
    assert_no_division_by_zero_risk,
    assert_no_duplicate_rows,
    assert_no_exp_overflow_risk,
    assert_no_log_domain_violation,
    assert_no_nan_in_dataset,
    assert_non_empty_text,
    assert_numeric_finite_and_bounded,
    assert_order_parameter_computation,
    assert_order_parameter_range,
    assert_phase_range,
    assert_phase_velocity_finite,
    assert_probability_normalization,
    assert_state_finite_after_step,
    assert_timeseries_monotonic_time,
    assert_weight_matrix_nonnegative,
)


class TestContractNegativeCases:
    def test_non_empty_text_rejects_blank(self) -> None:
        with pytest.raises(AssertionError, match="empty_text"):
            assert_non_empty_text("  ")

    def test_numeric_finite_rejects_inf(self) -> None:
        with pytest.raises(AssertionError, match="non_finite"):
            assert_numeric_finite_and_bounded([1.0, math.inf])

    def test_dt_stability_rejects_unstable(self) -> None:
        with pytest.raises(AssertionError, match="dt_stability_violation"):
            assert_dt_stability(0.1, 20.0, method="euler")

    def test_state_finite_rejects_nan(self) -> None:
        with pytest.raises(AssertionError, match="state_non_finite"):
            assert_state_finite_after_step(np.array([1.0, np.nan]), 42)

    def test_energy_rejects_growth(self) -> None:
        with pytest.raises(AssertionError, match="energy_monotonicity_violation"):
            assert_energy_bounded(np.array([1.0, 1.2]), 2.0)

    def test_tolerance_rejects_bad_atol(self) -> None:
        with pytest.raises(AssertionError, match="atol_dt_inconsistent"):
            assert_integration_tolerance_consistency(0.1, 1e-6, 0.01)

    def test_phase_range_rejects_invalid(self) -> None:
        with pytest.raises(AssertionError, match="phase_out_of_range"):
            assert_phase_range(np.array([0.1, 7.1]))

    def test_order_parameter_range_rejects(self) -> None:
        with pytest.raises(AssertionError, match="order_parameter_out_of_range"):
            assert_order_parameter_range(1.2)

    def test_order_parameter_computation_rejects(self) -> None:
        with pytest.raises(AssertionError, match="order_parameter_mismatch"):
            assert_order_parameter_computation(np.array([0.0, np.pi]), 0.9)

    def test_phase_velocity_rejects_inf(self) -> None:
        with pytest.raises(AssertionError, match="phase_velocity_non_finite"):
            assert_phase_velocity_finite(np.array([1.0, np.inf]))

    def test_coupling_matrix_rejects_asymmetry(self) -> None:
        with pytest.raises(AssertionError, match="coupling_not_symmetric"):
            assert_coupling_matrix_properties(np.array([[1.0, 2.0], [0.0, 1.0]]))

    def test_adjacency_rejects_self_loops(self) -> None:
        with pytest.raises(AssertionError, match="adjacency_self_loops"):
            assert_adjacency_binary(np.array([[1, 0], [0, 0]]))

    def test_weight_matrix_rejects_negative(self) -> None:
        with pytest.raises(AssertionError, match="weight_negative"):
            assert_weight_matrix_nonnegative(np.array([[1.0, -1.0], [0.0, 1.0]]))

    def test_cancellation_contract_rejects_precision_loss(self) -> None:
        a = np.array([1e16], dtype=np.float64)
        b = np.array([1e16 - 1.0], dtype=np.float64)
        with pytest.raises(AssertionError, match="catastrophic_cancellation"):
            assert_no_catastrophic_cancellation(a, b, np.array([0.0]), "test")

    def test_log_domain_rejects_non_positive(self) -> None:
        with pytest.raises(AssertionError, match="log_domain_violation"):
            assert_no_log_domain_violation(np.array([1.0, 0.0]), "test")

    def test_exp_overflow_rejects_large_values(self) -> None:
        with pytest.raises(AssertionError, match="exp_overflow_risk"):
            assert_no_exp_overflow_risk(np.array([1.0, 800.0]), "test")

    def test_division_by_zero_rejects_tiny_denominator(self) -> None:
        with pytest.raises(AssertionError, match="division_by_zero_risk"):
            assert_no_division_by_zero_risk(np.array([1.0, 1e-320]), "test")

    def test_dtype_consistency_rejects_mixed(self) -> None:
        with pytest.raises(AssertionError, match="dtype_mismatch"):
            assert_dtype_consistency({"a": np.array([1.0], dtype=np.float32), "b": np.array([1.0], dtype=np.float64)})

    def test_nan_dataset_rejects(self) -> None:
        with pytest.raises(AssertionError, match="dataset_nan"):
            assert_no_nan_in_dataset(np.array([1.0, np.nan]), "x")

    def test_duplicate_rows_rejects(self) -> None:
        with pytest.raises(AssertionError, match="dataset_duplicate_rows"):
            assert_no_duplicate_rows(np.array([[1, 2], [1, 2]]), "x")

    def test_column_ranges_rejects(self) -> None:
        d = np.array([(1.2,)], dtype=[("r", np.float64)])
        with pytest.raises(AssertionError, match="column_out_of_range"):
            assert_column_ranges(d, {"r": (0.0, 1.0)}, "x")

    def test_probability_normalization_rejects(self) -> None:
        with pytest.raises(AssertionError, match="probability_not_normalized"):
            assert_probability_normalization(np.array([[0.2, 0.2]]), axis=1)

    def test_timeseries_monotonic_rejects(self) -> None:
        with pytest.raises(AssertionError, match="time_not_strictly_increasing"):
            assert_timeseries_monotonic_time(np.array([0.0, 0.0, 1.0]))


if _HYPOTHESIS_AVAILABLE:

    @given(
        phases=hnp.arrays(
            np.float64,
            shape=hnp.array_shapes(min_dims=1, max_dims=1, min_side=1, max_side=200),
            elements=st.floats(min_value=0.0, max_value=(2 * np.pi) - 1e-12, allow_nan=False, allow_infinity=False),
        )
    )
    def test_order_parameter_always_in_unit_interval(phases: np.ndarray) -> None:
        r = float(np.abs(np.mean(np.exp(1j * phases))))
        assert 0.0 <= r <= 1.0 + 1e-10


    @given(N=st.integers(min_value=2, max_value=20))
    def test_symmetric_coupling_stays_symmetric(N: int) -> None:
        rng = np.random.default_rng(123)
        K = rng.standard_normal((N, N))
        K = (K + K.T) / 2.0
        assert_coupling_matrix_properties(K, expected_symmetric=True)

else:

    def test_order_parameter_always_in_unit_interval() -> None:
        pytest.skip("Hypothesis is required for property tests")


    def test_symmetric_coupling_stays_symmetric() -> None:
        pytest.skip("Hypothesis is required for property tests")


def test_manifest_covers_scoped_files() -> None:
    manifest = build_manifest()
    manifest_paths = {item["path"] for item in manifest["artifacts"]}
    scoped_paths = {str(path).replace("\\", "/") for path in iter_scope_files()}
    assert manifest_paths == scoped_paths


def test_validator_reports_no_failures_current_manifest() -> None:
    manifest = build_manifest()
    checks = validate_manifest(manifest)
    failures = [check for check in checks if check.status == "FAIL"]
    assert failures == []


def test_validator_detects_untrusted_provenance(tmp_path: Path) -> None:
    artifact = tmp_path / "sample.json"
    artifact.write_text(json.dumps({"x": 1.0}), encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "2.0",
        "timestamp": "2026-01-01T00:00:00Z",
        "artifacts": [
            {
                "path": str(artifact),
                "sha256": digest,
                "type": "derived_data",
                "generator": None,
                "provenance": "UNTRUSTED",
                "provenance_gap": "test",
            }
        ],
    }
    checks = validate_manifest(manifest)
    assert any(c.check_name == "provenance_trust" and c.status == "FAIL" for c in checks)


def test_build_manifest_has_no_untrusted_entries() -> None:
    manifest = build_manifest()
    assert all(a["provenance"] != "UNTRUSTED" for a in manifest["artifacts"])
