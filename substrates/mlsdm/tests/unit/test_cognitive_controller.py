"""
Unit Tests for Cognitive Controller

Tests memory monitoring, processing time limits, and emergency shutdown functionality.
"""

import gc

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController


class TestCognitiveControllerInitialization:
    """Test cognitive controller initialization."""

    def test_default_initialization(self):
        """Test controller can be initialized with defaults."""
        controller = CognitiveController()
        assert controller.dim == 384
        assert controller.memory_threshold_mb == 8192.0
        assert controller.max_processing_time_ms == 1000.0
        assert controller.emergency_shutdown is False
        assert controller.step_counter == 0

    def test_custom_initialization(self):
        """Test controller can be initialized with custom values."""
        controller = CognitiveController(
            dim=128, memory_threshold_mb=512.0, max_processing_time_ms=500.0
        )
        assert controller.dim == 128
        assert controller.memory_threshold_mb == 512.0
        assert controller.max_processing_time_ms == 500.0
        assert controller.emergency_shutdown is False


class TestCognitiveControllerMemoryMonitoring:
    """Test memory monitoring functionality."""

    def test_get_memory_usage(self):
        """Test memory usage can be retrieved."""
        controller = CognitiveController()
        memory_mb = controller.get_memory_usage()
        assert isinstance(memory_mb, float)
        assert memory_mb > 0, "Memory usage should be positive"
        # Sanity check: memory usage should be reasonable (< 10GB for this test)
        assert memory_mb < 10240, f"Memory usage seems unreasonable: {memory_mb} MB"

    def test_memory_threshold_exceeded_triggers_emergency_shutdown(self):
        """Test emergency shutdown is triggered when memory threshold is exceeded."""
        # Set a very low threshold to trigger emergency shutdown
        controller = CognitiveController(memory_threshold_mb=0.001)

        vector = np.random.randn(384).astype(np.float32)
        result = controller.process_event(vector, moral_value=0.8)

        assert controller.emergency_shutdown is True
        assert result["rejected"] is True
        assert "emergency shutdown" in result["note"]

    def test_emergency_shutdown_blocks_further_processing(self):
        """Test that once emergency shutdown is triggered, no further events are processed."""
        controller = CognitiveController(memory_threshold_mb=0.001)

        vector = np.random.randn(384).astype(np.float32)

        # First event triggers emergency shutdown
        result1 = controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert result1["rejected"] is True

        # Second event should be rejected immediately
        result2 = controller.process_event(vector, moral_value=0.8)
        assert result2["rejected"] is True
        assert result2["note"] == "emergency shutdown"

    def test_reset_emergency_shutdown(self):
        """Test emergency shutdown can be reset."""
        controller = CognitiveController(memory_threshold_mb=0.001)

        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency shutdown
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Reset emergency shutdown
        controller.reset_emergency_shutdown()
        assert controller.emergency_shutdown is False


class TestCognitiveControllerProcessingTime:
    """Test processing time limits."""

    def test_normal_processing_time(self):
        """Test events process within normal time limits."""
        # Use a reasonable time limit
        controller = CognitiveController(max_processing_time_ms=5000.0)

        vector = np.random.randn(384).astype(np.float32)
        result = controller.process_event(vector, moral_value=0.8)

        # Event should be processed normally (not rejected for time)
        if result["rejected"]:
            # Could be rejected for other reasons (sleep phase, moral)
            assert "processing time exceeded" not in result["note"]


class TestCognitiveControllerProcessEvent:
    """Test event processing functionality."""

    def test_process_accepted_event(self):
        """Test processing of an accepted event."""
        controller = CognitiveController()
        vector = np.random.randn(384).astype(np.float32)

        result = controller.process_event(vector, moral_value=0.8)

        assert isinstance(result, dict)
        assert "step" in result
        assert "rejected" in result
        assert "note" in result
        assert controller.step_counter > 0

    def test_process_rejected_moral_event(self):
        """Test processing of morally rejected event."""
        controller = CognitiveController()
        vector = np.random.randn(384).astype(np.float32)

        # Use low moral value to trigger rejection
        result = controller.process_event(vector, moral_value=0.1)

        assert result["rejected"] is True
        assert "morally rejected" in result["note"]

    def test_step_counter_increments(self):
        """Test step counter increments with each event."""
        controller = CognitiveController()
        vector = np.random.randn(384).astype(np.float32)

        initial_count = controller.step_counter
        controller.process_event(vector, moral_value=0.8)
        assert controller.step_counter == initial_count + 1

        controller.process_event(vector, moral_value=0.8)
        assert controller.step_counter == initial_count + 2


class TestCognitiveControllerMemoryLeak:
    """Test memory leak detection with high volume of events."""

    @pytest.mark.slow
    def test_no_memory_leak_10k_events(self):
        """Test that processing 10k events doesn't cause excessive memory growth."""
        controller = CognitiveController()

        # Get initial memory usage
        gc.collect()  # Force garbage collection before measuring
        initial_memory = controller.get_memory_usage()

        # Process 10k events
        num_events = 10_000
        for i in range(num_events):
            vector = np.random.randn(384).astype(np.float32)
            moral_value = 0.5 + (i % 10) * 0.05  # Vary moral values
            controller.process_event(vector, moral_value)

            # Periodically force garbage collection
            if i % 1000 == 0:
                gc.collect()

        # Force final garbage collection
        gc.collect()
        final_memory = controller.get_memory_usage()

        memory_growth = final_memory - initial_memory

        # Assert memory growth is reasonable (< 500 MB for 10k events)
        # This is a soft check - some growth is expected due to data structures
        assert memory_growth < 500, (
            f"Potential memory leak detected: memory grew by {memory_growth:.2f} MB "
            f"after processing {num_events} events. "
            f"Initial: {initial_memory:.2f} MB, Final: {final_memory:.2f} MB"
        )

        # Verify controller is still functional after high load
        vector = np.random.randn(384).astype(np.float32)
        result = controller.process_event(vector, moral_value=0.8)
        assert isinstance(result, dict)
        assert controller.step_counter == num_events + 1

    @pytest.mark.slow
    def test_memory_stays_stable_over_time(self):
        """Test memory usage stabilizes and doesn't continuously grow."""
        controller = CognitiveController()

        gc.collect()

        memory_samples = []

        # Process events in batches and measure memory
        for _ in range(5):
            for _ in range(1000):
                vector = np.random.randn(384).astype(np.float32)
                controller.process_event(vector, moral_value=0.7)

            gc.collect()
            memory_samples.append(controller.get_memory_usage())

        # Check that memory doesn't continuously grow between batches
        # Allow for initial growth but later samples should stabilize
        if len(memory_samples) >= 3:
            # Compare last 2 samples with first sample
            initial_growth = memory_samples[1] - memory_samples[0]
            later_growth = memory_samples[-1] - memory_samples[-2]

            # Define noise tolerance (0.5 MB) for RSS measurement fluctuations
            # RSS can vary due to allocator behavior, not actual leaks
            noise_tolerance_mb = 0.5

            # Later growth should be less than or similar to initial growth
            # This indicates stabilization rather than continuous leak
            # Allow small noise within tolerance even if initial_growth is near zero
            assert later_growth <= max(initial_growth * 2, noise_tolerance_mb), (
                f"Memory continues to grow significantly beyond allocator noise: "
                f"initial growth: {initial_growth:.2f} MB, "
                f"later growth: {later_growth:.2f} MB, "
                f"tolerance: {noise_tolerance_mb:.2f} MB. "
                f"Note: Small differences (<{noise_tolerance_mb} MB) are normal allocator fluctuations, "
                f"but sustained growth of hundreds of MB would indicate a real leak."
            )


class TestCognitiveControllerRetrieveContext:
    """Test context retrieval functionality."""

    def test_retrieve_context(self):
        """Test context retrieval works."""
        controller = CognitiveController()

        # Add some events first
        for _ in range(10):
            vector = np.random.randn(384).astype(np.float32)
            controller.process_event(vector, moral_value=0.8)

        # Retrieve context
        query = np.random.randn(384).astype(np.float32)
        results = controller.retrieve_context(query, top_k=5)

        assert isinstance(results, list)
        assert len(results) <= 5


class TestCognitiveControllerAutoRecovery:
    """Test health-based auto-recovery after emergency shutdown."""

    def test_normal_to_emergency_to_recovery_to_normal(self):
        """Test full cycle: Normal → Emergency → Recovery → Normal.

        This verifies that after emergency shutdown:
        1. Controller stays in emergency mode during cooldown
        2. Auto-recovery succeeds after cooldown with healthy conditions
        3. Controller continues normal operation after recovery
        """
        # Use low memory threshold to trigger emergency shutdown easily
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Step 1: Trigger emergency shutdown
        result = controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert result["rejected"] is True
        assert "emergency shutdown" in result["note"]
        initial_emergency_step = controller._last_emergency_step
        initial_recovery_attempts = controller._recovery_attempts

        # Verify internal state was updated
        assert initial_emergency_step == 1  # First event triggers shutdown
        assert initial_recovery_attempts == 1

        # Step 2: Simulate passing of cooldown period by incrementing step_counter
        # We need to increase memory_threshold_mb to allow recovery
        controller.memory_threshold_mb = 10000.0  # Reset to safe threshold

        # Import calibration to get actual cooldown value
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        # Manually increment step counter to simulate cooldown
        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS

        # Step 3: Attempt recovery by processing another event
        result = controller.process_event(vector, moral_value=0.8)

        # Verify auto-recovery succeeded
        assert controller.emergency_shutdown is False, "Emergency should be cleared after recovery"
        # After recovery, the event should be processed normally (or rejected for other reasons)
        # Note: could be rejected due to sleep phase or moral filter
        assert result is not None

        # Step 4: Verify controller continues normal operation
        result2 = controller.process_event(vector, moral_value=0.8)
        assert result2 is not None
        assert controller.step_counter > initial_emergency_step

    def test_recovery_does_not_trigger_without_cooldown(self):
        """Test that recovery does not happen if cooldown period has not passed."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency shutdown
        result1 = controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert result1["rejected"] is True

        # Increase threshold but don't wait for cooldown
        controller.memory_threshold_mb = 10000.0

        # Try to process another event immediately (no cooldown passed)
        # Note: step_counter hasn't increased enough yet
        result2 = controller.process_event(vector, moral_value=0.8)

        # Should still be in emergency shutdown (cooldown not passed)
        assert controller.emergency_shutdown is True
        assert result2["rejected"] is True
        assert result2["note"] == "emergency shutdown"

    def test_recovery_does_not_trigger_with_high_memory(self):
        """Test that recovery does not happen if memory is still high."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency shutdown
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Import calibration values
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        # Simulate cooldown period
        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS

        # Keep memory threshold very low (memory will still exceed threshold)
        # Process another event - should remain in emergency
        result = controller.process_event(vector, moral_value=0.8)

        assert controller.emergency_shutdown is True
        assert result["rejected"] is True
        assert result["note"] == "emergency shutdown"

    def test_no_state_leak_after_recovery(self):
        """Test that recovery doesn't create memory/state leaks.

        After Normal → Emergency → Recovery → Normal cycle:
        - No duplicate state objects
        - Counters don't increase uncontrollably
        - Buffer sizes remain reasonable
        """
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        initial_pelm_used = controller.pelm.get_state_stats()["used"]

        # Recover by adjusting threshold and passing cooldown
        controller.memory_threshold_mb = 10000.0
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS

        # Process recovery event
        controller.process_event(vector, moral_value=0.8)

        # Continue with several more events
        for _ in range(10):
            controller.process_event(vector, moral_value=0.8)

        # Check state is reasonable
        final_pelm_used = controller.pelm.get_state_stats()["used"]
        l1, l2, l3 = controller.synaptic.state()

        # Memory structures should have bounded growth
        # initial_pelm_used could be 0 or 1 depending on timing
        assert final_pelm_used <= initial_pelm_used + 15  # At most ~11 new entries

        # Norms should be finite
        assert np.isfinite(np.linalg.norm(l1))
        assert np.isfinite(np.linalg.norm(l2))
        assert np.isfinite(np.linalg.norm(l3))

        # Recovery attempts should not grow beyond initial attempt
        assert controller._recovery_attempts == 1

    def test_recovery_guard_against_infinite_loop(self):
        """Test that controller stops auto-recovery after max attempts.

        After exceeding max recovery attempts:
        - Controller should stay in emergency
        - No more auto-recovery attempts should succeed
        """
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        from mlsdm.core.cognitive_controller import (
            _CC_RECOVERY_COOLDOWN_STEPS,
            _CC_RECOVERY_MAX_ATTEMPTS,
        )

        # Perform multiple emergency → recovery cycles up to max attempts
        for attempt in range(_CC_RECOVERY_MAX_ATTEMPTS):
            # Trigger emergency
            controller.process_event(vector, moral_value=0.8)
            assert controller.emergency_shutdown is True
            assert controller._recovery_attempts == attempt + 1

            # Simulate cooldown and fix memory threshold
            controller.memory_threshold_mb = 10000.0
            controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS

            # Attempt recovery
            controller.process_event(vector, moral_value=0.8)

            # Recovery should succeed if under max attempts
            if attempt < _CC_RECOVERY_MAX_ATTEMPTS - 1:
                assert controller.emergency_shutdown is False
                # Re-trigger emergency with low threshold for next iteration
                controller.memory_threshold_mb = 0.001

        # At this point, we've hit max attempts and recovery should have failed on last attempt
        # Controller is still in emergency because recovery failed when attempts == max_attempts
        assert controller.emergency_shutdown is True
        assert controller._recovery_attempts == _CC_RECOVERY_MAX_ATTEMPTS

        # Try recovery again after more cooldown - should still fail
        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS
        result = controller.process_event(vector, moral_value=0.8)

        # Recovery should NOT succeed - max attempts exceeded
        assert controller.emergency_shutdown is True
        assert result["rejected"] is True
        assert result["note"] == "emergency shutdown"

    def test_manual_reset_enables_auto_recovery_again(self):
        """Test that manual reset clears recovery attempts, enabling auto-recovery again."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        from mlsdm.core.cognitive_controller import _CC_RECOVERY_MAX_ATTEMPTS

        # Exhaust all recovery attempts
        for _ in range(_CC_RECOVERY_MAX_ATTEMPTS + 2):
            controller.process_event(vector, moral_value=0.8)
            controller.memory_threshold_mb = 10000.0
            controller.step_counter += 20
            controller.process_event(vector, moral_value=0.8)
            controller.memory_threshold_mb = 0.001

        assert controller._recovery_attempts >= _CC_RECOVERY_MAX_ATTEMPTS

        # Manual reset
        controller.reset_emergency_shutdown()

        # Verify reset cleared both flags
        assert controller.emergency_shutdown is False
        assert controller._recovery_attempts == 0

        # Trigger emergency again
        controller.memory_threshold_mb = 0.001
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert controller._recovery_attempts == 1  # Reset counter

        # Auto-recovery should work again
        controller.memory_threshold_mb = 10000.0
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS
        controller.process_event(vector, moral_value=0.8)

        assert controller.emergency_shutdown is False

    def test_internal_state_tracking_accuracy(self):
        """Test that _last_emergency_step and _recovery_attempts are tracked correctly."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Initially, tracking fields should be at defaults
        assert controller._last_emergency_step == 0
        assert controller._recovery_attempts == 0

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)

        # Verify tracking updated
        assert controller._last_emergency_step == controller.step_counter
        assert controller._recovery_attempts == 1

        # Trigger another emergency (if we can recover first)
        controller.memory_threshold_mb = 10000.0
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS
        controller.process_event(vector, moral_value=0.8)  # Should recover

        controller.memory_threshold_mb = 0.001
        controller.process_event(vector, moral_value=0.8)  # Trigger again

        # Recovery attempts should increment
        assert controller._recovery_attempts == 2
        assert controller._last_emergency_step == controller.step_counter


class TestCognitiveControllerTimeBasedRecovery:
    """Test time-based auto-recovery after emergency shutdown (REL-001)."""

    def test_time_based_recovery_default_enabled(self):
        """Test that time-based recovery is enabled by default."""
        controller = CognitiveController()
        assert controller.auto_recovery_enabled is True
        assert controller.auto_recovery_cooldown_seconds == 60.0

    def test_time_based_recovery_can_be_disabled(self):
        """Test that time-based recovery can be disabled."""
        controller = CognitiveController(auto_recovery_enabled=False)
        assert controller.auto_recovery_enabled is False

    def test_time_based_recovery_custom_cooldown(self):
        """Test custom cooldown duration."""
        controller = CognitiveController(auto_recovery_cooldown_seconds=120.0)
        assert controller.auto_recovery_cooldown_seconds == 120.0

    def test_emergency_records_time(self):
        """Test that emergency shutdown records the time."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Initially, no emergency time
        assert controller._last_emergency_time == 0.0

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert controller._last_emergency_time > 0

    def test_time_based_recovery_after_cooldown(self):
        """Test recovery after time-based cooldown passes."""
        # Use short cooldown for testing
        controller = CognitiveController(
            memory_threshold_mb=0.001,
            auto_recovery_enabled=True,
            auto_recovery_cooldown_seconds=0.1,  # 100ms cooldown
        )
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Increase memory threshold to allow recovery
        controller.memory_threshold_mb = 10000.0

        # Simulate time-based cooldown passage without sleeping
        controller._last_emergency_time -= (
            controller.auto_recovery_cooldown_seconds + 0.01
        )

        # Process event - should trigger time-based recovery
        result = controller.process_event(vector, moral_value=0.8)

        # Should have recovered
        assert controller.emergency_shutdown is False
        assert result is not None

    def test_time_based_recovery_before_cooldown_fails(self):
        """Test that recovery fails if time-based cooldown has not passed."""
        controller = CognitiveController(
            memory_threshold_mb=0.001,
            auto_recovery_enabled=True,
            auto_recovery_cooldown_seconds=10.0,  # Long cooldown
        )
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Increase memory threshold
        controller.memory_threshold_mb = 10000.0

        # Don't wait for cooldown - process immediately
        result = controller.process_event(vector, moral_value=0.8)

        # Should still be in emergency (neither step nor time cooldown passed)
        assert controller.emergency_shutdown is True
        assert result["rejected"] is True

    def test_time_based_recovery_disabled_uses_step_only(self):
        """Test that with time-based recovery disabled, only step-based works."""
        from mlsdm.core.cognitive_controller import _CC_RECOVERY_COOLDOWN_STEPS

        controller = CognitiveController(
            memory_threshold_mb=0.001,
            auto_recovery_enabled=False,  # Disable time-based
        )
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Increase memory threshold
        controller.memory_threshold_mb = 10000.0

        # Even with time passed, won't recover without step cooldown
        controller._last_emergency_time -= controller.auto_recovery_cooldown_seconds + 1.0
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Now pass step-based cooldown
        controller.step_counter += _CC_RECOVERY_COOLDOWN_STEPS
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is False

    def test_manual_reset_clears_time_tracking(self):
        """Test that manual reset clears time tracking."""
        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller._last_emergency_time > 0

        # Manual reset
        controller.reset_emergency_shutdown()
        assert controller._last_emergency_time == 0.0


class TestCognitiveControllerYamlConfig:
    """Test yaml_config initialization path."""

    def test_yaml_config_without_synaptic_config(self):
        """Test initialization with yaml_config but without synaptic_config."""
        # This tests lines 101-103 in cognitive_controller.py
        # Provide yaml_config without synaptic_config to trigger the path
        yaml_config = {
            "multi_level_memory": {
                "lambda_l1": 0.5,
                "lambda_l2": 0.1,
            }
        }

        controller = CognitiveController(
            dim=128,
            yaml_config=yaml_config
        )

        assert controller.dim == 128
        assert controller.emergency_shutdown is False


class TestCognitiveControllerGetPhase:
    """Test get_phase method."""

    def test_get_phase(self):
        """Test that get_phase returns the current phase."""
        # This tests line 208 in cognitive_controller.py
        controller = CognitiveController()

        phase = controller.get_phase()

        assert isinstance(phase, str)
        assert phase in ["wake", "sleep"]


class TestCognitiveControllerProcessingTimeout:
    """Test processing timeout handling."""

    def test_processing_timeout_exceeded(self):
        """Test processing timeout rejection."""
        # This tests lines 373-377 in cognitive_controller.py
        from unittest.mock import patch

        controller = CognitiveController(max_processing_time_ms=1.0)  # Very short timeout
        vector = np.random.randn(384).astype(np.float32)

        # Mock time.perf_counter to simulate long processing time
        call_count = [0]

        def mock_perf_counter():
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - start time
                return 0.0
            else:
                # Second call - simulate >1ms elapsed (convert to seconds)
                return 2.0  # 2000ms elapsed

        with patch('time.perf_counter', side_effect=mock_perf_counter):
            result = controller.process_event(vector, moral_value=0.8)

        # Should be rejected for processing timeout
        assert result["rejected"] is True
        assert "processing time exceeded" in result["note"]


class TestCognitiveControllerMetricsExporterExceptions:
    """Test exception handling for metrics exporter."""

    def test_reset_emergency_shutdown_with_metrics_exception(self):
        """Test reset_emergency_shutdown when get_metrics_exporter() raises."""
        # This tests lines 440-441 in cognitive_controller.py
        from unittest.mock import patch

        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency first
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Mock get_metrics_exporter to raise exception
        with patch('mlsdm.core.cognitive_controller.get_metrics_exporter', side_effect=Exception("Metrics unavailable")):
            # Should not raise, just log and continue
            controller.reset_emergency_shutdown()

        assert controller.emergency_shutdown is False

    def test_enter_emergency_shutdown_with_metrics_exception(self):
        """Test _enter_emergency_shutdown when get_metrics_exporter() raises."""
        # This tests lines 462-463 in cognitive_controller.py
        from unittest.mock import patch

        controller = CognitiveController(memory_threshold_mb=0.001)
        vector = np.random.randn(384).astype(np.float32)

        # Mock get_metrics_exporter to raise exception
        with patch('mlsdm.core.cognitive_controller.get_metrics_exporter', side_effect=Exception("Metrics unavailable")):
            # Should not raise, just log and continue
            result = controller.process_event(vector, moral_value=0.8)

        # Should still enter emergency state despite metrics failure
        assert controller.emergency_shutdown is True
        assert result["rejected"] is True

    def test_record_auto_recovery_with_metrics_exception(self):
        """Test _record_auto_recovery when get_metrics_exporter() raises."""
        # This tests lines 526-528 in cognitive_controller.py
        from unittest.mock import patch

        controller = CognitiveController(
            memory_threshold_mb=0.001,
            auto_recovery_cooldown_seconds=0.1
        )
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Increase memory threshold and simulate cooldown passage
        controller.memory_threshold_mb = 10000.0
        controller._last_emergency_time -= 1.0

        # Mock get_metrics_exporter to raise exception during recovery
        with patch('mlsdm.core.cognitive_controller.get_metrics_exporter', side_effect=Exception("Metrics unavailable")):
            # Should not raise, recovery should still work
            _ = controller.process_event(vector, moral_value=0.8)

        # Recovery should succeed despite metrics failure
        assert controller.emergency_shutdown is False
