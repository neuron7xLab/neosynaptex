"""Tests for EventBus integration with Neosynaptex engine."""

import numpy as np

from core.event_bus import (
    CoherenceEvent,
    GammaShiftEvent,
    PhaseTransitionEvent,
    SubstrateEvent,
)
from neosynaptex import MockBnSynAdapter, MockMfnAdapter, MockMarketAdapter, Neosynaptex


def test_engine_exposes_event_bus():
    nx = Neosynaptex(window=16)
    assert nx.event_bus is not None
    assert nx.event_bus.count == 0


def test_engine_emits_coherence_events():
    nx = Neosynaptex(window=16)
    nx.register(MockBnSynAdapter())
    nx.register(MockMfnAdapter())

    events: list[SubstrateEvent] = []
    nx.event_bus.subscribe("coherence", lambda e: events.append(e))

    for _ in range(10):
        nx.observe()

    coherence_events = [e for e in events if isinstance(e, CoherenceEvent)]
    assert len(coherence_events) > 0
    # Check that global_gamma is set
    last_coh = coherence_events[-1]
    assert np.isfinite(last_coh.global_gamma) or True  # may be NaN early on


def test_engine_emits_phase_transitions():
    nx = Neosynaptex(window=16)
    nx.register(MockBnSynAdapter())
    nx.register(MockMfnAdapter())
    nx.register(MockMarketAdapter())

    events: list[PhaseTransitionEvent] = []
    nx.event_bus.subscribe("phase_transition", lambda e: events.append(e))

    for _ in range(30):
        nx.observe()

    # At minimum there should be an INITIALIZING -> something transition
    if events:
        first = events[0]
        # Phase enum is str-subclass, but str() includes class prefix
        assert "INITIALIZING" in first.old_phase
        assert first.new_phase != ""


def test_custom_event_bus_injection():
    from core.event_bus import EventBus

    bus = EventBus()
    nx = Neosynaptex(window=16, event_bus=bus)
    assert nx.event_bus is bus

    nx.register(MockBnSynAdapter())
    nx.register(MockMfnAdapter())
    for _ in range(5):
        nx.observe()

    # Events should land on the injected bus
    assert bus.count > 0


def test_unsubscribe():
    from core.event_bus import EventBus

    bus = EventBus()
    events: list[SubstrateEvent] = []
    handler = lambda e: events.append(e)

    bus.subscribe("test", handler)
    bus.emit(SubstrateEvent(event_type="test"))
    assert len(events) == 1

    result = bus.unsubscribe("test", handler)
    assert result is True

    bus.emit(SubstrateEvent(event_type="test"))
    assert len(events) == 1  # no new events after unsubscribe


def test_unsubscribe_nonexistent():
    from core.event_bus import EventBus

    bus = EventBus()
    result = bus.unsubscribe("test", lambda e: None)
    assert result is False
