"""
Robustness and Safety Tests for MLSDM.

This test suite validates the system's behavior under adverse conditions:
- Configuration failures and missing configs
- Invalid backend configurations
- Moral filter threshold stability under attack
- Stateless fallback behavior
- Error recovery mechanisms
"""

import os
import tempfile

import pytest

from mlsdm.cognition.moral_filter import MoralFilter
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2


class TestMoralFilterThresholdStability:
    """Tests for moral filter threshold stability under adverse conditions."""

    @pytest.mark.security
    def test_threshold_stable_under_toxic_storm(self):
        """
        Test that threshold remains bounded during sustained toxic attack.

        Simulates 1000 consecutive toxic inputs to verify drift bounds.
        """
        moral = MoralFilterV2(initial_threshold=0.5)
        initial_threshold = moral.threshold

        # Simulate toxic storm: 1000 consecutive toxic inputs
        for _ in range(1000):
            result = moral.evaluate(0.1)  # Very toxic
            moral.adapt(result)

        # Threshold must remain within bounds
        assert (
            moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        ), f"Threshold drifted below minimum: {moral.threshold}"
        assert (
            moral.threshold <= MoralFilterV2.MAX_THRESHOLD
        ), f"Threshold drifted above maximum: {moral.threshold}"

        # Drift should be bounded
        drift = abs(moral.threshold - initial_threshold)
        max_drift = MoralFilterV2.MAX_THRESHOLD - MoralFilterV2.MIN_THRESHOLD
        assert drift <= max_drift, f"Drift {drift} exceeds maximum possible {max_drift}"

    @pytest.mark.security
    def test_threshold_recovers_after_attack(self):
        """
        Test that threshold recovers after toxic attack ends.
        """
        moral = MoralFilterV2(initial_threshold=0.5)

        # Phase 1: Toxic attack
        for _ in range(200):
            result = moral.evaluate(0.1)
            moral.adapt(result)

        threshold_after_attack = moral.threshold

        # Phase 2: Normal operation (safe content)
        for _ in range(200):
            result = moral.evaluate(0.8)
            moral.adapt(result)

        threshold_after_recovery = moral.threshold

        # Should move toward initial threshold
        assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD

        # After safe content, threshold should increase from attack level
        # (threshold drops during attack, rises during safe content)
        assert (
            threshold_after_recovery >= threshold_after_attack
            or abs(threshold_after_recovery - threshold_after_attack) < 0.1
        )

    @pytest.mark.security
    def test_threshold_oscillation_damping(self):
        """
        Test that rapid switching between toxic and safe doesn't cause oscillation.
        """
        moral = MoralFilterV2(initial_threshold=0.5)

        thresholds = []

        # Alternating toxic/safe inputs
        for i in range(200):
            if i % 2 == 0:  # noqa: SIM108 - if/else is more readable with comments
                result = moral.evaluate(0.1)  # Toxic
            else:
                result = moral.evaluate(0.9)  # Safe
            moral.adapt(result)
            thresholds.append(moral.threshold)

        # Calculate oscillation amplitude in second half
        second_half = thresholds[100:]
        oscillation = max(second_half) - min(second_half)

        # Oscillation should be bounded (EMA should smooth)
        assert oscillation < 0.3, f"Excessive oscillation: {oscillation}"

    @pytest.mark.security
    def test_threshold_invalid_inputs_handled(self):
        """
        Test that invalid moral values are handled gracefully.
        """
        moral = MoralFilter()

        # Values outside [0, 1] should raise ValueError
        with pytest.raises(ValueError):
            moral.evaluate(-0.5)

        with pytest.raises(ValueError):
            moral.evaluate(1.5)

        # NaN handling (should raise)
        with pytest.raises(ValueError):
            moral.evaluate(float("nan"))


class TestConfigurationFailures:
    """Tests for handling missing or corrupt configuration."""

    @pytest.mark.security
    def test_missing_config_file_graceful_fail(self):
        """
        Test that missing config file produces clear error, not crash.
        """
        from mlsdm.utils.config_loader import ConfigLoader

        # Non-existent file should raise clear error
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_config("/nonexistent/path/config.yaml")

    @pytest.mark.security
    def test_corrupt_yaml_config_graceful_fail(self):
        """
        Test that corrupt YAML config produces clear error.
        """
        from mlsdm.utils.config_loader import ConfigLoader

        # Create temporary corrupt YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [}")
            temp_path = f.name

        try:
            with pytest.raises(ValueError):  # Should raise YAML parse error
                ConfigLoader.load_config(temp_path, validate=False)
        finally:
            os.unlink(temp_path)

    @pytest.mark.security
    def test_unsupported_config_format_raises_error(self):
        """
        Test that unsupported config format produces clear error.
        """
        from mlsdm.utils.config_loader import ConfigLoader

        # Create temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value"}')
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported"):
                ConfigLoader.load_config(temp_path)
        finally:
            os.unlink(temp_path)


class TestInvalidBackendConfiguration:
    """Tests for invalid backend/adapter configuration."""

    @pytest.mark.security
    def test_unknown_provider_type_explicit_error(self):
        """
        Test that unknown provider type produces explicit error.
        """
        from mlsdm.adapters.provider_factory import build_provider_from_env

        # Unknown provider type should raise clear error
        with pytest.raises(ValueError, match="(?i)invalid|unknown"):
            build_provider_from_env("nonexistent_provider_xyz")

    @pytest.mark.security
    def test_local_stub_works_without_api_key(self):
        """
        Test that local stub provider works without any API key.
        """
        from mlsdm.adapters.provider_factory import build_provider_from_env

        # Local stub should always work
        provider = build_provider_from_env("local_stub")
        assert provider is not None

        # Should be able to generate
        response = provider.generate("test prompt", 100)
        assert isinstance(response, str)


class TestStatelessFallback:
    """Tests for stateless fallback behavior under errors."""

    @pytest.mark.security
    def test_memory_corruption_triggers_recovery(self):
        """
        Test that memory corruption triggers auto-recovery, not crash.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

        # Add some data
        pelm.entangle([1.0] * 10, 0.5)
        pelm.entangle([2.0] * 10, 0.6)

        # Corrupt pointer
        pelm.pointer = 9999

        # Should detect corruption
        assert pelm.detect_corruption()

        # Should auto-recover
        recovered = pelm.auto_recover()
        assert recovered
        assert not pelm.detect_corruption()

        # Operations should work after recovery
        results = pelm.retrieve([1.0] * 10, 0.5)
        # May or may not find results depending on recovery, but shouldn't crash
        assert isinstance(results, list)

    @pytest.mark.security
    def test_pelm_handles_nan_inputs(self):
        """
        Test that PELM rejects NaN inputs with clear error.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=10)

        # NaN in vector should be rejected
        with pytest.raises(ValueError, match="invalid"):
            pelm.entangle([1.0, float("nan"), 3.0], 0.5)

        # Inf in vector should be rejected
        with pytest.raises(ValueError, match="invalid"):
            pelm.entangle([float("inf"), 2.0, 3.0], 0.5)

    @pytest.mark.security
    def test_pelm_handles_extreme_dimensions(self):
        """
        Test that PELM handles extreme dimension values safely.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        # Zero dimension should fail
        with pytest.raises(ValueError):
            PhaseEntangledLatticeMemory(dimension=0, capacity=100)

        # Negative dimension should fail
        with pytest.raises(ValueError):
            PhaseEntangledLatticeMemory(dimension=-1, capacity=100)

        # Extremely large capacity should fail (memory protection)
        with pytest.raises(ValueError, match="too large|memory"):
            PhaseEntangledLatticeMemory(dimension=384, capacity=10_000_000)


class TestConcurrencyRobustness:
    """Tests for thread safety and race condition prevention."""

    @pytest.mark.security
    def test_concurrent_pelm_entangle_no_corruption(self):
        """
        Test that concurrent entangle operations don't corrupt state.
        """
        import threading
        from queue import Queue

        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=1000)
        errors: Queue = Queue()

        def entangle_batch(thread_id: int, count: int) -> None:
            try:
                for i in range(count):
                    vector = [float(thread_id * 1000 + i)] * 10
                    pelm.entangle(vector, (thread_id + i) / 100.0 % 1.0)
            except Exception as e:
                errors.put((thread_id, str(e)))

        # Run concurrent entangles
        threads = [threading.Thread(target=entangle_batch, args=(i, 50)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        assert errors.empty(), f"Concurrent errors: {list(errors.queue)}"

        # State should be consistent
        assert not pelm.detect_corruption()
        assert pelm.size <= pelm.capacity

    @pytest.mark.security
    def test_concurrent_moral_filter_adapt_no_race(self):
        """
        Test that concurrent moral filter adaptations are thread-safe.
        """
        import threading

        moral = MoralFilterV2(initial_threshold=0.5)

        def adapt_batch(accept: bool, count: int) -> None:
            for _ in range(count):
                moral.adapt(accept)

        threads = [
            threading.Thread(target=adapt_batch, args=(True, 100)),
            threading.Thread(target=adapt_batch, args=(False, 100)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Threshold should still be within bounds
        assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD


class TestErrorRecovery:
    """Tests for error recovery mechanisms."""

    @pytest.mark.security
    def test_rate_limiter_blocks_excess_requests(self):
        """
        Test that rate limiter blocks excess requests.
        """
        from mlsdm.security.rate_limit import RateLimiter

        # 5 requests per 60 second window
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)

        # First 5 requests should be allowed
        for i in range(5):
            assert limiter.is_allowed("client1") is True, f"Request {i+1} should be allowed"

        # 6th request should be blocked
        assert limiter.is_allowed("client1") is False, "6th request should be blocked"

    @pytest.mark.security
    def test_rate_limiter_different_clients_independent(self):
        """
        Test that different clients have independent rate limits.
        """
        from mlsdm.security.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_window=2, window_seconds=60)

        # Exhaust client1's limit
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False

        # client2 should still have its full quota
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is False

    @pytest.mark.security
    def test_aphasia_detector_handles_pathological_input(self):
        """
        Test that aphasia detector handles pathological input.
        """
        from mlsdm.extensions import AphasiaBrocaDetector

        detector = AphasiaBrocaDetector()

        pathological_inputs = [
            "",  # Empty
            "   \n\t  ",  # Whitespace only
            "a" * 10000,  # Very long single word
            ". . . . .",  # Only punctuation
            "😀🎉🚀" * 100,  # Only emojis
            "\x00\x01\x02",  # Control characters
        ]

        for inp in pathological_inputs:
            result = detector.analyze(inp)
            # Should not crash, should return valid result
            assert isinstance(result, dict)
            assert "is_aphasic" in result
            assert "severity" in result
            assert 0.0 <= result["severity"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
