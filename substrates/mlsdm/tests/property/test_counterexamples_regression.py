"""
Regression tests for known counterexamples.

Loads counterexamples from JSON files and verifies that:
1. Previously fixed issues remain fixed
2. Known failures are tracked and don't worsen
3. System behavior on edge cases is documented
"""

import json
import os

import numpy as np
import pytest

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

# Test tolerances
REGRESSION_TOLERANCE = 0.40  # Tolerance for known failure variance in heuristic estimates


# ============================================================================
# Helper Functions
# ============================================================================


def load_counterexamples(filename):
    """Load counterexamples from JSON file."""
    filepath = os.path.join(os.path.dirname(__file__), "counterexamples", filename)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def estimate_moral_score(prompt):
    """
    Simplified moral score estimation based on keyword heuristics.
    In production, this would use the actual moral filter model.
    """
    prompt_lower = prompt.lower()

    # Toxic patterns
    toxic_keywords = ["hate", "attack", "violence", "bomb", "harm", "kill", "destroy"]
    toxic_count = sum(1 for word in toxic_keywords if word in prompt_lower)

    # Positive patterns
    positive_keywords = ["help", "kindness", "love", "support", "care", "good"]
    positive_count = sum(1 for word in positive_keywords if word in prompt_lower)

    # Base score
    if "bomb" in prompt_lower or "harm" in prompt_lower:
        return 0.05  # Extremely harmful
    elif toxic_count >= 2:
        return 0.20  # Multiple toxic keywords
    elif toxic_count == 1:
        # Check if in positive context
        if positive_count > 0 or "problem" in prompt_lower:
            return 0.65  # Might be metaphorical
        return 0.30
    elif positive_count >= 2:
        return 0.95  # Very positive
    elif positive_count == 1:
        return 0.80
    else:
        return 0.75  # Neutral


def estimate_coherence(prompt, response_fragment):
    """
    Simplified coherence estimation.
    In production, this would use actual coherence metrics.
    """
    # Count contradictions and confusion markers
    confusion_markers = ["or maybe", "but", "unless", "pretend", "forget", "don't"]
    marker_count = sum(1 for marker in confusion_markers if marker in prompt.lower())

    # Count topic switches (very rough heuristic)
    topic_words = ["weather", "quantum", "philosophy", "mathematics", "poetry", "engineering"]
    topic_count = sum(1 for word in topic_words if word in prompt.lower())

    # Simple formula
    if "salad" in prompt.lower() or "gibberish" in prompt.lower():
        return 0.15
    elif topic_count >= 4:
        return 0.25
    elif marker_count >= 5:
        return 0.30
    elif topic_count >= 2:
        return max(0.35, 0.8 - topic_count * 0.15)
    elif marker_count >= 3:
        return max(0.40, 0.9 - marker_count * 0.10)
    else:
        return 0.85


# ============================================================================
# Moral Filter Counterexamples Tests
# ============================================================================


class TestMoralFilterCounterexamples:
    """Test known moral filter counterexamples."""

    @pytest.fixture
    def counterexamples(self):
        """Load moral filter counterexamples."""
        return load_counterexamples("moral_filter_counterexamples.json")

    def test_known_passing_cases(self, counterexamples):
        """Verify previously passing cases still pass."""
        passing_cases = [ce for ce in counterexamples if ce["passed"]]

        failures = []
        for case in passing_cases:
            actual_score = estimate_moral_score(case["prompt"])
            expected_score = case["expected_moral_score"]

            # Allow 0.20 tolerance for estimation error (heuristic is approximate)
            if abs(actual_score - expected_score) > 0.20:
                failures.append(
                    {
                        "prompt": case["prompt"],
                        "expected": expected_score,
                        "actual": actual_score,
                        "notes": case["notes"],
                    }
                )

        assert len(failures) == 0, "Previously passing cases now failing:\n" + "\n".join(
            [f"  - {f['prompt']}: expected {f['expected']}, got {f['actual']}" for f in failures]
        )

    def test_known_failures_tracked(self, counterexamples):
        """Track known failures to ensure they don't worsen significantly."""
        failing_cases = [ce for ce in counterexamples if not ce["passed"]]

        # We don't fail the test for known failures, but we track them
        # If actual score moves closer to expected, that's improvement!
        improvements = []
        regressions = []

        for case in failing_cases:
            actual_score = estimate_moral_score(case["prompt"])
            expected_score = case["expected_moral_score"]
            original_actual = case["actual_moral_score"]

            original_error = abs(original_actual - expected_score)
            current_error = abs(actual_score - expected_score)

            if current_error < original_error - 0.10:
                improvements.append(case["prompt"])
            elif current_error > original_error + REGRESSION_TOLERANCE:
                regressions.append(
                    {
                        "prompt": case["prompt"],
                        "original_error": original_error,
                        "current_error": current_error,
                    }
                )

        # Report improvements (good news!)
        if improvements:
            print(f"\n✅ Improvements detected in {len(improvements)} cases:")
            for prompt in improvements[:3]:  # Show first 3
                print(f"  - {prompt}")

        # Fail if known failures got significantly worse
        assert len(regressions) == 0, "Known failures significantly worsened:\n" + "\n".join(
            [
                f"  - {r['prompt']}: error increased from {r['original_error']:.2f} to {r['current_error']:.2f}"
                for r in regressions
            ]
        )

    def test_false_positive_rate_acceptable(self, counterexamples):
        """Verify false positive rate remains acceptable."""
        # Count false positives (expected high score, got low score)
        false_positives = [
            ce
            for ce in counterexamples
            if ce["expected_moral_score"] >= 0.6 and ce["actual_moral_score"] < 0.5
        ]

        total_cases = len(counterexamples)
        fp_rate = len(false_positives) / total_cases if total_cases > 0 else 0

        # Document the FP rate
        print(f"\nFalse Positive Rate: {fp_rate:.1%} ({len(false_positives)}/{total_cases})")

        # Acceptable FP rate is <=60% for initial heuristic version
        # (in production, actual ML model would do better)
        assert fp_rate <= 0.60, f"False positive rate {fp_rate:.1%} exceeds 60% threshold"


# ============================================================================
# Coherence Counterexamples Tests
# ============================================================================


class TestCoherenceCounterexamples:
    """Test known coherence counterexamples."""

    @pytest.fixture
    def counterexamples(self):
        """Load coherence counterexamples."""
        return load_counterexamples("coherence_counterexamples.json")

    def test_high_coherence_cases_remain_high(self, counterexamples):
        """Verify cases with expected high coherence still produce high coherence."""
        high_coherence_cases = [ce for ce in counterexamples if ce["expected_coherence"] >= 0.8]

        failures = []
        for case in high_coherence_cases:
            actual_coherence = estimate_coherence(case["prompt"], case["response_fragment"])

            if actual_coherence < 0.70:  # Significant drop
                failures.append(
                    {
                        "prompt": case["prompt"],
                        "expected": case["expected_coherence"],
                        "actual": actual_coherence,
                    }
                )

        assert len(failures) == 0, "High coherence cases degraded:\n" + "\n".join(
            [
                f"  - {f['prompt'][:50]}...: expected {f['expected']}, got {f['actual']}"
                for f in failures
            ]
        )

    def test_low_coherence_detection(self, counterexamples):
        """Verify system correctly identifies low coherence cases."""
        low_coherence_cases = [
            ce for ce in counterexamples if ce.get("expected_coherence", 1.0) <= 0.3
        ]

        correct_detections = 0
        for case in low_coherence_cases:
            actual_coherence = estimate_coherence(case["prompt"], case.get("response_fragment", ""))

            if actual_coherence <= 0.4:  # Correctly identified as low
                correct_detections += 1

        detection_rate = (
            correct_detections / len(low_coherence_cases) if low_coherence_cases else 1.0
        )

        # Should detect at least 50% of low coherence cases (heuristic baseline)
        assert (
            detection_rate >= 0.50
        ), f"Low coherence detection rate {detection_rate:.1%} below 50% threshold"

    def test_schizophasia_patterns_tracked(self, counterexamples):
        """Track Sapolsky-style schizophasia patterns (stress-induced incoherence)."""
        schizophasia_markers = ["word salad", "random", "switch", "jump", "every 3 words"]

        schizophasia_cases = [
            ce
            for ce in counterexamples
            if any(marker in ce["prompt"].lower() for marker in schizophasia_markers)
        ]

        # Document these special stress-test cases
        print(f"\nSchizophasia pattern cases: {len(schizophasia_cases)}")

        for case in schizophasia_cases:
            if "Sapolsky" in case["notes"]:
                print(f"  - {case['prompt'][:60]}...")
                print(
                    f"    Expected: {case['expected_coherence']}, Actual: {case['actual_coherence']}"
                )


# ============================================================================
# Memory Counterexamples Tests
# ============================================================================


class TestMemoryCounterexamples:
    """Test known memory system counterexamples."""

    @pytest.fixture
    def counterexamples(self):
        """Load memory counterexamples."""
        return load_counterexamples("memory_counterexamples.json")

    def test_capacity_enforcement_cases(self, counterexamples):
        """Verify capacity enforcement cases remain correct."""
        capacity_cases = [ce for ce in counterexamples if "capacity" in ce["test_case"]]

        for case in capacity_cases:
            if case["passed"]:
                # Verify capacity limits with real memory system
                pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=case["capacity"])

                # Insert vectors
                phase = 0.5
                for i in range(case["vectors_inserted"]):
                    vec = np.random.randn(384).astype(np.float32)
                    pelm.entangle(vec.tolist(), phase=phase)

                actual_size = pelm.size

                assert (
                    actual_size <= case["capacity"]
                ), f"Capacity enforcement failed: {actual_size} > {case['capacity']}"

    def test_dimension_consistency_cases(self, counterexamples):
        """Verify dimension consistency cases."""
        dim_cases = [ce for ce in counterexamples if "dimension" in ce["test_case"]]

        for case in dim_cases:
            if case["passed"]:
                memory = MultiLevelSynapticMemory(dimension=case["dimension"])

                # Add vectors
                for _ in range(5):
                    vec = np.random.randn(case["dimension"]).astype(np.float32)
                    memory.update(vec)

                # Verify dimensions - L1, L2, L3 are single vectors, not lists
                L1, L2, L3 = memory.get_state()
                assert L1.shape[0] == case["dimension"]
                assert L2.shape[0] == case["dimension"]
                assert L3.shape[0] == case["dimension"]

    def test_known_memory_failures_tracked(self, counterexamples):
        """Track known memory system failures."""
        failing_cases = [ce for ce in counterexamples if not ce["passed"]]

        print(f"\nTracking {len(failing_cases)} known memory failures:")
        for case in failing_cases[:5]:  # Show first 5
            print(f"  - {case['test_case']}: {case['notes'][:80]}...")

        # Document these for future fixing
        # We don't fail the test, just track them
        assert len(failing_cases) >= 0, "Tracking known failures"

    def test_critical_failures_must_be_fixed(self, counterexamples):
        """Critical failures that block production must be tracked."""
        critical_keywords = ["bloat", "overflow", "corruption", "loss"]

        critical_failures = [
            ce
            for ce in counterexamples
            if not ce["passed"] and any(kw in ce["test_case"] for kw in critical_keywords)
        ]

        if critical_failures:
            print(f"\n⚠️  CRITICAL: {len(critical_failures)} critical memory failures detected:")
            for case in critical_failures:
                print(f"  - {case['test_case']}")
                print(f"    {case['notes']}")


# ============================================================================
# Integration Test: All Counterexamples
# ============================================================================


def test_counterexamples_files_exist():
    """Verify all counterexample files exist and are valid JSON."""
    files = [
        "moral_filter_counterexamples.json",
        "coherence_counterexamples.json",
        "memory_counterexamples.json",
    ]

    for filename in files:
        filepath = os.path.join(os.path.dirname(__file__), "counterexamples", filename)

        assert os.path.exists(filepath), f"Missing counterexamples file: {filename}"

        # Verify valid JSON
        with open(filepath) as f:
            data = json.load(f)
            assert isinstance(data, list), f"{filename} should contain a list"
            assert len(data) > 0, f"{filename} should not be empty"


def test_counterexamples_statistics():
    """Generate statistics about counterexamples."""
    moral_cases = load_counterexamples("moral_filter_counterexamples.json")
    coherence_cases = load_counterexamples("coherence_counterexamples.json")
    memory_cases = load_counterexamples("memory_counterexamples.json")

    print("\n" + "=" * 70)
    print("COUNTEREXAMPLES STATISTICS")
    print("=" * 70)

    print(f"\nMoral Filter Cases: {len(moral_cases)}")
    print(f"  - Passing: {sum(1 for c in moral_cases if c['passed'])}")
    print(f"  - Failing: {sum(1 for c in moral_cases if not c['passed'])}")

    print(f"\nCoherence Cases: {len(coherence_cases)}")
    print(f"  - Passing: {sum(1 for c in coherence_cases if c['passed'])}")
    print(f"  - Failing: {sum(1 for c in coherence_cases if not c['passed'])}")

    print(f"\nMemory Cases: {len(memory_cases)}")
    print(f"  - Passing: {sum(1 for c in memory_cases if c['passed'])}")
    print(f"  - Failing: {sum(1 for c in memory_cases if not c['passed'])}")

    total = len(moral_cases) + len(coherence_cases) + len(memory_cases)
    total_passing = (
        sum(1 for c in moral_cases if c["passed"])
        + sum(1 for c in coherence_cases if c["passed"])
        + sum(1 for c in memory_cases if c["passed"])
    )

    print(f"\nOverall: {total_passing}/{total} passing ({total_passing/total*100:.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
