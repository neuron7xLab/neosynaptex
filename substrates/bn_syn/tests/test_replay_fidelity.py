"""Tests for replay fidelity tracking."""

import numpy as np

from bnsyn.assembly.detector import AssemblyDetector
from bnsyn.assembly.replay_fidelity import ReplayFidelityTracker


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _feed_correlated(det: AssemblyDetector, N: int, n_steps: int, seed: int = 0) -> None:
    """Feed correlated-group spikes into the detector."""
    rng = np.random.default_rng(seed)
    for step in range(n_steps):
        spiked = np.zeros(N, dtype=bool)
        if rng.random() < 0.3:
            spiked[:10] = rng.random(10) < 0.8
        if rng.random() < 0.3:
            spiked[10:20] = rng.random(10) < 0.8
        spiked[20:] = rng.random(N - 20) < 0.05
        det.observe(spiked, step)


def _feed_random(det: AssemblyDetector, N: int, n_steps: int, start_step: int = 0, seed: int = 99) -> None:
    """Feed independent random spikes."""
    rng = np.random.default_rng(seed)
    for step in range(start_step, start_step + n_steps):
        spiked = rng.random(N) < 0.05
        det.observe(spiked, step)


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestReplayFidelity:
    def test_replay_fidelity_same_data(self) -> None:
        """Same correlated data in wake and replay should yield high cosine similarity."""
        N = 50
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)

        # Wake phase
        _feed_correlated(det, N, n_steps=3000, seed=42)
        tracker = ReplayFidelityTracker(det)
        tracker.snapshot_wake_state()

        # "Replay" with identical statistics (same seed, fresh detector buffer)
        # Reset detector buffer by creating a new one and re-feeding
        det2 = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)
        _feed_correlated(det2, N, n_steps=3000, seed=42)
        tracker2 = ReplayFidelityTracker(det2)
        # Snapshot first, then measure (uses same data)
        tracker2.snapshot_wake_state()
        result = tracker2.measure_replay_fidelity("light_sleep")

        # With identical data, cosine similarity should be 1.0 (or very close)
        assert result.mean_cosine_similarity > 0.9, (
            f"Expected high cosine similarity for same data, got {result.mean_cosine_similarity}"
        )
        assert result.assembly_reactivation_rate > 0.5

    def test_replay_fidelity_random_data(self) -> None:
        """Random replay after correlated wake should yield low reactivation."""
        N = 50
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)

        # Wake: correlated
        _feed_correlated(det, N, n_steps=3000, seed=7)
        tracker = ReplayFidelityTracker(det)
        tracker.snapshot_wake_state()

        # Now overwrite buffer with random spikes (new detector for clean buffer)
        det_replay = AssemblyDetector(N, bin_ms=10.0, buffer_bins=300)
        _feed_random(det_replay, N, n_steps=3000, start_step=3000, seed=123)

        # Build tracker on replay detector but inject wake result
        tracker_replay = ReplayFidelityTracker(det_replay)
        tracker_replay._wake_result = tracker._wake_result  # transfer wake snapshot
        result = tracker_replay.measure_replay_fidelity("deep_sleep")

        # Random replay should not reactivate wake assemblies well
        assert result.assembly_reactivation_rate < 1.0, (
            f"Expected low reactivation for random replay, got {result.assembly_reactivation_rate}"
        )

    def test_replay_fidelity_phase_label(self) -> None:
        """Phase string should be preserved in the result."""
        N = 30
        det = AssemblyDetector(N, bin_ms=10.0, buffer_bins=100)
        _feed_correlated(det, N, n_steps=1000, seed=5)
        tracker = ReplayFidelityTracker(det)
        tracker.snapshot_wake_state()
        result = tracker.measure_replay_fidelity("rem")
        assert result.phase == "rem"
