"""Event Bus — in-process pub/sub for inter-substrate reactive communication.

Sync, thread-safe, zero external dependencies.
Bounded queue (max 10000), overflow drops oldest.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SubstrateEvent:
    """Base event type. All events are frozen with timestamp."""

    event_type: str = ""
    domain: str = ""
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class GammaShiftEvent(SubstrateEvent):
    event_type: str = "gamma_shift"
    old_gamma: float = 0.0
    new_gamma: float = 0.0


@dataclass(frozen=True)
class PhaseTransitionEvent(SubstrateEvent):
    event_type: str = "phase_transition"
    old_phase: str = ""
    new_phase: str = ""


@dataclass(frozen=True)
class AnomalyEvent(SubstrateEvent):
    event_type: str = "anomaly"
    metric: str = ""
    value: float = 0.0
    threshold: float = 0.0


@dataclass(frozen=True)
class ModulationEvent(SubstrateEvent):
    event_type: str = "modulation"
    delta: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class CoherenceEvent(SubstrateEvent):
    event_type: str = "coherence"
    domain: str = "global"
    global_gamma: float = 0.0
    per_domain_gammas: tuple[tuple[str, float], ...] = ()


_MAX_QUEUE = 10000

EventHandler = Callable[[SubstrateEvent], Any]


class EventBus:
    """Synchronous in-process event bus with bounded history."""

    def __init__(self, max_events: int = _MAX_QUEUE) -> None:
        self._max = max_events
        self._events: list[SubstrateEvent] = []
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._lock = threading.Lock()

    def emit(self, event: SubstrateEvent) -> None:
        """Publish event, notify subscribers, maintain bounded queue."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max:
                self._events = self._events[-self._max :]

            # Notify type-specific handlers
            for handler in self._handlers.get(event.event_type, []):
                with contextlib.suppress(Exception):
                    handler(event)

            # Notify global handlers
            for handler in self._global_handlers:
                with contextlib.suppress(Exception):
                    handler(event)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe handler to specific event type."""
        with self._lock:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe handler from specific event type. Returns True if found."""
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe handler to all events."""
        with self._lock:
            self._global_handlers.append(handler)

    def unsubscribe_all(self, handler: EventHandler) -> bool:
        """Unsubscribe handler from global events. Returns True if found."""
        with self._lock:
            try:
                self._global_handlers.remove(handler)
                return True
            except ValueError:
                return False

    def replay(self, since: float = 0.0) -> list[SubstrateEvent]:
        """Return events since timestamp (monotonic)."""
        with self._lock:
            return [e for e in self._events if e.timestamp >= since]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._events)
