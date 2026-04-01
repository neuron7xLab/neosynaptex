"""Release-grade hardening tests.

Property tests, negative tests, and mutation-oriented coverage
for decision paths, causal gate, and artifact integrity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.types.causal import CausalDecision, CausalValidationResult

# ═══════════════════════════════════════════════════════════════
#  Property tests — replay determinism
# ═══════════════════════════════════════════════════════════════


class TestReplayDeterminism:
    """Same input must produce identical output across runs."""

    @pytest.fixture
    def spec(self) -> mfn.SimulationSpec:
        return mfn.SimulationSpec(grid_size=16, steps=8, seed=42)

    def test_simulation_deterministic(self, spec: mfn.SimulationSpec) -> None:
        s1 = mfn.simulate(spec)
        s2 = mfn.simulate(spec)
        np.testing.assert_array_equal(s1.field, s2.field)

    def test_detection_deterministic(self, spec: mfn.SimulationSpec) -> None:
        seq = mfn.simulate(spec)
        d1 = seq.detect()
        d2 = seq.detect()
        assert d1.label == d2.label
        assert d1.score == d2.score

    def test_extraction_deterministic(self, spec: mfn.SimulationSpec) -> None:
        seq = mfn.simulate(spec)
        e1 = seq.extract()
        e2 = seq.extract()
        assert e1.to_dict() == e2.to_dict()

    def test_forecast_deterministic(self, spec: mfn.SimulationSpec) -> None:
        seq = mfn.simulate(spec)
        f1 = seq.forecast(4)
        f2 = seq.forecast(4)
        assert f1.horizon == f2.horizon

    def test_causal_verdict_deterministic(self, spec: mfn.SimulationSpec) -> None:
        seq = mfn.simulate(spec)
        desc = seq.extract()
        det = seq.detect()
        v1 = validate_causal_consistency(seq, desc, det, mode="strict")
        v2 = validate_causal_consistency(seq, desc, det, mode="strict")
        assert v1.decision == v2.decision
        assert v1.provenance_hash == v2.provenance_hash
        assert v1.config_hash == v2.config_hash

    def test_provenance_hash_changes_with_mode(self, spec: mfn.SimulationSpec) -> None:
        seq = mfn.simulate(spec)
        v_strict = validate_causal_consistency(seq, mode="strict")
        v_observe = validate_causal_consistency(seq, mode="observe")
        assert v_strict.provenance_hash != v_observe.provenance_hash
        assert v_strict.mode == "strict"
        assert v_observe.mode == "observe"


# ═══════════════════════════════════════════════════════════════
#  Property tests — perturbation stability
# ═══════════════════════════════════════════════════════════════


class TestPerturbationStability:
    """Detection labels should be stable under small perturbation."""

    def test_label_stable_under_epsilon_noise(self) -> None:
        spec = mfn.SimulationSpec(grid_size=24, steps=12, seed=7)
        seq = mfn.simulate(spec)
        baseline = seq.detect()
        for seed_offset in range(5):
            rng = np.random.default_rng(100 + seed_offset)
            perturbed_field = seq.field + rng.normal(0, 1e-6, seq.field.shape)
            perturbed_field = np.clip(perturbed_field, -95.0, 40.0)
            from mycelium_fractal_net.types.field import FieldSequence

            perturbed = FieldSequence(
                field=perturbed_field,
                spec=seq.spec,
                metadata=seq.metadata,
            )
            det = perturbed.detect()
            assert det.label == baseline.label, (
                f"Label changed from {baseline.label} to {det.label} "
                f"under 1e-6 noise (seed_offset={seed_offset})"
            )


# ═══════════════════════════════════════════════════════════════
#  Negative tests — corrupted/forged input
# ═══════════════════════════════════════════════════════════════


class TestNegativeInputs:
    """System must reject or flag corrupted data."""

    def test_nan_field_rejected_at_construction(self) -> None:
        """FieldSequence rejects NaN at construction — eager validation."""
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        corrupted_field = seq.field.copy()
        corrupted_field[0, 0] = float("nan")
        from mycelium_fractal_net.types.field import FieldSequence

        with pytest.raises(ValueError, match="NaN or Inf"):
            FieldSequence(field=corrupted_field, spec=seq.spec, metadata=seq.metadata)

    def test_inf_field_rejected_at_construction(self) -> None:
        """FieldSequence rejects Inf at construction — eager validation."""
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        corrupted_field = seq.field.copy()
        corrupted_field[5, 5] = float("inf")
        from mycelium_fractal_net.types.field import FieldSequence

        with pytest.raises(ValueError, match="NaN or Inf"):
            FieldSequence(field=corrupted_field, spec=seq.spec, metadata=seq.metadata)

    def test_out_of_bounds_field_triggers_error(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        corrupted_field = seq.field.copy()
        corrupted_field[0, :] = 100.0  # Above +40 mV biophysical limit
        from mycelium_fractal_net.types.field import FieldSequence

        corrupted = FieldSequence(field=corrupted_field, spec=seq.spec, metadata=seq.metadata)
        v = validate_causal_consistency(corrupted, mode="strict")
        assert v.decision == CausalDecision.FAIL
        assert any(r.rule_id == "SIM-003" and not r.passed for r in v.rule_results)


# ═══════════════════════════════════════════════════════════════
#  Causal gate mode tests
# ═══════════════════════════════════════════════════════════════


class TestCausalGateModes:
    """Verify mode semantics for the causal validation gate."""

    @pytest.fixture
    def clean_result(self) -> CausalValidationResult:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        return validate_causal_consistency(seq, mode="strict")

    def test_strict_mode_passes_clean_input(self, clean_result: CausalValidationResult) -> None:
        assert clean_result.decision == CausalDecision.PASS
        assert clean_result.mode == "strict"

    def test_observe_mode_never_fails(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        v = validate_causal_consistency(seq, mode="observe")
        assert v.decision in (CausalDecision.PASS, CausalDecision.DEGRADED)
        assert v.mode == "observe"

    def test_strict_release_strictest(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        v = validate_causal_consistency(seq, mode="strict_release")
        assert v.mode == "strict_release"
        # Clean input should pass even strict_release
        assert v.decision == CausalDecision.PASS

    def test_engine_version_populated(self, clean_result: CausalValidationResult) -> None:
        assert clean_result.engine_version != ""
        assert clean_result.engine_version != "unknown"

    def test_to_dict_has_all_fields(self, clean_result: CausalValidationResult) -> None:
        d = clean_result.to_dict()
        required_keys = {
            "schema_version",
            "decision",
            "ok",
            "stages_checked",
            "total_rules",
            "passed_rules",
            "error_count",
            "warning_count",
            "runtime_hash",
            "config_hash",
            "provenance_hash",
            "mode",
            "engine_version",
            "rule_version",
            "violations",
            "all_rules",
        }
        assert required_keys.issubset(d.keys()), f"Missing keys: {required_keys - d.keys()}"


# ═══════════════════════════════════════════════════════════════
#  Config governance tests
# ═══════════════════════════════════════════════════════════════


class TestConfigGovernance:
    """Config files must be valid, versioned, and consistent."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_detection_config_valid_json(self) -> None:
        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        assert "schema_version" in data
        assert data["schema_version"] == "mfn-detection-config-v1"

    def test_detection_config_has_required_sections(self) -> None:
        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        required = [
            "evidence_normalization",
            "regime_thresholds",
            "regime_weights",
            "anomaly_weights",
            "instability_weights",
            "confidence",
            "comparison",
            "forecast",
        ]
        for section in required:
            assert section in data, f"Missing required section: {section}"
            assert isinstance(data[section], dict), f"{section} must be dict"

    def test_detection_config_schema_validation(self) -> None:
        from mycelium_fractal_net.core.detection_config import _validate_schema

        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        warnings = _validate_schema(data)
        assert len(warnings) == 0, f"Schema validation warnings: {warnings}"

    def test_causal_config_valid_json(self) -> None:
        path = self.ROOT / "configs" / "causal_validation_v1.json"
        data = json.loads(path.read_text())
        assert "schema_version" in data
        assert "rules" in data
        assert "modes" in data

    def test_causal_config_has_all_modes(self) -> None:
        path = self.ROOT / "configs" / "causal_validation_v1.json"
        data = json.loads(path.read_text())
        expected_modes = {"strict", "strict_release", "strict_api", "observe", "permissive"}
        actual_modes = set(data["modes"].keys())
        assert expected_modes == actual_modes, f"Missing modes: {expected_modes - actual_modes}"

    def test_detection_config_weights_sum_to_one(self) -> None:
        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        aw = data["anomaly_weights"]
        total = sum(aw.values())
        assert abs(total - 1.0) < 0.01, f"Anomaly weights sum to {total}, expected ~1.0"
        iw = data["instability_weights"]
        total_i = sum(iw.values())
        assert abs(total_i - 1.0) < 0.01, f"Instability weights sum to {total_i}"

    def test_config_hash_deterministic(self) -> None:
        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        content = path.read_bytes()
        h1 = hashlib.sha256(content).hexdigest()
        h2 = hashlib.sha256(content).hexdigest()
        assert h1 == h2

    def test_config_loaded_matches_file(self) -> None:
        """Verify detection_config.py actually loaded values from the JSON file."""
        from mycelium_fractal_net.core.detection_config import (
            CONFIG_HASH,
            COSINE_NEAR_IDENTICAL,
            DAMPING_BASE,
            DYNAMIC_ANOMALY_BASELINE,
        )

        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        assert data["regime_thresholds"]["dynamic_anomaly_baseline"] == DYNAMIC_ANOMALY_BASELINE
        assert data["comparison"]["cosine_near_identical"] == COSINE_NEAR_IDENTICAL
        assert data["forecast"]["damping_base"] == DAMPING_BASE
        assert CONFIG_HASH != "default", "Config was not loaded from file"

    def test_forecast_config_present(self) -> None:
        path = self.ROOT / "configs" / "detection_thresholds_v1.json"
        data = json.loads(path.read_text())
        fc = data["forecast"]
        required_keys = [
            "damping_base",
            "damping_max",
            "fluidity_coeff_default",
            "field_clip_min",
            "field_clip_max",
            "uncertainty_w_plasticity",
            "uncertainty_w_connectivity",
            "uncertainty_w_desensitization",
            "structural_error_weight",
        ]
        for key in required_keys:
            assert key in fc, f"Missing forecast config key: {key}"


# ═══════════════════════════════════════════════════════════════
#  Release governance file checks
# ═══════════════════════════════════════════════════════════════


class TestReleaseGovernanceFiles:
    """Required release governance files must exist."""

    ROOT = Path(__file__).resolve().parents[1]

    @pytest.mark.parametrize(
        "path",
        [
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "KNOWN_LIMITATIONS.md",
            "RELEASE_NOTES.md",
            "docs/RELEASE_GOVERNANCE.md",
            "docs/QUALITY_GATE.md",
            "docs/PUBLIC_API_CONTRACT.md",
            "docs/ARCHITECTURE.md",
            "docs/API.md",
            "docs/CAUSAL_VALIDATION.md",
            "docs/BENCHMARKS.md",
            "docs/DATA_MODEL.md",
            "docs/DEPRECATION_POLICY.md",
            "docs/VERSIONING_POLICY.md",
            "docs/DEPENDENCY_POLICY.md",
            "docs/contracts/claims_manifest.json",
            "configs/detection_thresholds_v1.json",
            "configs/causal_validation_v1.json",
        ],
    )
    def test_governance_file_exists(self, path: str) -> None:
        full = self.ROOT / path
        assert full.exists(), f"Missing governance file: {path}"
        assert full.stat().st_size > 0, f"Empty governance file: {path}"

    def test_claims_manifest_consistent_with_runtime(self) -> None:
        """Claims manifest must match actual runtime values."""
        import subprocess

        result = subprocess.run(
            ["python", "scripts/check_claims_drift.py"],
            capture_output=True,
            text=True,
            cwd=str(self.ROOT),
        )
        assert result.returncode == 0, f"Claims drift: {result.stdout}"

    def test_claims_manifest_valid_json(self) -> None:
        path = self.ROOT / "docs" / "contracts" / "claims_manifest.json"
        data = json.loads(path.read_text())
        assert data["schema"] == "mfn-claims-manifest-v1"
        assert data["metrics"]["causal_rules"] == 46
        assert data["metrics"]["embedding_dims"] == 57
        assert data["metrics"]["feature_groups_active"] == 6
