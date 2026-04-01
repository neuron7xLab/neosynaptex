"""Memory consolidator with capacity-based eviction and consolidation dynamics.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements a high-level consolidator interface that wraps internal MemoryTrace
with enhanced eviction logic and consolidation tracking.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .trace import MemoryTrace as _InternalMemoryTrace

Float64Array = NDArray[np.float64]


@dataclass
class ConsolidatedMemory:
    """A stored memory pattern with metadata.

    Parameters
    ----------
    pattern : Float64Array
        Stored pattern (1D array).
    importance : float
        Importance score in [0, 1].
    tag_step : int
        Step when this pattern was tagged.
    consolidated : bool
        Whether this pattern has been consolidated.
    strength : float
        Consolidation strength in [0, 1].
    recall_count : int
        Number of times this pattern has been recalled.

    Notes
    -----
    Immutable snapshot of a memory trace returned by MemoryConsolidator.

    References
    ----------
    docs/SPEC.md
    """

    pattern: Float64Array
    importance: float
    tag_step: int
    consolidated: bool
    strength: float
    recall_count: int


class MemoryConsolidator:
    """Consolidate and recall memory patterns with eviction policy.

    Parameters
    ----------
    capacity : int
        Maximum number of patterns to store (must be positive).

    Notes
    -----
    - Provides tag/consolidate/recall API per SPEC.
    - Evicts least important non-consolidated patterns when at capacity.
    - Deterministic tie-breaking: oldest pattern evicted first.

    References
    ----------
    docs/SPEC.md
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._capacity = capacity
        self._storage = _InternalMemoryTrace(capacity=capacity)
        self._step_counter = 0
        self._consolidated_flags: list[bool] = []
        self._strengths: list[float] = []
        self._tag_steps: list[int] = []

    def tag(self, pattern: Float64Array, importance: float) -> ConsolidatedMemory:
        """Tag a new memory pattern.

        Parameters
        ----------
        pattern : Float64Array
            Pattern vector to store (must be 1D).
        importance : float
            Importance score in [0, 1].

        Returns
        -------
        ConsolidatedMemory
            The stored memory trace.

        Raises
        ------
        ValueError
            If pattern is not 1D or importance is out of range.

        Notes
        -----
        If at capacity, evicts least important non-consolidated pattern.
        Tie-breaking: oldest pattern evicted first (deterministic).
        """
        if pattern.ndim != 1:
            raise ValueError("pattern must be 1D array")
        if not 0.0 <= importance <= 1.0:
            raise ValueError("importance must be in [0, 1]")

        # Check if we need to evict before adding
        if len(self._storage.patterns) >= self._capacity:
            # Find least important non-consolidated pattern
            eviction_idx = self._find_eviction_candidate()
            if eviction_idx is not None:
                self._evict(eviction_idx)

        # Tag the new pattern
        self._storage.tag(pattern, importance)
        self._consolidated_flags.append(False)
        self._strengths.append(0.0)
        self._tag_steps.append(self._step_counter)
        self._step_counter += 1

        # Return ConsolidatedMemory snapshot
        idx = len(self._storage.patterns) - 1
        return ConsolidatedMemory(
            pattern=self._storage.patterns[idx].astype(np.float64, copy=True),
            importance=float(self._storage.importance[idx]),
            tag_step=self._tag_steps[idx],
            consolidated=self._consolidated_flags[idx],
            strength=self._strengths[idx],
            recall_count=int(self._storage.recall_counters[idx]),
        )

    def _find_eviction_candidate(self) -> int | None:
        """Find index of pattern to evict.

        Returns
        -------
        int | None
            Index of pattern to evict, or None if all consolidated.

        Notes
        -----
        Evicts least important non-consolidated pattern.
        Deterministic tie-breaking: oldest (lowest tag_step) first.
        """
        candidates = []
        for i in range(len(self._storage.patterns)):
            if not self._consolidated_flags[i]:
                candidates.append(
                    (
                        self._storage.importance[i],
                        self._tag_steps[i],
                        i,
                    )
                )

        if not candidates:
            # All consolidated, evict oldest overall
            return 0

        # Sort by (importance, tag_step) ascending
        candidates.sort()
        return candidates[0][2]

    def _evict(self, idx: int) -> None:
        """Evict pattern at index.

        Parameters
        ----------
        idx : int
            Index to evict.
        """
        self._storage.remove_at(idx)
        self._consolidated_flags.pop(idx)
        self._strengths.pop(idx)
        self._tag_steps.pop(idx)

    def consolidate(self, protein_level: float, temperature: float) -> list[ConsolidatedMemory]:
        """Apply consolidation to stored patterns.

        Parameters
        ----------
        protein_level : float
            Global protein availability in [0, 1].
        temperature : float
            System temperature (non-negative).

        Returns
        -------
        list[ConsolidatedMemory]
            List of newly consolidated memory traces.

        Raises
        ------
        ValueError
            If protein_level or temperature out of range.

        Notes
        -----
        Updates consolidation flags and strength based on protein and temperature.
        """
        if not 0 <= protein_level <= 1:
            raise ValueError("protein_level must be in [0, 1]")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")

        self._storage.consolidate(protein_level, temperature)

        # Update consolidation flags and strengths
        consolidated_traces = []
        for i in range(len(self._storage.patterns)):
            # Consolidation threshold: protein level * temperature factor
            consolidation_gain = protein_level * (1.0 + temperature) * 0.1
            self._strengths[i] = min(1.0, self._strengths[i] + consolidation_gain)

            # Mark as consolidated if strength exceeds threshold
            if self._strengths[i] > 0.5 and protein_level > 0.5:
                if not self._consolidated_flags[i]:
                    self._consolidated_flags[i] = True
                    consolidated_traces.append(
                        ConsolidatedMemory(
                            pattern=self._storage.patterns[i].astype(np.float64, copy=True),
                            importance=float(self._storage.importance[i]),
                            tag_step=self._tag_steps[i],
                            consolidated=True,
                            strength=self._strengths[i],
                            recall_count=int(self._storage.recall_counters[i]),
                        )
                    )

        return consolidated_traces

    def recall(self, cue: Float64Array, threshold: float = 0.7) -> ConsolidatedMemory | None:
        """Recall a memory similar to the cue.

        Parameters
        ----------
        cue : Float64Array
            Query pattern (1D, non-zero norm).
        threshold : float, optional
            Similarity threshold for recall (default: 0.7).

        Returns
        -------
        ConsolidatedMemory | None
            Most similar memory trace above threshold, or None if no match.

        Raises
        ------
        ValueError
            If cue is invalid or threshold out of range.

        Notes
        -----
        Uses cosine similarity. Returns None if no patterns stored or no match.
        """
        if cue.ndim != 1:
            raise ValueError("cue must be 1D array")
        if float(np.linalg.norm(cue)) == 0:
            raise ValueError("cue must have non-zero norm")
        if not -1 <= threshold <= 1:
            raise ValueError("threshold must be in [-1, 1]")

        indices = self._storage.recall(cue, threshold)

        if not indices:
            return None

        # Return best match (first in sorted list)
        best_idx = indices[0]
        return ConsolidatedMemory(
            pattern=self._storage.patterns[best_idx].astype(np.float64, copy=True),
            importance=float(self._storage.importance[best_idx]),
            tag_step=self._tag_steps[best_idx],
            consolidated=self._consolidated_flags[best_idx],
            strength=self._strengths[best_idx],
            recall_count=int(self._storage.recall_counters[best_idx]),
        )

    def stats(self) -> dict[str, float | int]:
        """Return consolidator statistics.

        Returns
        -------
        dict[str, float | int]
            Dictionary with count, consolidated_count, mean_strength,
            mean_importance, and total_recalls.

        Notes
        -----
        Useful for dashboard and demo reporting.
        """
        count = len(self._storage.patterns)
        if count == 0:
            return {
                "count": 0,
                "consolidated_count": 0,
                "mean_strength": 0.0,
                "mean_importance": 0.0,
                "total_recalls": 0,
            }

        consolidated_count = sum(self._consolidated_flags)
        mean_strength = float(np.mean(self._strengths))
        mean_importance = float(np.mean(self._storage.importance))
        total_recalls = int(np.sum(self._storage.recall_counters))

        return {
            "count": count,
            "consolidated_count": consolidated_count,
            "mean_strength": mean_strength,
            "mean_importance": mean_importance,
            "total_recalls": total_recalls,
        }
