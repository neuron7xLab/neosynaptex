"""Consolidation audit ledger utilities for deterministic event tracking.

Key components:
- ``ConsolidationEvent``: immutable record for a consolidation checkpoint.
- ``ConsolidationLedger``: append-only event ledger with deterministic SHA256 hashing.

References
----------
docs/SPEC.md#P0-10
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

Float64Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass
class ConsolidationEvent:
    """Single consolidation event record.

    Parameters
    ----------
    step : int
        Simulation step number.
    timestamp : float
        Event timestamp in seconds.
    gate : float
        Gate value at event time.
    temperature : float
        System temperature at event time.
    dw_tags_sum : float | None
        Sum of DualWeights tags (if available).
    dw_protein : float | None
        DualWeights protein level (if available).
    tag_count : int | None
        Total number of active tags (if available).

    Notes
    -----
    Records snapshot of consolidation-relevant state for audit purposes.
    """

    step: int
    timestamp: float
    gate: float
    temperature: float
    dw_tags_sum: float | None = None
    dw_protein: float | None = None
    tag_count: int | None = None


@dataclass
class ConsolidationLedger:
    """Audit ledger for consolidation events with cryptographic hashing.

    Parameters
    ----------
    events : list[ConsolidationEvent]
        Chronologically ordered consolidation events.

    Notes
    -----
    - Events are append-only to maintain audit integrity.
    - Hash computed deterministically using SHA256.
    - Supports optional DualWeights state recording.

    References
    ----------
    docs/SPEC.md
    """

    events: list[ConsolidationEvent] = field(default_factory=list)

    def record_event(
        self,
        gate: float,
        temperature: float,
        step: int,
        timestamp: float = 0.0,
        dw_tags: BoolArray | None = None,
        dw_protein: float | None = None,
    ) -> None:
        """Record a consolidation event to the ledger.

        Parameters
        ----------
        gate : float
            Gate value at event time (must be in [0, 1]).
        temperature : float
            System temperature (must be non-negative).
        step : int
            Simulation step number (must be non-negative).
        timestamp : float, optional
            Event timestamp in seconds (default: 0.0).
        dw_tags : BoolArray | None, optional
            DualWeights tag array for tag sum computation.
        dw_protein : float | None, optional
            DualWeights protein level (must be in [0, 1] if provided).

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If gate, temperature, step, or protein are out of valid ranges.

        Notes
        -----
        - Computes tag sum and count from dw_tags if provided.
        - Events are immutable once recorded.
        """
        if not 0 <= gate <= 1:
            raise ValueError("gate must be in [0, 1]")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")
        if step < 0:
            raise ValueError("step must be non-negative")
        if dw_protein is not None and not 0 <= dw_protein <= 1:
            raise ValueError("dw_protein must be in [0, 1]")

        # Compute tag statistics if provided
        dw_tags_sum: float | None = None
        tag_count: int | None = None
        if dw_tags is not None:
            tag_sum = np.sum(dw_tags)
            dw_tags_sum = float(tag_sum)
            tag_count = int(tag_sum)

        event = ConsolidationEvent(
            step=step,
            timestamp=timestamp,
            gate=gate,
            temperature=temperature,
            dw_tags_sum=dw_tags_sum,
            dw_protein=dw_protein,
            tag_count=tag_count,
        )
        self.events.append(event)

    def get_history(self) -> list[dict[str, Any]]:
        """Return ledger history as list of event dictionaries.

        Returns
        -------
        list[dict[str, Any]]
            List of event dictionaries with keys: 'step', 'timestamp', 'gate',
            'temperature', 'dw_tags_sum', 'dw_protein', 'tag_count'.

        Notes
        -----
        Returns copies to prevent external modification of ledger.
        """
        return [
            {
                "step": event.step,
                "timestamp": event.timestamp,
                "gate": event.gate,
                "temperature": event.temperature,
                "dw_tags_sum": event.dw_tags_sum,
                "dw_protein": event.dw_protein,
                "tag_count": event.tag_count,
            }
            for event in self.events
        ]

    def compute_hash(self) -> str:
        """Compute SHA256 hash of entire ledger state.

        Returns
        -------
        str
            Hexadecimal SHA256 hash digest of ledger contents.

        Notes
        -----
        - Hash is deterministic for reproducibility verification.
        - Includes all event fields in canonical order.
        - Uses UTF-8 encoding for string representation.
        - None values are represented as "None" in hash computation.

        Examples
        --------
        >>> ledger = ConsolidationLedger()
        >>> ledger.record_event(gate=1.0, temperature=0.5, step=100)
        >>> hash_value = ledger.compute_hash()
        >>> len(hash_value)
        64
        """
        hasher = hashlib.sha256()

        for event in self.events:
            # Canonical string representation of event
            event_str = (
                f"step={event.step},"
                f"timestamp={event.timestamp:.10f},"
                f"gate={event.gate:.10f},"
                f"temperature={event.temperature:.10f},"
                f"dw_tags_sum={event.dw_tags_sum},"
                f"dw_protein={event.dw_protein},"
                f"tag_count={event.tag_count}"
            )
            hasher.update(event_str.encode("utf-8"))

        return hasher.hexdigest()

    def get_state(self) -> dict[str, Any]:
        """Return ledger state for inspection or serialization.

        Returns
        -------
        dict[str, Any]
            Dictionary with 'event_count' and 'hash' keys.

        Notes
        -----
        Provides lightweight state summary without full event history.
        """
        return {
            "event_count": len(self.events),
            "hash": self.compute_hash(),
        }
