"""
Tests for Synergy Experience Learning Module.

Tests cover:
- Experience memory initialization and basic operations
- Delta eOI classification (positive, neutral, negative)
- ε-greedy combo selection policy
- Learning adaptation over multiple trials
- Thread safety
"""

import pytest

from mlsdm.cognition.synergy_experience import (
    ComboStats,
    SynergyExperienceMemory,
    compute_eoi,
    create_state_signature,
)


class TestComboStats:
    """Tests for ComboStats dataclass."""

    def test_initial_state(self) -> None:
        """Test initial stats are zeroed."""
        stats = ComboStats()
        assert stats.trial_count == 0
        assert stats.total_delta_eoi == 0.0
        assert stats.last_delta_eoi == 0.0
        assert stats.ema_effectiveness == 0.0

    def test_avg_delta_eoi_empty(self) -> None:
        """Test avg_delta_eoi returns 0 when no trials."""
        stats = ComboStats()
        assert stats.avg_delta_eoi == 0.0

    def test_single_update(self) -> None:
        """Test single update sets all values correctly."""
        stats = ComboStats()
        stats.update(0.5)

        assert stats.trial_count == 1
        assert stats.total_delta_eoi == 0.5
        assert stats.last_delta_eoi == 0.5
        assert stats.avg_delta_eoi == 0.5
        assert stats.ema_effectiveness == 0.5  # First update sets EMA directly

    def test_multiple_updates(self) -> None:
        """Test multiple updates accumulate correctly."""
        stats = ComboStats()
        stats.update(0.2)
        stats.update(0.4)
        stats.update(0.6)

        assert stats.trial_count == 3
        assert stats.total_delta_eoi == pytest.approx(1.2)
        assert stats.last_delta_eoi == 0.6
        assert stats.avg_delta_eoi == pytest.approx(0.4)

    def test_ema_smoothing(self) -> None:
        """Test EMA applies exponential smoothing."""
        stats = ComboStats()
        stats.update(1.0)
        stats.update(0.0)

        # EMA = 0.2 * 0.0 + 0.8 * 1.0 = 0.8
        assert stats.ema_effectiveness == pytest.approx(0.8)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        stats = ComboStats()
        stats.update(0.5)
        d = stats.to_dict()

        assert d["trial_count"] == 1
        assert d["avg_delta_eoi"] == 0.5
        assert d["last_delta_eoi"] == 0.5
        assert d["ema_effectiveness"] == 0.5


class TestSynergyExperienceMemory:
    """Tests for SynergyExperienceMemory."""

    def test_initialization_default(self) -> None:
        """Test default initialization."""
        memory = SynergyExperienceMemory()
        assert memory.epsilon == 0.1
        assert memory.neutral_tolerance == 0.01
        assert memory.min_trials_for_confidence == 3

    def test_initialization_custom(self) -> None:
        """Test custom initialization."""
        memory = SynergyExperienceMemory(
            epsilon=0.2,
            neutral_tolerance=0.05,
            min_trials_for_confidence=5,
        )
        assert memory.epsilon == 0.2
        assert memory.neutral_tolerance == 0.05
        assert memory.min_trials_for_confidence == 5

    def test_initialization_invalid_epsilon(self) -> None:
        """Test epsilon validation."""
        with pytest.raises(ValueError, match="epsilon must be in"):
            SynergyExperienceMemory(epsilon=1.5)

        with pytest.raises(ValueError, match="epsilon must be in"):
            SynergyExperienceMemory(epsilon=-0.1)

    def test_initialization_invalid_tolerance(self) -> None:
        """Test neutral_tolerance validation."""
        with pytest.raises(ValueError, match="neutral_tolerance must be non-negative"):
            SynergyExperienceMemory(neutral_tolerance=-0.1)

    def test_update_experience_new_combo(self) -> None:
        """Test updating experience for a new combo."""
        memory = SynergyExperienceMemory()
        stats = memory.update_experience("state_1", "combo_A", 0.1)

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.1

    def test_update_experience_existing_combo(self) -> None:
        """Test updating experience for existing combo."""
        memory = SynergyExperienceMemory()
        memory.update_experience("state_1", "combo_A", 0.1)
        stats = memory.update_experience("state_1", "combo_A", 0.2)

        assert stats.trial_count == 2
        assert stats.last_delta_eoi == 0.2
        assert stats.avg_delta_eoi == pytest.approx(0.15)

    def test_get_experience_found(self) -> None:
        """Test getting experience for known combo."""
        memory = SynergyExperienceMemory()
        memory.update_experience("state_1", "combo_A", 0.1)

        stats = memory.get_experience("state_1", "combo_A")
        assert stats is not None
        assert stats.trial_count == 1

    def test_get_experience_not_found(self) -> None:
        """Test getting experience for unknown combo."""
        memory = SynergyExperienceMemory()
        stats = memory.get_experience("state_1", "combo_A")
        assert stats is None

    def test_select_combo_single_option(self) -> None:
        """Test selection with single combo returns that combo."""
        memory = SynergyExperienceMemory()
        selected = memory.select_combo("state_1", ["combo_A"], seed=42)
        assert selected == "combo_A"

    def test_select_combo_empty_raises(self) -> None:
        """Test selection with empty list raises."""
        memory = SynergyExperienceMemory()
        with pytest.raises(ValueError, match="available_combos cannot be empty"):
            memory.select_combo("state_1", [])

    def test_select_combo_exploration_deterministic(self) -> None:
        """Test exploration mode selects randomly with seed."""
        # Use epsilon=1.0 to force exploration
        memory = SynergyExperienceMemory(epsilon=1.0)
        combos = ["combo_A", "combo_B", "combo_C"]

        # Should be deterministic with seed
        selected1 = memory.select_combo("state_1", combos, seed=42)
        selected2 = memory.select_combo("state_1", combos, seed=42)
        assert selected1 == selected2

    def test_select_combo_exploitation_prefers_positive(self) -> None:
        """Test exploitation mode prefers positive combos."""
        # Use epsilon=0.0 to force exploitation
        memory = SynergyExperienceMemory(epsilon=0.0, min_trials_for_confidence=1)

        # Train combo_A to be positive
        for _ in range(5):
            memory.update_experience("state_1", "combo_A", 0.5)

        # Train combo_B to be negative
        for _ in range(5):
            memory.update_experience("state_1", "combo_B", -0.5)

        # combo_A should be selected more often (weighted selection)
        selections = [
            memory.select_combo("state_1", ["combo_A", "combo_B"], seed=i) for i in range(10)
        ]

        combo_a_count = selections.count("combo_A")
        assert combo_a_count >= 5  # Should prefer combo_A (majority)

    def test_get_combo_priority(self) -> None:
        """Test priority calculation for combos."""
        memory = SynergyExperienceMemory(min_trials_for_confidence=1)

        # Unknown combo gets neutral priority
        priority_unknown = memory.get_combo_priority("state_1", "combo_X")
        assert priority_unknown == 1.0

        # Train positive combo
        for _ in range(3):
            memory.update_experience("state_1", "combo_A", 0.5)

        priority_positive = memory.get_combo_priority("state_1", "combo_A")
        assert priority_positive > 1.0  # Should be boosted

        # Train negative combo
        for _ in range(3):
            memory.update_experience("state_1", "combo_B", -0.5)

        priority_negative = memory.get_combo_priority("state_1", "combo_B")
        assert priority_negative < priority_positive

    def test_get_stats(self) -> None:
        """Test getting overall memory statistics."""
        memory = SynergyExperienceMemory()

        memory.update_experience("state_1", "combo_A", 0.1)
        memory.update_experience("state_1", "combo_B", 0.2)
        memory.select_combo("state_1", ["combo_A", "combo_B"], seed=42)

        stats = memory.get_stats()
        assert stats["total_combos_tracked"] == 2
        assert stats["total_updates"] == 2
        assert stats["total_selections"] == 1

    def test_reset(self) -> None:
        """Test resetting memory clears all data."""
        memory = SynergyExperienceMemory()

        memory.update_experience("state_1", "combo_A", 0.1)
        memory.select_combo("state_1", ["combo_A"], seed=42)

        memory.reset()

        stats = memory.get_stats()
        assert stats["total_combos_tracked"] == 0
        assert stats["total_updates"] == 0
        assert stats["total_selections"] == 0


class TestNeutralComboLearning:
    """Tests specifically for neutral combo handling (reviewer concern)."""

    def test_neutral_combo_priority_decreases(self) -> None:
        """Test: Neutral combos (delta_eoi ≈ 0) become less favored over time."""
        memory = SynergyExperienceMemory(
            epsilon=0.0,
            neutral_tolerance=0.01,
            min_trials_for_confidence=3,
        )

        # Train combo_A to be neutral (delta_eoi ≈ 0)
        for _ in range(10):
            memory.update_experience("state_1", "combo_A", 0.001)  # Nearly zero

        # Train combo_B to be moderately positive
        for _ in range(10):
            memory.update_experience("state_1", "combo_B", 0.1)

        # combo_B should be preferred over neutral combo_A
        priority_neutral = memory.get_combo_priority("state_1", "combo_A")
        priority_positive = memory.get_combo_priority("state_1", "combo_B")

        assert priority_positive > priority_neutral
        assert priority_neutral < 1.0  # Neutral gets reduced weight

    def test_neutral_combo_selected_less_frequently(self) -> None:
        """Test: After many neutral trials, combo is selected less often."""
        memory = SynergyExperienceMemory(
            epsilon=0.0,
            neutral_tolerance=0.01,
            min_trials_for_confidence=3,
        )

        # Train combo_A with many neutral results
        for _ in range(20):
            memory.update_experience("state_1", "combo_A", 0.005)

        # Train combo_B with positive results
        for _ in range(20):
            memory.update_experience("state_1", "combo_B", 0.1)

        # Select 100 times and count
        selections = [
            memory.select_combo("state_1", ["combo_A", "combo_B"], seed=i) for i in range(100)
        ]

        combo_a_count = selections.count("combo_A")
        combo_b_count = selections.count("combo_B")

        # combo_B should be selected more often (weighted selection gives preference)
        assert combo_b_count > combo_a_count


class TestPositiveComboLearning:
    """Tests for positive combo learning behavior."""

    def test_positive_combo_priority_increases(self) -> None:
        """Test: Positive combos gain higher priority."""
        memory = SynergyExperienceMemory(min_trials_for_confidence=1)

        # Get initial priority (unknown)
        initial_priority = memory.get_combo_priority("state_1", "combo_A")

        # Train with positive results
        for _ in range(5):
            memory.update_experience("state_1", "combo_A", 0.3)

        final_priority = memory.get_combo_priority("state_1", "combo_A")
        assert final_priority > initial_priority

    def test_positive_combo_dominates_selection(self) -> None:
        """Test: Positive combos are selected more frequently."""
        memory = SynergyExperienceMemory(epsilon=0.0, min_trials_for_confidence=3)

        # Train combo_A to be positive
        for _ in range(10):
            memory.update_experience("state_1", "combo_A", 0.5)

        # Train combo_B to be slightly positive
        for _ in range(10):
            memory.update_experience("state_1", "combo_B", 0.1)

        # combo_A should be selected more often
        selections = [
            memory.select_combo("state_1", ["combo_A", "combo_B"], seed=i) for i in range(100)
        ]

        combo_a_count = selections.count("combo_A")
        combo_b_count = selections.count("combo_B")
        assert combo_a_count > combo_b_count  # Better combo selected more


class TestNegativeComboLearning:
    """Tests for negative combo learning behavior."""

    def test_negative_combo_priority_decreases(self) -> None:
        """Test: Negative combos have reduced priority."""
        memory = SynergyExperienceMemory(min_trials_for_confidence=1)

        # Train with negative results
        for _ in range(5):
            memory.update_experience("state_1", "combo_A", -0.5)

        priority = memory.get_combo_priority("state_1", "combo_A")
        assert priority < 1.0  # Below neutral

    def test_negative_combo_rarely_selected(self) -> None:
        """Test: Negative combos are selected less frequently."""
        memory = SynergyExperienceMemory(epsilon=0.0, min_trials_for_confidence=3)

        # Train combo_A to be negative
        for _ in range(10):
            memory.update_experience("state_1", "combo_A", -0.5)

        # Train combo_B to be slightly positive
        for _ in range(10):
            memory.update_experience("state_1", "combo_B", 0.1)

        # combo_B should be selected more often
        selections = [
            memory.select_combo("state_1", ["combo_A", "combo_B"], seed=i) for i in range(100)
        ]

        combo_a_count = selections.count("combo_A")
        combo_b_count = selections.count("combo_B")
        assert combo_b_count > combo_a_count  # Positive combo preferred


class TestEOIComputation:
    """Tests for eOI computation."""

    def test_balanced_state_high_eoi(self) -> None:
        """Test balanced state produces high eOI."""
        eoi = compute_eoi(
            memory_l1_norm=0.5,
            memory_l2_norm=0.5,
            memory_l3_norm=0.5,
            moral_threshold=0.5,
            acceptance_rate=0.6,
        )
        assert eoi > 0.7  # Should be high

    def test_imbalanced_memory_lower_eoi(self) -> None:
        """Test imbalanced memory reduces eOI."""
        balanced_eoi = compute_eoi(
            memory_l1_norm=0.5,
            memory_l2_norm=0.5,
            memory_l3_norm=0.5,
            moral_threshold=0.5,
            acceptance_rate=0.6,
        )

        imbalanced_eoi = compute_eoi(
            memory_l1_norm=1.0,
            memory_l2_norm=0.1,
            memory_l3_norm=0.0,
            moral_threshold=0.5,
            acceptance_rate=0.6,
        )

        assert imbalanced_eoi < balanced_eoi

    def test_extreme_moral_threshold_lower_eoi(self) -> None:
        """Test extreme moral threshold reduces eOI."""
        balanced_eoi = compute_eoi(
            memory_l1_norm=0.5,
            memory_l2_norm=0.5,
            memory_l3_norm=0.5,
            moral_threshold=0.5,
            acceptance_rate=0.6,
        )

        extreme_eoi = compute_eoi(
            memory_l1_norm=0.5,
            memory_l2_norm=0.5,
            memory_l3_norm=0.5,
            moral_threshold=0.9,  # Very high
            acceptance_rate=0.6,
        )

        assert extreme_eoi < balanced_eoi


class TestStateSignature:
    """Tests for state signature creation."""

    def test_wake_low_sparse(self) -> None:
        """Test wake state with low moral and sparse memory."""
        sig = create_state_signature("wake", 0.3, 0.2)
        assert sig == "wake:low:sparse"

    def test_sleep_high_dense(self) -> None:
        """Test sleep state with high moral and dense memory."""
        sig = create_state_signature("sleep", 0.8, 0.8)
        assert sig == "sleep:high:dense"

    def test_wake_mid_normal(self) -> None:
        """Test wake state with mid moral and normal memory."""
        sig = create_state_signature("wake", 0.5, 0.5)
        assert sig == "wake:mid:normal"

    def test_signature_consistency(self) -> None:
        """Test same inputs produce same signature."""
        sig1 = create_state_signature("wake", 0.5, 0.5)
        sig2 = create_state_signature("wake", 0.5, 0.5)
        assert sig1 == sig2


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_updates(self) -> None:
        """Test concurrent updates don't cause data corruption."""
        import queue
        import threading

        memory = SynergyExperienceMemory()
        num_threads = 10
        updates_per_thread = 100
        error_queue: queue.Queue[Exception] = queue.Queue()

        def update_thread(thread_id: int) -> None:
            try:
                for i in range(updates_per_thread):
                    memory.update_experience(
                        f"state_{thread_id}",
                        f"combo_{i % 5}",
                        float(thread_id) / 10,
                    )
            except Exception as e:
                error_queue.put(e)

        threads = [threading.Thread(target=update_thread, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert error_queue.empty(), f"Thread errors: {list(error_queue.queue)}"
        stats = memory.get_stats()
        assert stats["total_updates"] == num_threads * updates_per_thread


class TestEdgeCases:
    """Tests for edge cases including NaN/inf handling."""

    def test_nan_delta_eoi_treated_as_zero(self) -> None:
        """Test NaN delta_eoi is treated as 0.0."""
        import math

        memory = SynergyExperienceMemory()
        stats = memory.update_experience("state_1", "combo_A", float("nan"))

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0
        assert not math.isnan(stats.ema_effectiveness)

    def test_inf_delta_eoi_treated_as_zero(self) -> None:
        """Test infinity delta_eoi is treated as 0.0."""
        import math

        memory = SynergyExperienceMemory()
        stats = memory.update_experience("state_1", "combo_A", float("inf"))

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0
        assert not math.isinf(stats.ema_effectiveness)

    def test_negative_inf_delta_eoi_treated_as_zero(self) -> None:
        """Test negative infinity delta_eoi is treated as 0.0."""
        memory = SynergyExperienceMemory()
        stats = memory.update_experience("state_1", "combo_A", float("-inf"))

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0

    def test_combo_stats_update_handles_nan(self) -> None:
        """Test ComboStats.update handles NaN gracefully."""
        import math

        stats = ComboStats()
        stats.update(float("nan"))

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0
        assert not math.isnan(stats.avg_delta_eoi)

    def test_record_combo_result_with_valid_values(self) -> None:
        """Test record_combo_result with valid eOI values."""
        memory = SynergyExperienceMemory()
        stats = memory.record_combo_result("state_1", "combo_A", 0.3, 0.5)

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == pytest.approx(0.2)

    def test_record_combo_result_with_nan_before(self) -> None:
        """Test record_combo_result handles NaN in eoi_before."""
        memory = SynergyExperienceMemory()
        stats = memory.record_combo_result("state_1", "combo_A", float("nan"), 0.5)

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0

    def test_record_combo_result_with_nan_after(self) -> None:
        """Test record_combo_result handles NaN in eoi_after."""
        memory = SynergyExperienceMemory()
        stats = memory.record_combo_result("state_1", "combo_A", 0.3, float("nan"))

        assert stats.trial_count == 1
        assert stats.last_delta_eoi == 0.0

    def test_combo_stats_aliases(self) -> None:
        """Test ComboStats property aliases work correctly."""
        stats = ComboStats()
        stats.update(0.5)
        stats.update(0.3)

        # Test aliases
        assert stats.attempts == stats.trial_count
        assert stats.mean_delta_eoi == stats.avg_delta_eoi
        assert stats.ema_delta_eoi == stats.ema_effectiveness

    def test_combo_stats_to_dict_has_all_fields(self) -> None:
        """Test to_dict includes all expected fields."""
        stats = ComboStats()
        stats.update(0.5)
        d = stats.to_dict()

        # New field names
        assert "attempts" in d
        assert "mean_delta_eoi" in d
        assert "ema_delta_eoi" in d

        # Legacy field names for backward compatibility
        assert "trial_count" in d
        assert "avg_delta_eoi" in d
        assert "ema_effectiveness" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
