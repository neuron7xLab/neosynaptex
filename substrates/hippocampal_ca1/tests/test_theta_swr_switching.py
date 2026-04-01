import numpy as np

from core.theta_swr_switching import (
    NetworkState,
    NetworkStateController,
    ReplayDetector,
    StateTransitionParams,
)


def test_state_transitions_reachable():
    np.random.seed(0)
    params = StateTransitionParams(
        P_theta_to_SWR=0.9, P_SWR_to_theta=0.9, P_transition_duration=1.0
    )
    controller = NetworkStateController(params, dt=1.0)

    visited = {controller.state}
    for _ in range(50):
        state, _ = controller.step()
        visited.add(state)
        if NetworkState.SWR in visited and NetworkState.THETA in visited:
            break

    assert NetworkState.THETA in visited
    assert NetworkState.SWR in visited
    controller.state = NetworkState.SWR
    assert controller.get_inhibition_factor() < 1.0
    assert controller.get_recurrence_factor() > 1.0


def test_replay_detector_thresholding():
    detector = ReplayDetector(
        rate_threshold=2.0, min_duration=20.0, max_duration=150.0, min_neurons=3
    )
    detector.update_baseline(spike_count=10, window=100.0)

    spikes = [(0.0, 0), (1.0, 1), (2.0, 2), (3.0, 0)]
    event_start = detector.detect(t=30.0, spikes=spikes, state=NetworkState.SWR)
    assert event_start is None

    event = detector.detect(t=70.0, spikes=[], state=NetworkState.SWR)
    assert event is not None
    assert detector.min_duration <= event.duration() <= detector.max_duration
    assert event.n_neurons() >= detector.min_neurons
