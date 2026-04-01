"""
Theta ↔ SWR Mode Switching with Validation
Implements network state transitions and replay detection

Based on:
- O'Keefe & Recce 1993 (theta rhythms)
- SWR curated dataset, Nature Sci Data 2025 (DOI: 10.1038/s41597-025-06115-0)

Key improvements:
1. Explicit state machine (theta/SWR/transition)
2. Gated inhibition control (OLM, PV interneurons)
3. Neuromodulation (ACh for theta, lack of ACh for SWR)
4. Replay detection and validation metrics
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class NetworkState(Enum):
    """Network operational state"""

    THETA = "theta"  # Exploration, encoding
    SWR = "swr"  # Offline consolidation, replay
    TRANSITION = "transition"  # Between states


@dataclass
class StateTransitionParams:
    """Parameters for state transitions"""

    # Transition probabilities (per ms)
    P_theta_to_SWR: float = 0.001
    P_SWR_to_theta: float = 0.1
    P_transition_duration: float = 10.0  # ms

    # SWR duration statistics (from curated dataset)
    SWR_duration_mean: float = 50.0  # ms
    SWR_duration_std: float = 20.0

    # Inhibition modulation
    inhibition_reduction_SWR: float = 0.5  # Reduce by 50% during SWR

    # Recurrent excitation boost
    recurrence_boost_SWR: float = 2.0

    # Neuromodulation (ACh level)
    ACh_theta: float = 1.0
    ACh_SWR: float = 0.1


class NetworkStateController:
    """
    Controls network state transitions

    State machine:
    THETA → TRANSITION → SWR → TRANSITION → THETA

    During SWR:
    - Reduce inhibition (disinhibition)
    - Boost recurrent excitation
    - No theta drive
    - ACh low
    """

    def __init__(self, params: StateTransitionParams, dt: float = 0.1):
        self.p = params
        self.dt = dt  # ms

        # Current state
        self.state = NetworkState.THETA
        self.time_in_state = 0.0
        self.SWR_duration = 0.0  # Will be sampled when entering SWR
        self._previous_state = self.state

        # State history
        self.state_history = []

        # Neuromodulation
        self.ACh_level = self.p.ACh_theta

    def step(self) -> Tuple[NetworkState, bool]:
        """
        One timestep of state machine

        Returns:
            current_state: NetworkState
            state_changed: bool (whether transition occurred)
        """
        state_changed = False

        # Increment time in current state
        self.time_in_state += self.dt

        # State transitions
        if self.state == NetworkState.THETA:
            # Theta → SWR transition
            if np.random.rand() < self.p.P_theta_to_SWR * self.dt:
                self._previous_state = self.state
                self.state = NetworkState.TRANSITION
                self.time_in_state = 0.0
                state_changed = True

        elif self.state == NetworkState.TRANSITION:
            # Wait for transition duration
            if self.time_in_state >= self.p.P_transition_duration:
                # Determine next state (based on previous)
                if self._previous_state == NetworkState.THETA:
                    # Entering SWR
                    self.state = NetworkState.SWR
                    # Sample SWR duration
                    self.SWR_duration = max(
                        np.random.normal(self.p.SWR_duration_mean, self.p.SWR_duration_std), 10.0
                    )
                else:
                    # Returning to theta
                    self.state = NetworkState.THETA

                self.time_in_state = 0.0
                state_changed = True

        elif self.state == NetworkState.SWR:
            # SWR → theta transition
            if self.time_in_state >= self.SWR_duration:
                self._previous_state = self.state
                self.state = NetworkState.TRANSITION
                self.time_in_state = 0.0
                state_changed = True

        # Update ACh level (smooth transition)
        target_ACh = self.p.ACh_theta if self.state == NetworkState.THETA else self.p.ACh_SWR
        tau_ACh = 50.0  # ms
        self.ACh_level += (target_ACh - self.ACh_level) / tau_ACh * self.dt

        # Record history
        if state_changed:
            self.state_history.append(self.state)

        return self.state, state_changed

    def get_inhibition_factor(self) -> float:
        """
        Get inhibition scaling factor

        Returns:
            factor: Multiply inhibitory conductances by this
        """
        if self.state == NetworkState.SWR:
            return self.p.inhibition_reduction_SWR
        else:
            return 1.0

    def get_recurrence_factor(self) -> float:
        """
        Get recurrent excitation scaling factor

        Returns:
            factor: Multiply recurrent weights by this
        """
        if self.state == NetworkState.SWR:
            return self.p.recurrence_boost_SWR
        else:
            return 1.0

    def get_theta_drive(self, t: float, f_theta: float = 8.0) -> float:
        """
        Get theta oscillation drive

        Args:
            t: Current time (ms)
            f_theta: Theta frequency (Hz)

        Returns:
            drive: Theta amplitude (0 during SWR)
        """
        if self.state == NetworkState.THETA:
            return np.sin(2 * np.pi * f_theta * t / 1000.0)
        else:
            return 0.0


# ============================================================================
# REPLAY DETECTION
# ============================================================================


@dataclass
class ReplayEvent:
    """Detected replay event"""

    start_time: float  # ms
    end_time: float
    neuron_sequence: List[int]
    spike_times: List[float]

    def duration(self) -> float:
        return self.end_time - self.start_time

    def n_neurons(self) -> int:
        return len(set(self.neuron_sequence))


class ReplayDetector:
    """
    Detects replay events during SWR

    Criteria (from curated SWR dataset):
    1. Increased population rate (> 3x baseline)
    2. Sequential activation pattern
    3. Duration 20-150 ms
    4. ≥ 5 neurons involved
    """

    def __init__(
        self,
        rate_threshold: float = 3.0,
        min_duration: float = 20.0,
        max_duration: float = 150.0,
        min_neurons: int = 5,
    ):
        self.rate_threshold = rate_threshold
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.min_neurons = min_neurons

        # Detection state
        self.baseline_rate = 0.0
        self.in_candidate = False
        self.candidate_start = 0.0
        self.candidate_spikes = []

    def update_baseline(self, spike_count: int, window: float = 100.0):
        """Update baseline rate (during theta)"""
        rate = spike_count / (window / 1000.0)  # Hz
        # Exponential smoothing
        alpha = 0.1
        self.baseline_rate = alpha * rate + (1 - alpha) * self.baseline_rate

    def detect(
        self, t: float, spikes: List[Tuple[float, int]], state: NetworkState  # (time, neuron_id)
    ) -> Optional[ReplayEvent]:
        """
        Detect replay event

        Args:
            t: Current time
            spikes: Recent spikes [(time, neuron_id)]
            state: Current network state

        Returns:
            event: ReplayEvent if detected, else None
        """
        if state != NetworkState.SWR:
            self.in_candidate = False
            self.candidate_spikes = []
            return None

        # Add current spikes to candidate
        self.candidate_spikes.extend(spikes)

        if self.in_candidate and not spikes:
            duration = t - self.candidate_start
            if (
                duration >= self.min_duration
                and len(set(s[1] for s in self.candidate_spikes)) >= self.min_neurons
            ):
                sorted_spikes = sorted(self.candidate_spikes)
                neuron_seq = [s[1] for s in sorted_spikes]
                spike_times = [s[0] for s in sorted_spikes]
                event = ReplayEvent(
                    start_time=self.candidate_start,
                    end_time=t,
                    neuron_sequence=neuron_seq,
                    spike_times=spike_times,
                )
                self.in_candidate = False
                self.candidate_spikes = []
                return event

        # Compute current rate
        if len(spikes) > 0:
            window = 10.0  # ms
            current_rate = len(spikes) / (window / 1000.0)

            # Check threshold
            if current_rate > self.rate_threshold * max(self.baseline_rate, 1.0):
                if not self.in_candidate:
                    # Start candidate
                    self.in_candidate = True
                    self.candidate_start = t
            else:
                if self.in_candidate:
                    # End candidate, check criteria
                    duration = t - self.candidate_start

                    if (
                        self.min_duration <= duration <= self.max_duration
                        and len(set(s[1] for s in self.candidate_spikes)) >= self.min_neurons
                    ):

                        # Valid replay event
                        neuron_seq = [s[1] for s in sorted(self.candidate_spikes)]
                        spike_times = [s[0] for s in sorted(self.candidate_spikes)]

                        event = ReplayEvent(
                            start_time=self.candidate_start,
                            end_time=t,
                            neuron_sequence=neuron_seq,
                            spike_times=spike_times,
                        )

                        # Reset
                        self.in_candidate = False
                        self.candidate_spikes = []

                        return event

                    # Reset invalid candidate
                    self.in_candidate = False
                    self.candidate_spikes = []

        return None


# ============================================================================
# REPLAY VALIDATION
# ============================================================================


def validate_replay_vs_template(
    replay_sequence: List[int], template_sequence: List[int], method: str = "spearman"
) -> Tuple[float, float]:
    """
    Validate replay against template sequence

    Args:
        replay_sequence: Neuron IDs in replay order
        template_sequence: Template (e.g., from theta exploration)
        method: "spearman" or "jaccard"

    Returns:
        correlation: Sequence similarity metric
        p_value: Statistical significance
    """
    # Find common neurons
    common = set(replay_sequence) & set(template_sequence)

    if len(common) < 3:
        return 0.0, 1.0

    # Ranks in each sequence
    rank_replay = {nid: i for i, nid in enumerate(replay_sequence) if nid in common}
    rank_template = {nid: i for i, nid in enumerate(template_sequence) if nid in common}

    # Align
    ranks_r = [rank_replay[nid] for nid in sorted(common)]
    ranks_t = [rank_template[nid] for nid in sorted(common)]

    if method == "spearman":
        from scipy.stats import spearmanr

        corr, p_val = spearmanr(ranks_r, ranks_t)
        return corr, p_val
    elif method == "jaccard":
        # Jaccard similarity of top-k
        k = min(5, len(common))
        top_r = set(sorted(rank_replay, key=rank_replay.get)[:k])
        top_t = set(sorted(rank_template, key=rank_template.get)[:k])
        jaccard = len(top_r & top_t) / len(top_r | top_t)
        return jaccard, 0.0  # No p-value for Jaccard


def compute_replay_metrics(
    replay_events: List[ReplayEvent], template_sequences: List[List[int]]
) -> Dict[str, float]:
    """
    Compute replay quality metrics

    Metrics (from SWR curated dataset):
    1. Replay rate (events per minute)
    2. Mean sequence correlation
    3. Fraction of significant replays (p < 0.05)
    4. Mean duration
    5. Participation (neurons per event)

    Args:
        replay_events: Detected replays
        template_sequences: Reference sequences from theta

    Returns:
        metrics: Dictionary of validation metrics
    """
    if not replay_events:
        return {
            "n_events": 0,
            "rate_per_min": 0.0,
            "mean_correlation": 0.0,
            "frac_significant": 0.0,
            "mean_duration": 0.0,
            "mean_neurons": 0.0,
        }

    # Correlations
    correlations = []
    p_values = []

    for event in replay_events:
        # Find best matching template
        best_corr = -1.0
        best_p = 1.0

        for template in template_sequences:
            corr, p_val = validate_replay_vs_template(event.neuron_sequence, template)
            if corr > best_corr:
                best_corr = corr
                best_p = p_val

        correlations.append(best_corr)
        p_values.append(best_p)

    # Duration
    durations = [e.duration() for e in replay_events]

    # Participation
    neurons_per_event = [e.n_neurons() for e in replay_events]

    return {
        "n_events": len(replay_events),
        "rate_per_min": 0.0,  # Would need total time
        "mean_correlation": np.mean(correlations),
        "frac_significant": np.mean(np.array(p_values) < 0.05),
        "mean_duration": np.mean(durations),
        "mean_neurons": np.mean(neurons_per_event),
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Testing Theta-SWR State Switching...")

    np.random.seed(42)

    # Create state controller
    params = StateTransitionParams(
        P_theta_to_SWR=0.01,  # 1% chance per ms
        P_SWR_to_theta=0.05,
        SWR_duration_mean=60.0,
        SWR_duration_std=15.0,
    )

    controller = NetworkStateController(params, dt=0.1)

    # Simulate 10 seconds
    T = 10000.0  # ms
    dt = 0.1
    n_steps = int(T / dt)

    print(f"Simulating {T} ms...")

    state_changes = []
    theta_time = 0.0
    swr_time = 0.0

    for step in range(n_steps):
        t = step * dt
        state, changed = controller.step()

        if changed:
            state_changes.append((t, state))

        # Track time in each state
        if state == NetworkState.THETA:
            theta_time += dt
        elif state == NetworkState.SWR:
            swr_time += dt

    print("\n--- State Statistics ---")
    print(f"State changes: {len(state_changes)}")
    print(f"Theta time: {theta_time:.1f} ms ({theta_time/T*100:.1f}%)")
    print(f"SWR time: {swr_time:.1f} ms ({swr_time/T*100:.1f}%)")

    # Test replay detection
    print("\n--- Testing Replay Detection ---")

    detector = ReplayDetector()

    # Simulate theta phase (build template)
    template_sequence = list(range(20))
    detector.update_baseline(spike_count=50, window=100.0)

    # Simulate SWR with replay
    print("Simulating SWR with replay...")

    replay_events = []

    # Create synthetic replay (reversed sequence)
    t_swr = 0.0
    synthetic_spikes = []

    for i, neuron_id in enumerate(reversed(template_sequence)):
        spike_time = t_swr + i * 2.0  # 2 ms spacing
        synthetic_spikes.append((spike_time, neuron_id))

    # Detect
    event = detector.detect(
        t=synthetic_spikes[-1][0] + 10.0, spikes=synthetic_spikes, state=NetworkState.SWR
    )

    if event:
        replay_events.append(event)
        print("✓ Detected replay event:")
        print(f"  Duration: {event.duration():.1f} ms")
        print(f"  Neurons: {event.n_neurons()}")

    # Validate
    print("\n--- Replay Validation ---")

    metrics = compute_replay_metrics(replay_events, [template_sequence])

    for key, val in metrics.items():
        print(f"{key}: {val:.3f}")

    # Test template matching
    if replay_events:
        corr, p_val = validate_replay_vs_template(
            replay_events[0].neuron_sequence, template_sequence
        )
        print(f"\nTemplate correlation: {corr:.3f} (p={p_val:.4f})")
        print(f"Reversed sequence detected: {corr < -0.5}")

    # Test modulation
    print("\n--- Testing Gating Factors ---")

    controller_theta = NetworkStateController(params)
    controller_theta.state = NetworkState.THETA

    controller_swr = NetworkStateController(params)
    controller_swr.state = NetworkState.SWR

    print("Theta mode:")
    print(f"  Inhibition factor: {controller_theta.get_inhibition_factor():.2f}")
    print(f"  Recurrence factor: {controller_theta.get_recurrence_factor():.2f}")
    print(f"  ACh level: {controller_theta.ACh_level:.2f}")

    print("SWR mode:")
    print(f"  Inhibition factor: {controller_swr.get_inhibition_factor():.2f}")
    print(f"  Recurrence factor: {controller_swr.get_recurrence_factor():.2f}")
    print(f"  ACh level: {controller_swr.ACh_level:.2f}")
