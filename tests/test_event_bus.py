"""12 tests for EventBus — inter-substrate reactive communication."""

import threading
import time

from core.event_bus import (
    AnomalyEvent,
    CoherenceEvent,
    EventBus,
    GammaShiftEvent,
    ModulationEvent,
    PhaseTransitionEvent,
    SubstrateEvent,
)


def test_emit_and_replay():
    bus = EventBus()
    bus.emit(SubstrateEvent(event_type="test", domain="spike"))
    assert bus.count == 1
    events = bus.replay()
    assert len(events) == 1
    assert events[0].domain == "spike"


def test_subscribe_receives_event():
    bus = EventBus()
    received = []
    bus.subscribe("gamma_shift", lambda e: received.append(e))
    bus.emit(GammaShiftEvent(domain="morpho", old_gamma=0.9, new_gamma=1.0))
    assert len(received) == 1
    assert received[0].old_gamma == 0.9


def test_subscribe_all_receives_all():
    bus = EventBus()
    received = []
    bus.subscribe_all(lambda e: received.append(e))
    bus.emit(GammaShiftEvent(domain="spike"))
    bus.emit(PhaseTransitionEvent(domain="morpho", old_phase="INIT", new_phase="METASTABLE"))
    assert len(received) == 2


def test_subscribe_filters_by_type():
    bus = EventBus()
    gamma_events = []
    bus.subscribe("gamma_shift", lambda e: gamma_events.append(e))
    bus.emit(GammaShiftEvent(domain="spike"))
    bus.emit(PhaseTransitionEvent(domain="morpho"))
    assert len(gamma_events) == 1


def test_bounded_queue_drops_oldest():
    bus = EventBus(max_events=5)
    for i in range(10):
        bus.emit(SubstrateEvent(event_type="test", domain=f"d{i}"))
    assert bus.count == 5
    events = bus.replay()
    assert events[0].domain == "d5"


def test_replay_since_timestamp():
    bus = EventBus()
    bus.emit(SubstrateEvent(event_type="old", domain="a"))
    cutoff = time.monotonic()
    bus.emit(SubstrateEvent(event_type="new", domain="b"))
    recent = bus.replay(since=cutoff)
    assert len(recent) == 1
    assert recent[0].domain == "b"


def test_clear():
    bus = EventBus()
    bus.emit(SubstrateEvent(event_type="test", domain="a"))
    bus.clear()
    assert bus.count == 0


def test_events_are_frozen():
    event = GammaShiftEvent(domain="spike", old_gamma=0.9, new_gamma=1.0)
    import dataclasses

    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        event.domain = "changed"  # type: ignore[misc]


def test_anomaly_event():
    event = AnomalyEvent(domain="spike", metric="sr", value=1.6, threshold=1.5)
    assert event.event_type == "anomaly"
    assert event.value == 1.6


def test_modulation_event():
    event = ModulationEvent(domain="morpho", delta=0.03, reason="gamma drift")
    assert abs(event.delta) <= 0.05
    assert event.reason == "gamma drift"


def test_coherence_event():
    event = CoherenceEvent(
        global_gamma=1.003,
        per_domain_gammas=(("spike", 0.95), ("morpho", 1.0)),
    )
    assert event.event_type == "coherence"
    assert len(event.per_domain_gammas) == 2


def test_thread_safety():
    bus = EventBus()
    n_threads = 4
    n_per_thread = 100

    def emit_batch(tid: int) -> None:
        for i in range(n_per_thread):
            bus.emit(SubstrateEvent(event_type="thread_test", domain=f"t{tid}_{i}"))

    threads = [threading.Thread(target=emit_batch, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert bus.count == n_threads * n_per_thread
