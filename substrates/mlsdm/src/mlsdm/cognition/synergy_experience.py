"""
Synergy Experience Learning Module.

This module implements a learning layer for combo/synergy actions that:
1. Tracks the effectiveness of different action combinations
2. Uses eOI (estimated Objective Index) to measure before/after effects
3. Adapts policy to favor successful combos and avoid ineffective ones

The system follows an ε-greedy exploration strategy with experience-based
weight adjustment.

Key components:
- ComboStats: Stores per-combo statistics (attempts, mean_delta_eoi, last_delta_eoi, ema_delta_eoi)
- SynergyExperienceMemory: Maps (state_signature, combo_id) -> ComboStats
- compute_eoi: Pure function to calculate estimated Objective Index
- create_state_signature: Pure function to discretize state for lookup
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Small constant to avoid division by zero
EPSILON = 1e-9


def _sanitize_delta_eoi(value: float | None) -> float:
    """Sanitize delta_eoi value, converting NaN/inf/None to 0.0.

    Args:
        value: The delta_eoi value to sanitize

    Returns:
        Sanitized float value (0.0 for invalid inputs)
    """
    if value is None:
        return 0.0
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


@dataclass
class ComboStats:
    """Statistics for a single combo action.

    Stores the effectiveness metrics for a combo across multiple trials:
    - attempts: Number of times this combo has been executed
    - mean_delta_eoi: Average eOI change across all trials
    - last_delta_eoi: Most recent eOI change
    - ema_delta_eoi: Exponentially weighted moving average of recent effectiveness

    The EMA gives more weight to recent results, making the policy more responsive
    to changing conditions.
    """

    trial_count: int = 0
    total_delta_eoi: float = 0.0
    last_delta_eoi: float = 0.0
    ema_effectiveness: float = 0.0
    _ema_alpha: float = field(default=0.2, repr=False)  # EMA smoothing factor

    @property
    def attempts(self) -> int:
        """Number of attempts (alias for trial_count)."""
        return self.trial_count

    @property
    def mean_delta_eoi(self) -> float:
        """Mean delta_eoi across all trials (alias for avg_delta_eoi)."""
        return self.avg_delta_eoi

    @property
    def ema_delta_eoi(self) -> float:
        """EMA of delta_eoi (alias for ema_effectiveness)."""
        return self.ema_effectiveness

    @property
    def avg_delta_eoi(self) -> float:
        """Calculate average delta_eoi across all trials."""
        if self.trial_count == 0:
            return 0.0
        return self.total_delta_eoi / self.trial_count

    def update(self, delta_eoi: float) -> None:
        """Update stats with a new trial result.

        Args:
            delta_eoi: The change in eOI (eOI_after - eOI_before).
                       NaN/inf values are treated as 0.0 with a warning.
        """
        # Check for invalid values before sanitizing (NaN != NaN, so direct compare fails)
        is_invalid = delta_eoi is None or math.isnan(delta_eoi) or math.isinf(delta_eoi)
        if is_invalid:
            logger.warning(
                "ComboStats.update received invalid delta_eoi=%s, treating as 0.0",
                delta_eoi,
            )
            delta_eoi = 0.0

        self.trial_count += 1
        self.total_delta_eoi += delta_eoi
        self.last_delta_eoi = delta_eoi

        # Update EMA
        if self.trial_count == 1:
            self.ema_effectiveness = delta_eoi
        else:
            self.ema_effectiveness = (
                self._ema_alpha * delta_eoi + (1 - self._ema_alpha) * self.ema_effectiveness
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize stats to dictionary.

        Returns:
            Dictionary containing:
            - attempts: Number of trials
            - mean_delta_eoi: Average delta_eoi
            - last_delta_eoi: Most recent delta_eoi
            - ema_delta_eoi: EMA of delta_eoi
        """
        return {
            "attempts": self.attempts,
            "mean_delta_eoi": self.mean_delta_eoi,
            "last_delta_eoi": self.last_delta_eoi,
            "ema_delta_eoi": self.ema_delta_eoi,
            # Legacy aliases for backward compatibility
            "trial_count": self.trial_count,
            "avg_delta_eoi": self.avg_delta_eoi,
            "ema_effectiveness": self.ema_effectiveness,
        }


class SynergyExperienceMemory:
    """Memory structure for synergy/combo experience learning.

    Stores and manages experience data for different combo actions across
    various state signatures. Provides methods for updating experience and
    selecting combos based on learned effectiveness.

    Example:
        >>> memory = SynergyExperienceMemory()
        >>> memory.update_experience("state_1", "combo_A", 0.1)  # positive
        >>> memory.update_experience("state_1", "combo_B", -0.05)  # negative
        >>> combo = memory.select_combo("state_1", ["combo_A", "combo_B"])
        >>> # combo_A is more likely to be selected
    """

    def __init__(
        self,
        epsilon: float = 0.1,
        neutral_tolerance: float = 0.01,
        min_trials_for_confidence: int = 3,
    ) -> None:
        """Initialize the synergy experience memory.

        Args:
            epsilon: Exploration rate for ε-greedy selection (0-1)
            neutral_tolerance: Threshold for considering delta_eoi as neutral
            min_trials_for_confidence: Minimum trials before trusting stats
        """
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError(f"epsilon must be in [0, 1], got {epsilon}")
        if neutral_tolerance < 0:
            raise ValueError(f"neutral_tolerance must be non-negative, got {neutral_tolerance}")

        self._experience: dict[tuple[str, str], ComboStats] = {}
        self._lock = Lock()
        self.epsilon = epsilon
        self.neutral_tolerance = neutral_tolerance
        self.min_trials_for_confidence = min_trials_for_confidence

        # Tracking for observability
        self._total_updates = 0
        self._total_selections = 0
        self._exploration_count = 0
        self._exploitation_count = 0

    def update_experience(
        self,
        state_signature: str,
        combo_id: str,
        delta_eoi: float,
    ) -> ComboStats:
        """Update experience after a combo is executed.

        Args:
            state_signature: A signature identifying the current state
            combo_id: Identifier for the combo action
            delta_eoi: The change in eOI (eOI_after - eOI_before)

        Returns:
            The updated ComboStats for this state-combo pair
        """
        # Check for invalid values (NaN != NaN, so use math.isnan)
        is_invalid = delta_eoi is None or (
            isinstance(delta_eoi, float) and (math.isnan(delta_eoi) or math.isinf(delta_eoi))
        )
        if is_invalid:
            logger.warning(
                "update_experience received invalid delta_eoi=%s for combo=%s, treating as 0.0",
                delta_eoi,
                combo_id,
            )
            delta_eoi = 0.0

        key = (state_signature, combo_id)

        with self._lock:
            if key not in self._experience:
                self._experience[key] = ComboStats()

            stats = self._experience[key]
            stats.update(delta_eoi)
            self._total_updates += 1

            # Classify and log the result
            if delta_eoi > self.neutral_tolerance:
                classification = "positive"
            elif delta_eoi < -self.neutral_tolerance:
                classification = "negative"
            else:
                classification = "neutral"

            logger.debug(
                "SynergyExperience update: state=%s combo=%s delta_eoi=%.4f (%s) "
                "attempts=%d mean=%.4f ema=%.4f",
                state_signature,
                combo_id,
                delta_eoi,
                classification,
                stats.attempts,
                stats.mean_delta_eoi,
                stats.ema_delta_eoi,
            )

            return stats

    def record_combo_result(
        self,
        state_signature: str,
        combo_id: str,
        eoi_before: float,
        eoi_after: float,
    ) -> ComboStats:
        """Record the result of executing a combo action.

        This is the primary interface for updating experience. It computes
        delta_eoi = eoi_after - eoi_before and updates the stats.

        Args:
            state_signature: A signature identifying the current state
            combo_id: Identifier for the combo action
            eoi_before: eOI value before the combo was executed
            eoi_after: eOI value after the combo was executed

        Returns:
            The updated ComboStats for this state-combo pair

        Note:
            Invalid values (NaN, inf, None) in eoi_before or eoi_after
            result in delta_eoi being treated as 0.0 with a warning logged.
        """

        # Check for invalid values (NaN != NaN, so use math.isnan)
        def _is_invalid(value: float | None) -> bool:
            return value is None or math.isnan(value) or math.isinf(value)

        before_invalid = _is_invalid(eoi_before)
        after_invalid = _is_invalid(eoi_after)

        if before_invalid or after_invalid:
            logger.warning(
                "record_combo_result received invalid eOI values: before=%s, after=%s "
                "for combo=%s. Treating delta as 0.0.",
                eoi_before,
                eoi_after,
                combo_id,
            )
            delta_eoi = 0.0
        else:
            # Both values are valid floats
            delta_eoi = float(eoi_after) - float(eoi_before)

        return self.update_experience(state_signature, combo_id, delta_eoi)

    def get_experience(
        self,
        state_signature: str,
        combo_id: str,
    ) -> ComboStats | None:
        """Get experience stats for a specific state-combo pair.

        Args:
            state_signature: A signature identifying the current state
            combo_id: Identifier for the combo action

        Returns:
            ComboStats if found, None otherwise
        """
        key = (state_signature, combo_id)
        with self._lock:
            return self._experience.get(key)

    def _calculate_weight(self, stats: ComboStats | None) -> float:
        """Calculate selection weight for a combo based on its stats.

        Args:
            stats: The ComboStats for this combo, or None if unknown

        Returns:
            A weight value (higher = more likely to select)
        """
        if stats is None:
            # Unknown combos get neutral weight to encourage exploration
            return 1.0

        if stats.trial_count < self.min_trials_for_confidence:
            # Not enough trials - slightly prefer to explore
            return 1.0 + (stats.ema_effectiveness * 0.5)

        # Use EMA effectiveness to adjust weight
        # Positive effectiveness -> higher weight
        # Neutral/negative effectiveness -> lower weight
        base_weight = 1.0

        if stats.ema_effectiveness > self.neutral_tolerance:
            # Positive: boost weight proportionally
            weight = base_weight + stats.ema_effectiveness * 2.0
        elif stats.ema_effectiveness < -self.neutral_tolerance:
            # Negative: reduce weight (but keep positive to allow rare exploration)
            weight = max(0.1, base_weight + stats.ema_effectiveness)
        else:
            # Neutral: slightly reduce weight to prefer tested alternatives
            weight = base_weight * 0.8

        return weight

    def select_combo(
        self,
        state_signature: str,
        available_combos: list[str],
        seed: int | None = None,
    ) -> str:
        """Select a combo using ε-greedy policy based on experience.

        With probability ε, explores by selecting randomly.
        With probability 1-ε, exploits by selecting based on weights.

        Args:
            state_signature: A signature identifying the current state
            available_combos: List of available combo IDs to choose from
            seed: Optional random seed for deterministic testing

        Returns:
            The selected combo ID

        Raises:
            ValueError: If available_combos is empty
        """
        if not available_combos:
            raise ValueError("available_combos cannot be empty")

        if len(available_combos) == 1:
            return available_combos[0]

        rng = random.Random(seed) if seed is not None else random

        with self._lock:
            self._total_selections += 1

            # ε-greedy: explore with probability ε
            if rng.random() < self.epsilon:
                self._exploration_count += 1
                selected = rng.choice(available_combos)
                logger.debug(
                    "SynergyExperience select (explore): state=%s combos=%s selected=%s",
                    state_signature,
                    available_combos,
                    selected,
                )
                return selected

            # Exploit: select based on weighted probability
            self._exploitation_count += 1

            weights = []
            for combo_id in available_combos:
                key = (state_signature, combo_id)
                stats = self._experience.get(key)
                weight = self._calculate_weight(stats)
                weights.append(weight)

            # Normalize weights
            total_weight = sum(weights)
            if total_weight <= 0:
                # Fallback to uniform selection
                selected = rng.choice(available_combos)
            else:
                # Weighted selection
                normalized = [w / total_weight for w in weights]
                r = rng.random()
                cumulative = 0.0
                selected = available_combos[-1]  # Default to last
                for combo_id, prob in zip(available_combos, normalized, strict=True):
                    cumulative += prob
                    if r <= cumulative:
                        selected = combo_id
                        break

            logger.debug(
                "SynergyExperience select (exploit): state=%s combos=%s weights=%s selected=%s",
                state_signature,
                available_combos,
                [f"{w:.3f}" for w in weights],
                selected,
            )

            return selected

    def get_combo_priority(
        self,
        state_signature: str,
        combo_id: str,
    ) -> float:
        """Get the priority/weight for a specific combo.

        Useful for external systems to query combo effectiveness.

        Args:
            state_signature: A signature identifying the current state
            combo_id: Identifier for the combo action

        Returns:
            Priority value (higher = more preferred)
        """
        key = (state_signature, combo_id)
        with self._lock:
            stats = self._experience.get(key)
            return self._calculate_weight(stats)

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics for the experience memory.

        Returns:
            Dictionary with memory statistics
        """
        with self._lock:
            return {
                "total_combos_tracked": len(self._experience),
                "total_updates": self._total_updates,
                "total_selections": self._total_selections,
                "exploration_count": self._exploration_count,
                "exploitation_count": self._exploitation_count,
                "exploration_rate": (
                    self._exploration_count / self._total_selections
                    if self._total_selections > 0
                    else 0.0
                ),
            }

    def reset(self) -> None:
        """Reset all experience memory and statistics."""
        with self._lock:
            self._experience.clear()
            self._total_updates = 0
            self._total_selections = 0
            self._exploration_count = 0
            self._exploitation_count = 0


def compute_eoi(
    memory_l1_norm: float,
    memory_l2_norm: float,
    memory_l3_norm: float,
    moral_threshold: float,
    acceptance_rate: float,
) -> float:
    """Compute the estimated Objective Index (eOI).

    eOI is a composite metric that measures the overall "health" or
    "effectiveness" of the cognitive system, combining:
    - Memory utilization across levels
    - Moral threshold stability
    - Acceptance rate balance

    Higher eOI indicates better system performance.

    Args:
        memory_l1_norm: L1 (short-term) memory utilization
        memory_l2_norm: L2 (medium-term) memory utilization
        memory_l3_norm: L3 (long-term) memory utilization
        moral_threshold: Current moral filter threshold
        acceptance_rate: Recent acceptance rate (0-1)

    Returns:
        The computed eOI value (higher is better)
    """
    # Memory utilization component (balanced usage across levels is good)
    # Penalize when L1 >> L3 (poor consolidation) or L1 << L3 (stagnation)
    total_memory = memory_l1_norm + memory_l2_norm + memory_l3_norm + EPSILON
    l1_ratio = memory_l1_norm / total_memory
    l3_ratio = memory_l3_norm / total_memory

    # Ideal: roughly balanced memory hierarchy
    memory_balance = 1.0 - abs(l1_ratio - l3_ratio)

    # Moral threshold stability (0.5 is ideal)
    moral_stability = 1.0 - abs(moral_threshold - 0.5) * 2

    # Acceptance rate balance (0.5-0.7 is ideal)
    ideal_acceptance = 0.6
    acceptance_balance = 1.0 - abs(acceptance_rate - ideal_acceptance) * 2
    acceptance_balance = max(0.0, acceptance_balance)

    # Combine components with weights
    eoi = 0.3 * memory_balance + 0.3 * moral_stability + 0.4 * acceptance_balance

    return eoi


def create_state_signature(
    phase: str,
    moral_threshold: float,
    memory_l1_norm: float,
) -> str:
    """Create a state signature for experience lookup.

    Discretizes continuous state values into a string signature that can
    be used as a key for experience lookup. Uses coarse buckets to enable
    generalization across similar states.

    Args:
        phase: Current cognitive phase ("wake" or "sleep")
        moral_threshold: Current moral filter threshold
        memory_l1_norm: L1 memory utilization

    Returns:
        A string signature representing the discretized state
    """
    # Discretize moral threshold into buckets (low/mid/high)
    if moral_threshold < 0.4:
        moral_bucket = "low"
    elif moral_threshold < 0.7:
        moral_bucket = "mid"
    else:
        moral_bucket = "high"

    # Discretize memory usage into buckets
    if memory_l1_norm < 0.3:
        memory_bucket = "sparse"
    elif memory_l1_norm < 0.7:
        memory_bucket = "normal"
    else:
        memory_bucket = "dense"

    return f"{phase}:{moral_bucket}:{memory_bucket}"
