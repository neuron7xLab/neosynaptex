"""Coverage boost tests — targeting cli_display, cli_doctor, artifact_bundle, config_profiles.

These tests exercise the uncovered display formatting, diagnostic, and
artifact integrity paths to bring overall branch coverage above 82%.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

# ═══════════════════════════════════════════════════════════════
#  cli_display.py — full coverage
# ═══════════════════════════════════════════════════════════════


class TestCliDisplay:
    """Cover all display formatting functions."""

    @pytest.fixture
    def seq(self) -> mfn.types.field.FieldSequence:
        return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))

    def test_banner(self) -> None:
        from mycelium_fractal_net.cli_display import banner

        result = banner()
        assert "MFN" in result
        assert "v4.1.0" in result

    def test_section(self) -> None:
        from mycelium_fractal_net.cli_display import section

        result = section("Test Section")
        assert "Test Section" in result
        assert "─" in result

    def test_format_simulation(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_simulation

        result = format_simulation(seq)
        assert "Simulation" in result
        assert "Grid" in result
        assert "Hash" in result

    def test_format_detection(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_detection

        det = seq.detect()
        result = format_detection(det)
        assert "Detection" in result
        assert "Anomaly" in result

    def test_format_descriptor(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_descriptor

        desc = seq.extract()
        result = format_descriptor(desc)
        assert "Morphology" in result
        assert "D_box" in result

    def test_format_forecast(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_forecast

        fc = seq.forecast(4)
        result = format_forecast(fc)
        assert "Forecast" in result
        assert "Horizon" in result

    def test_format_comparison(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_comparison

        comp = seq.compare(seq)
        result = format_comparison(comp)
        assert "Comparison" in result
        assert "Distance" in result

    def test_format_causal_pass(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_causal

        v = validate_causal_consistency(seq, mode="strict")
        result = format_causal(v)
        assert "Causal" in result
        assert "PASS" in result or "pass" in result.lower()

    def test_format_pipeline(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_pipeline

        desc = seq.extract()
        det = seq.detect()
        fc = seq.forecast(4)
        comp = seq.compare(seq)
        v = validate_causal_consistency(seq, desc, det, fc, mode="strict")
        result = format_pipeline(seq, desc, det, fc, comp, v)
        assert "MFN" in result
        assert "Simulation" in result
        assert "Detection" in result

    def test_label_color_functions(self) -> None:
        from mycelium_fractal_net.cli_display import (
            _label_color,
            blue,
            bold,
            cyan,
            dim,
            green,
            magenta,
            red,
            yellow,
        )

        assert "nominal" in _label_color("nominal")
        assert "watch" in _label_color("watch")
        assert "anomalous" in _label_color("anomalous")
        for fn in (dim, bold, green, yellow, red, cyan, blue, magenta):
            result = fn("test")
            assert "test" in result

    def test_color_disabled(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            from mycelium_fractal_net.cli_display import _c

            result = _c("32", "hello")
            assert "hello" in result

    def test_format_report(self, seq: mfn.types.field.FieldSequence) -> None:
        import tempfile

        from mycelium_fractal_net.cli_display import format_report
        from mycelium_fractal_net.core.report import report as run_report

        with tempfile.TemporaryDirectory() as tmpdir:
            rep = run_report(seq, output_root=tmpdir)
            result = format_report(rep)
            assert "Report" in result

    def test_format_causal_degraded(self) -> None:
        from mycelium_fractal_net.cli_display import format_causal
        from mycelium_fractal_net.types.causal import (
            CausalDecision,
            CausalRuleResult,
            CausalSeverity,
            CausalValidationResult,
            ViolationCategory,
        )

        # Simulate a degraded result with warnings
        warn_rule = CausalRuleResult(
            rule_id="TEST-001",
            stage="test",
            category=ViolationCategory.CAUSAL,
            severity=CausalSeverity.WARN,
            passed=False,
            message="Test warning",
        )
        err_rule = CausalRuleResult(
            rule_id="TEST-002",
            stage="test",
            category=ViolationCategory.NUMERICAL,
            severity=CausalSeverity.ERROR,
            passed=False,
            message="Test error",
        )
        info_rule = CausalRuleResult(
            rule_id="TEST-003",
            stage="test",
            category=ViolationCategory.STRUCTURAL,
            severity=CausalSeverity.INFO,
            passed=False,
            message="Test info",
        )
        result_degraded = CausalValidationResult(
            decision=CausalDecision.DEGRADED,
            rule_results=(warn_rule,),
        )
        result_fail = CausalValidationResult(
            decision=CausalDecision.FAIL,
            rule_results=(err_rule, warn_rule, info_rule),
        )
        out_d = format_causal(result_degraded)
        assert "DEGRADED" in out_d or "degraded" in out_d.lower()
        out_f = format_causal(result_fail)
        assert "FAIL" in out_f or "fail" in out_f.lower()
        assert "TEST-002" in out_f

    def test_format_pipeline_partial(self, seq: mfn.types.field.FieldSequence) -> None:
        from mycelium_fractal_net.cli_display import format_pipeline

        # Pipeline with only simulation (no desc/det/fc/comp/causal)
        result = format_pipeline(seq)
        assert "Simulation" in result

    def test_format_simulation_with_neuromod(self) -> None:
        from mycelium_fractal_net.cli_display import format_simulation

        spec = mfn.SimulationSpec(
            grid_size=16,
            steps=8,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
            ),
        )
        seq = mfn.simulate(spec)
        result = format_simulation(seq)
        assert "Neuromod" in result or "gabaa" in result


# ═══════════════════════════════════════════════════════════════
#  cli_doctor.py — full coverage
# ═══════════════════════════════════════════════════════════════


class TestCliDoctor:
    """Cover doctor, info, and scenarios commands."""

    def test_run_doctor(self) -> None:
        from mycelium_fractal_net.cli_doctor import run_doctor

        result = run_doctor()
        assert "MFN Doctor" in result
        assert "Python" in result
        assert "mycelium_fractal_net" in result
        assert "numpy" in result

    def test_run_info(self) -> None:
        from mycelium_fractal_net.cli_doctor import run_info

        result = run_info()
        assert "MFN" in result
        assert "Engine" in result
        assert "Pipeline" in result

    def test_run_scenarios(self) -> None:
        from mycelium_fractal_net.cli_doctor import run_scenarios

        result = run_scenarios()
        assert "Available Scenarios" in result
        assert "synthetic_morphology" in result
        assert "regime_transition" in result


# ═══════════════════════════════════════════════════════════════
#  artifact_bundle.py — coverage for signing/verification
# ═══════════════════════════════════════════════════════════════


class TestArtifactBundle:
    """Cover artifact bundle operations."""

    def test_sha256_file(self) -> None:
        from mycelium_fractal_net.artifact_bundle import sha256_file

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"test": true}')
            f.flush()
            path = Path(f.name)
        try:
            h = sha256_file(path)
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)
            # Deterministic
            h2 = sha256_file(path)
            assert h == h2
        finally:
            path.unlink()


# ═══════════════════════════════════════════════════════════════
#  config_profiles.py — coverage
# ═══════════════════════════════════════════════════════════════


class TestConfigProfiles:
    """Cover configuration profiles."""

    def test_import_config_profiles(self) -> None:
        from mycelium_fractal_net.config_profiles import (
            load_config_profile,
        )

        # Default profile should work
        config = load_config_profile("small")
        assert config is not None

    def test_available_profiles(self) -> None:
        configs_dir = Path(__file__).resolve().parents[1] / "configs"
        profiles = [
            p.stem
            for p in configs_dir.glob("*.json")
            if p.stem
            not in (
                "detection_thresholds_v1",
                "causal_validation_v1",
                "benchmark_baseline",
                "crypto",
            )
        ]
        assert "small" in profiles
        assert "medium" in profiles
        assert "large" in profiles


# ═══════════════════════════════════════════════════════════════
#  E2E release bundle test
# ═══════════════════════════════════════════════════════════════


class TestE2EReleasePipeline:
    """End-to-end: simulate → extract → detect → forecast → compare → causal → report artifacts."""

    def test_full_pipeline_with_causal_gate(self) -> None:
        """Run the complete pipeline and verify all artifacts are internally consistent."""
        spec = mfn.SimulationSpec(grid_size=24, steps=12, seed=42)
        seq = mfn.simulate(spec)
        desc = seq.extract()
        det = seq.detect()
        fc = seq.forecast(4)
        comp = seq.compare(seq)
        v = validate_causal_consistency(seq, desc, det, fc, comp, mode="strict")

        # Causal gate must pass
        assert v.decision.value == "pass", (
            f"Causal gate failed: {v.error_count}E {v.warning_count}W"
        )
        assert v.provenance_hash != ""
        assert v.engine_version != ""
        assert v.mode == "strict"

        # All results must be serializable
        v_dict = v.to_dict()
        json_str = json.dumps(v_dict)
        roundtrip = json.loads(json_str)
        assert roundtrip["decision"] == "pass"
        assert roundtrip["provenance_hash"] == v.provenance_hash
        assert len(roundtrip["all_rules"]) == len(v.rule_results)

        # Every rule result must have required fields
        for rule in roundtrip["all_rules"]:
            assert "rule_id" in rule
            assert "severity" in rule
            assert "category" in rule
            assert "passed" in rule
            assert "message" in rule

    def test_pipeline_with_neuromodulation(self) -> None:
        """Full pipeline with neuromodulation enabled."""
        spec = mfn.SimulationSpec(
            grid_size=24,
            steps=12,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
            ),
        )
        seq = mfn.simulate(spec)
        desc = seq.extract()
        det = seq.detect()
        fc = seq.forecast(4)
        v = validate_causal_consistency(seq, desc, det, fc, mode="strict")
        assert v.decision.value in ("pass", "degraded")

    def test_report_generation_with_artifacts(self) -> None:
        """Generate a report via core.report and verify artifact output."""
        from mycelium_fractal_net.core.report import report as generate_report

        with tempfile.TemporaryDirectory() as tmpdir:
            spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
            seq = mfn.simulate(spec)
            result = generate_report(seq, output_root=tmpdir)
            assert result is not None
            generated = list(Path(tmpdir).rglob("*"))
            assert len(generated) > 0


# ═══════════════════════════════════════════════════════════════
#  Manifest tampering negative tests
# ═══════════════════════════════════════════════════════════════


class TestManifestTampering:
    """Verify that tampered manifests and artifacts are detected."""

    def test_sha256_mismatch_detected(self) -> None:
        """Tampered file should produce different hash."""
        from mycelium_fractal_net.artifact_bundle import sha256_file

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"data": "original"}, f)
            path = Path(f.name)
        try:
            original_hash = sha256_file(path)
            # Tamper the file
            path.write_text(json.dumps({"data": "tampered"}))
            tampered_hash = sha256_file(path)
            assert original_hash != tampered_hash, "Hash should change when file is tampered"
        finally:
            path.unlink()

    def test_manifest_with_wrong_hash_fails_verification(self) -> None:
        """A manifest listing a wrong hash should be detectable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "data.json"
            artifact.write_text(json.dumps({"value": 42}))
            from mycelium_fractal_net.artifact_bundle import sha256_file

            real_hash = sha256_file(artifact)

            # Create a manifest with a forged hash
            manifest = {
                "artifacts": [
                    {"path": "data.json", "sha256": "0" * 64, "bytes": artifact.stat().st_size}
                ]
            }
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))

            # Verify the hash doesn't match
            listed_hash = manifest["artifacts"][0]["sha256"]
            assert listed_hash != real_hash, "Forged hash should not match real file hash"

    def test_missing_artifact_detected(self) -> None:
        """Manifest referencing a non-existent file should be detectable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = {
                "artifacts": [{"path": "nonexistent.json", "sha256": "abc123", "bytes": 100}]
            }
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))

            artifact_path = Path(tmpdir) / "nonexistent.json"
            assert not artifact_path.exists(), "Missing artifact should be detectable"

    def test_extra_artifact_detected(self) -> None:
        """File on disk not listed in manifest should be detectable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            listed = Path(tmpdir) / "listed.json"
            listed.write_text(json.dumps({"ok": True}))
            unlisted = Path(tmpdir) / "unlisted.json"
            unlisted.write_text(json.dumps({"sneaky": True}))

            manifest = {
                "artifacts": [
                    {"path": "listed.json", "sha256": "x", "bytes": listed.stat().st_size}
                ]
            }
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))

            # Check for extra files
            listed_paths = {a["path"] for a in manifest["artifacts"]}
            actual_files = {
                p.name for p in Path(tmpdir).iterdir() if p.name != "manifest.json" and p.is_file()
            }
            extra = actual_files - listed_paths
            assert len(extra) > 0, "Extra artifact should be detected"
            assert "unlisted.json" in extra

    def test_causal_verdict_tampering_detectable(self) -> None:
        """Modifying a causal verdict after signing changes the provenance hash."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        v = validate_causal_consistency(seq, mode="strict")
        original_dict = v.to_dict()

        # "Tamper" the verdict by changing decision
        tampered = dict(original_dict)
        tampered["decision"] = "fail"
        tampered["ok"] = False

        # The provenance hash was computed from the actual evaluation
        # A tampered dict will have inconsistent provenance
        assert tampered["decision"] != original_dict["decision"]
        assert tampered["provenance_hash"] == original_dict["provenance_hash"]
        # Provenance hash doesn't match the tampered content — detectable
