"""Unit Tests for Policy Drift Detection.

Tests the drift detection system for MoralFilterV2 including:
- Metric recording on threshold changes
- Critical drift logging (>10%)
- Sustained drift detection (>15% over 10 operations)
- Drift statistics accuracy
"""

import logging
from unittest.mock import patch

import pytest

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.observability.policy_drift_telemetry import (
    moral_threshold_drift_rate,
    record_threshold_change,
)


class TestPolicyDriftDetection:
    """Test policy drift detection functionality."""

    def test_records_drift_on_threshold_change(self):
        """Drift is recorded when threshold changes."""
        with patch(
            "mlsdm.cognition.moral_filter_v2.record_threshold_change"
        ) as mock_record:
            mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

            # Reset call count from __init__
            mock_record.reset_mock()

            # Force threshold change by setting high EMA
            mf.ema_accept_rate = 0.7  # High acceptance
            mf.adapt(accepted=True)

            # Should record drift if threshold changed
            # Check if called (threshold may or may not change depending on error)
            # Let's force a change by directly manipulating
            old_threshold = 0.5
            new_threshold = 0.55
            mf._record_drift(old_threshold, new_threshold)

            # Should record drift
            assert mock_record.call_count >= 1

    def test_logs_critical_drift(self, caplog):
        """Critical drift (>10%) is logged."""
        caplog.set_level(logging.ERROR)

        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Simulate large drift
        old = 0.5
        new = 0.65  # +15% drift (0.15)
        mf._record_drift(old, new)

        # Check log
        assert "CRITICAL DRIFT" in caplog.text
        assert "0.150" in caplog.text

    def test_logs_warning_drift(self, caplog):
        """Warning drift (>5%, <10%) is logged."""
        caplog.set_level(logging.WARNING)

        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Simulate moderate drift
        old = 0.5
        new = 0.58  # +8% drift (0.08)
        mf._record_drift(old, new)

        # Check log
        assert "Significant drift" in caplog.text
        assert "0.080" in caplog.text

    def test_detects_sustained_drift(self, caplog):
        """Sustained drift over multiple operations detected."""
        caplog.set_level(logging.ERROR)

        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Simulate gradual drift by calling _record_drift multiple times
        # Start with 9 items in history
        for i in range(9):
            threshold = 0.5 + (i * 0.015)  # Gradual increase
            mf._drift_history.append(threshold)

        # Now record drift that should trigger sustained drift detection
        # History will have 10 items total after this call
        # Drift from first to last: 0.5 to (0.5 + 10*0.015) = 0.5 to 0.65 = 0.15
        old_val = 0.5 + (9 * 0.015)
        new_val = 0.5 + (10 * 0.015)
        mf._record_drift(old_val, new_val)

        # Should detect sustained drift (0.15 difference over 10 operations)
        assert "SUSTAINED DRIFT" in caplog.text

    def test_drift_stats_accurate(self):
        """get_drift_stats returns accurate data."""
        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Add drift history
        mf._drift_history = [0.5, 0.52, 0.54, 0.53, 0.51]
        mf.threshold = 0.51
        mf.ema_accept_rate = 0.48

        stats = mf.get_drift_stats()

        assert stats["total_changes"] == 5
        assert stats["drift_range"] == pytest.approx(0.04)
        assert stats["min_threshold"] == 0.5
        assert stats["max_threshold"] == 0.54
        assert stats["current_threshold"] == 0.51
        assert stats["ema_acceptance"] == 0.48

    def test_drift_stats_empty_history(self):
        """get_drift_stats returns correct data with no history."""
        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Clear history
        mf._drift_history = []

        stats = mf.get_drift_stats()

        assert stats["total_changes"] == 0
        assert stats["drift_range"] == 0.0
        assert stats["current_threshold"] == 0.5

    def test_no_drift_on_stable_threshold(self, caplog):
        """No drift logged when threshold stable."""
        caplog.set_level(logging.WARNING)

        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Simulate no change (drift magnitude = 0)
        mf._record_drift(0.5, 0.5)

        # Should not log any drift warnings (checking for any log records)
        # When drift is 0, no warning or error should be logged
        drift_logs = [
            record
            for record in caplog.records
            if "drift" in record.message.lower()
            and record.levelname in ("WARNING", "ERROR")
        ]
        assert len(drift_logs) == 0, f"Expected no drift logs, but found: {drift_logs}"

    def test_filter_id_passed_to_metrics(self):
        """Filter ID is correctly passed to metrics."""
        with patch(
            "mlsdm.cognition.moral_filter_v2.record_threshold_change"
        ) as mock_record:
            _mf = MoralFilterV2(initial_threshold=0.5, filter_id="production-filter")

            # Check that __init__ called record_threshold_change with correct filter_id
            mock_record.assert_called()
            call_args = mock_record.call_args
            assert call_args.kwargs["filter_id"] == "production-filter"

    def test_drift_history_max_size(self):
        """Drift history respects max size limit."""
        mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

        # Add items via _record_drift to test the trimming logic
        for i in range(150):
            old_val = 0.5 + (i - 1) * 0.001 if i > 0 else 0.5
            new_val = 0.5 + i * 0.001
            mf._record_drift(old_val, new_val)

        # Should be capped at max_history
        assert len(mf._drift_history) <= mf._max_history
        assert len(mf._drift_history) == mf._max_history

    def test_adapt_triggers_drift_recording(self):
        """adapt() method triggers drift recording when threshold changes."""
        with patch.object(MoralFilterV2, "_record_drift") as mock_drift:
            mf = MoralFilterV2(initial_threshold=0.5, filter_id="test")

            # Set up conditions that will cause threshold change
            # Need to move EMA far enough from 0.5 to trigger adaptation
            for _ in range(20):
                mf.adapt(accepted=True)

            # Should have called _record_drift at least once
            assert mock_drift.call_count > 0

    def test_metrics_recorded_on_init(self):
        """Metrics are recorded during initialization."""
        with patch(
            "mlsdm.cognition.moral_filter_v2.record_threshold_change"
        ) as mock_record:
            _mf = MoralFilterV2(initial_threshold=0.6, filter_id="init-test")

            # Should have been called once in __init__
            assert mock_record.call_count == 1
            call_args = mock_record.call_args
            assert call_args.kwargs["filter_id"] == "init-test"
            assert call_args.kwargs["new_threshold"] == 0.6
            assert call_args.kwargs["old_threshold"] == 0.6
            assert call_args.kwargs["ema_value"] == 0.5

    def test_drift_rate_metric_set(self):
        """Drift rate metric is calculated."""
        record_threshold_change(
            filter_id="drift-rate-test",
            old_threshold=0.4,
            new_threshold=0.55,
            ema_value=0.5,
        )

        samples = moral_threshold_drift_rate.collect()[0].samples
        value = next(
            (s.value for s in samples if s.labels.get("filter_id") == "drift-rate-test"),
            None,
        )

        assert value is not None
        assert value == pytest.approx(0.15)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
