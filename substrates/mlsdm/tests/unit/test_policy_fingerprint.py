"""Unit Tests for Policy Fingerprint System (TD-002).

Tests the drift detection system including:
- Canonical JSON serialization
- SHA-256 fingerprinting
- Structured JSON event logging
- Drift detection (fingerprint A vs B)

Resolves: TD-002 (HIGH priority - Policy Drift Guard)

Section 10.3: Drift detection test
- Compute fingerprint A on baseline thresholds
- Modify threshold → fingerprint B
- Assert A != B and drift guard triggers
"""

from __future__ import annotations

import json
import logging

import pytest

from mlsdm.config.policy_drift import PolicyDriftError
from mlsdm.policy.fingerprint import (
    PolicyFingerprintGuard,
    compute_canonical_json,
    compute_fingerprint_hash,
    compute_policy_fingerprint,
    detect_policy_drift,
    emit_policy_fingerprint_event,
)


class TestCanonicalSerialization:
    """Test canonical JSON serialization (Section 10.1)."""

    def test_sorted_keys(self):
        """Keys should be sorted alphabetically."""
        thresholds = {"z_value": 1.0, "a_value": 2.0, "m_value": 3.0}
        canonical = compute_canonical_json(thresholds)

        # Parse and verify order
        assert '"a_value"' in canonical
        assert canonical.index('"a_value"') < canonical.index('"m_value"')
        assert canonical.index('"m_value"') < canonical.index('"z_value"')

    def test_stable_float_formatting(self):
        """Floats should have stable 6-decimal formatting."""
        thresholds = {"value": 0.5}
        canonical = compute_canonical_json(thresholds)

        assert '"0.500000"' in canonical

    def test_no_whitespace(self):
        """Canonical JSON should have no whitespace."""
        thresholds = {"a": 1.0, "b": 2.0}
        canonical = compute_canonical_json(thresholds)

        assert " " not in canonical
        assert "\n" not in canonical
        assert "\t" not in canonical

    def test_nested_dict_sorted(self):
        """Nested dicts should also be sorted."""
        thresholds = {
            "outer_z": {"inner_b": 1.0, "inner_a": 2.0},
            "outer_a": 3.0,
        }
        canonical = compute_canonical_json(thresholds)

        # outer_a should come before outer_z
        assert canonical.index('"outer_a"') < canonical.index('"outer_z"')
        # inner_a should come before inner_b
        assert canonical.index('"inner_a"') < canonical.index('"inner_b"')

    def test_list_values_preserved(self):
        """List values should be serialized correctly."""
        thresholds = {"values": [0.3, 0.5, 0.9]}
        canonical = compute_canonical_json(thresholds)

        # Parse JSON and verify structure rather than exact string matching
        import json
        parsed = json.loads(canonical)
        assert "values" in parsed
        assert parsed["values"] == ["0.300000", "0.500000", "0.900000"]

    def test_deterministic_output(self):
        """Same input should always produce same output."""
        thresholds = {"threshold": 0.5, "min": 0.3, "max": 0.9}

        canonical1 = compute_canonical_json(thresholds)
        canonical2 = compute_canonical_json(thresholds)

        assert canonical1 == canonical2


class TestFingerprintHashing:
    """Test SHA-256 fingerprint hashing."""

    def test_hash_is_sha256_hex(self):
        """Hash should be 64-character hex string (SHA-256)."""
        canonical = '{"threshold":"0.500000"}'
        fingerprint = compute_fingerprint_hash(canonical)

        assert len(fingerprint) == 64
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_same_input_same_hash(self):
        """Same input should produce same hash."""
        canonical = '{"threshold":"0.500000"}'

        hash1 = compute_fingerprint_hash(canonical)
        hash2 = compute_fingerprint_hash(canonical)

        assert hash1 == hash2

    def test_different_input_different_hash(self):
        """Different input should produce different hash."""
        hash1 = compute_fingerprint_hash('{"threshold":"0.500000"}')
        hash2 = compute_fingerprint_hash('{"threshold":"0.600000"}')

        assert hash1 != hash2


class TestPolicyFingerprint:
    """Test PolicyFingerprint computation."""

    def test_compute_fingerprint(self):
        """Should compute fingerprint with all metadata."""
        thresholds = {"threshold": 0.5, "min_threshold": 0.3, "max_threshold": 0.9}

        fingerprint = compute_policy_fingerprint(
            thresholds=thresholds,
            policy_version="1.2.0",
            source_of_truth="src/mlsdm/cognition/moral_filter.py",
        )

        assert fingerprint.fingerprint_sha256
        assert len(fingerprint.fingerprint_sha256) == 64
        assert fingerprint.policy_version == "1.2.0"
        assert fingerprint.source_of_truth == "src/mlsdm/cognition/moral_filter.py"
        assert fingerprint.timestamp_utc
        assert fingerprint.canonical_json

    def test_fingerprint_is_frozen(self):
        """PolicyFingerprint should be immutable."""
        fingerprint = compute_policy_fingerprint(
            thresholds={"threshold": 0.5},
            policy_version="1.0.0",
            source_of_truth="test",
        )

        with pytest.raises(Exception):  # FrozenInstanceError or similar
            fingerprint.fingerprint_sha256 = "modified"  # type: ignore[misc]


class TestStructuredLogging:
    """Test structured JSON logging (Section 10.2)."""

    def test_emit_event_format(self):
        """Emitted event should have required fields."""
        fingerprint = compute_policy_fingerprint(
            thresholds={"threshold": 0.5},
            policy_version="1.2.0",
            source_of_truth="test/module.py",
        )

        event = emit_policy_fingerprint_event(fingerprint)

        assert event["event"] == "POLICY_FINGERPRINT"
        assert event["fingerprint_sha256"] == fingerprint.fingerprint_sha256
        assert event["policy_version"] == "1.2.0"
        assert event["source_of_truth"] == "test/module.py"
        assert "timestamp_utc" in event

    def test_event_logged_as_json(self, caplog):
        """Event should be logged as JSON string."""
        caplog.set_level(logging.INFO)

        fingerprint = compute_policy_fingerprint(
            thresholds={"threshold": 0.5},
            policy_version="1.2.0",
            source_of_truth="test/module.py",
        )

        emit_policy_fingerprint_event(fingerprint)

        # Find the JSON log entry
        json_logs = [r for r in caplog.records if r.message.startswith("{")]
        assert len(json_logs) >= 1

        # Parse and verify it's valid JSON with expected fields
        log_data = json.loads(json_logs[0].message)
        assert log_data["event"] == "POLICY_FINGERPRINT"


class TestDriftDetection:
    """Test drift detection (Section 10.3)."""

    def test_no_drift_same_thresholds(self):
        """Same thresholds should not trigger drift."""
        thresholds = {"threshold": 0.5, "min": 0.3, "max": 0.9}

        baseline = compute_policy_fingerprint(
            thresholds=thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
        )
        current = compute_policy_fingerprint(
            thresholds=thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
        )

        drift_detected, reason = detect_policy_drift(baseline, current)

        assert drift_detected is False
        assert reason is None

    def test_drift_detected_on_threshold_change(self):
        """Modified threshold should trigger drift detection.

        Section 10.3: Drift detection test
        - Compute fingerprint A on baseline thresholds
        - Modify threshold → fingerprint B
        - Assert A != B and drift guard triggers
        """
        baseline_thresholds = {"threshold": 0.5, "min": 0.3, "max": 0.9}
        modified_thresholds = {"threshold": 0.6, "min": 0.3, "max": 0.9}

        fingerprint_a = compute_policy_fingerprint(
            thresholds=baseline_thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
        )
        fingerprint_b = compute_policy_fingerprint(
            thresholds=modified_thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
        )

        # Assert A != B
        assert fingerprint_a.fingerprint_sha256 != fingerprint_b.fingerprint_sha256

        # Assert drift guard triggers
        drift_detected, reason = detect_policy_drift(fingerprint_a, fingerprint_b)
        assert drift_detected is True
        assert reason is not None
        assert "drift" in reason.lower()

    def test_drift_detected_on_any_field_change(self):
        """Any field change should trigger drift."""
        baseline = {"threshold": 0.5, "min": 0.3, "max": 0.9}
        modified_min = {"threshold": 0.5, "min": 0.2, "max": 0.9}  # Only min changed

        fp_baseline = compute_policy_fingerprint(baseline, "1.0.0", "test")
        fp_modified = compute_policy_fingerprint(modified_min, "1.0.0", "test")

        drift_detected, _ = detect_policy_drift(fp_baseline, fp_modified)
        assert drift_detected is True


class TestPolicyFingerprintGuard:
    """Test the PolicyFingerprintGuard class."""

    def test_register_baseline(self):
        """Should register and return baseline fingerprint."""
        guard = PolicyFingerprintGuard()
        thresholds = {"threshold": 0.5, "min": 0.3, "max": 0.9}

        baseline = guard.register_baseline(
            thresholds=thresholds,
            policy_version="1.2.0",
            source_of_truth="test/moral_filter.py",
        )

        assert guard.baseline is not None
        assert guard.baseline.fingerprint_sha256 == baseline.fingerprint_sha256

    def test_check_drift_no_baseline_raises(self):
        """Should raise if no baseline registered."""
        guard = PolicyFingerprintGuard()

        with pytest.raises(ValueError, match="No baseline registered"):
            guard.check_drift(
                thresholds={"threshold": 0.5},
                policy_version="1.0.0",
                source_of_truth="test",
            )

    def test_check_drift_no_change(self):
        """No drift when thresholds unchanged."""
        guard = PolicyFingerprintGuard()
        thresholds = {"threshold": 0.5, "min": 0.3, "max": 0.9}

        guard.register_baseline(
            thresholds=thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
        )

        drift_detected, _ = guard.check_drift(
            thresholds=thresholds,
            policy_version="1.0.0",
            source_of_truth="test",
            enforce=False,
        )

        assert drift_detected is False

    def test_check_drift_raises_on_change(self):
        """Should raise PolicyDriftError when drift detected (enforce=True)."""
        guard = PolicyFingerprintGuard()

        guard.register_baseline(
            thresholds={"threshold": 0.5},
            policy_version="1.0.0",
            source_of_truth="test",
        )

        with pytest.raises(PolicyDriftError, match="drift"):
            guard.check_drift(
                thresholds={"threshold": 0.6},  # Changed!
                policy_version="1.0.0",
                source_of_truth="test",
                enforce=True,
            )

    def test_check_drift_returns_detection_without_enforce(self):
        """Should return drift status when enforce=False."""
        guard = PolicyFingerprintGuard()

        guard.register_baseline(
            thresholds={"threshold": 0.5},
            policy_version="1.0.0",
            source_of_truth="test",
        )

        drift_detected, current = guard.check_drift(
            thresholds={"threshold": 0.6},  # Changed!
            policy_version="1.0.0",
            source_of_truth="test",
            enforce=False,
        )

        assert drift_detected is True
        assert current.fingerprint_sha256 != guard.baseline.fingerprint_sha256  # type: ignore[union-attr]

    def test_update_baseline(self):
        """Should update baseline after authorized change."""
        guard = PolicyFingerprintGuard()

        original = guard.register_baseline(
            thresholds={"threshold": 0.5},
            policy_version="1.0.0",
            source_of_truth="test",
        )

        # Check drift, get new fingerprint
        _, new_fingerprint = guard.check_drift(
            thresholds={"threshold": 0.6},
            policy_version="1.1.0",
            source_of_truth="test",
            enforce=False,
        )

        # Update baseline
        guard.update_baseline(new_fingerprint)

        assert guard.baseline is not None
        assert guard.baseline.fingerprint_sha256 == new_fingerprint.fingerprint_sha256
        assert guard.baseline.fingerprint_sha256 != original.fingerprint_sha256


class TestMoralFilterIntegration:
    """Test integration with MoralFilter thresholds."""

    def test_moral_filter_fingerprint(self):
        """Should compute fingerprint from MoralFilter state."""
        from mlsdm.cognition.moral_filter import MoralFilter

        mf = MoralFilter(
            threshold=0.5,
            adapt_rate=0.05,
            min_threshold=0.3,
            max_threshold=0.9,
        )

        fingerprint = compute_policy_fingerprint(
            thresholds=mf.to_dict(),
            policy_version="1.2.0",
            source_of_truth="src/mlsdm/cognition/moral_filter.py",
        )

        assert fingerprint.fingerprint_sha256
        assert len(fingerprint.fingerprint_sha256) == 64

    def test_moral_filter_drift_detection(self):
        """Drift should be detected when MoralFilter thresholds change."""
        from mlsdm.cognition.moral_filter import MoralFilter

        mf1 = MoralFilter(threshold=0.5)
        mf2 = MoralFilter(threshold=0.6)  # Different threshold

        fp1 = compute_policy_fingerprint(
            thresholds=mf1.to_dict(),
            policy_version="1.0.0",
            source_of_truth="test",
        )
        fp2 = compute_policy_fingerprint(
            thresholds=mf2.to_dict(),
            policy_version="1.0.0",
            source_of_truth="test",
        )

        drift_detected, _ = detect_policy_drift(fp1, fp2)
        assert drift_detected is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
