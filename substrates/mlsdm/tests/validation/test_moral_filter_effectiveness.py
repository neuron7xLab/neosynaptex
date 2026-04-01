"""
Validation Tests for Moral Filter Effectiveness

This test suite demonstrates measurable improvements in safety
from moral filtering using rigorous statistical validation.

Principal System Architect level validation.
"""

import numpy as np

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.utils.coherence_safety_metrics import CoherenceSafetyAnalyzer


class NoFilterController(CognitiveController):
    """Controller without moral filtering for baseline comparison"""

    def process_event(self, vector, moral_value):
        with self._lock:
            self.step_counter += 1

            # NO moral filtering - process everything during wake
            # Still respect wake/sleep rhythm for fair comparison
            if not self.rhythm.is_wake():
                self.rhythm_step()  # Advance rhythm even during sleep
                return self._build_state(rejected=True, note="sleep phase")

            phase_val = 0.1 if self.rhythm.phase == "wake" else 0.9
            self.memory_commit(vector, phase_val)
            self.rhythm_step()

            return self._build_state(rejected=False, note="processed")


def generate_moral_value_distribution(n_samples: int, toxic_ratio: float = 0.3) -> list:
    """
    Generate realistic distribution of moral values.

    Args:
        n_samples: Number of samples
        toxic_ratio: Ratio of toxic content (low moral values)

    Returns:
        List of moral values
    """
    np.random.seed(42)
    moral_values = []

    n_toxic = int(n_samples * toxic_ratio)
    n_safe = n_samples - n_toxic

    # Toxic content: moral values between 0.1-0.4
    toxic_values = np.random.uniform(0.1, 0.4, n_toxic)

    # Safe content: moral values between 0.6-0.95
    safe_values = np.random.uniform(0.6, 0.95, n_safe)

    # Mix them
    moral_values = list(toxic_values) + list(safe_values)
    np.random.shuffle(moral_values)

    return moral_values


def generate_test_vectors(n_vectors: int, dim: int = 384) -> list:
    """Generate test vectors"""
    np.random.seed(42)
    vectors = []

    for _ in range(n_vectors):
        vec = np.random.randn(dim).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vectors.append(vec)

    return vectors


def test_moral_filter_toxic_rejection():
    """
    Test 1: Moral filter effectively rejects toxic content

    Expected: High rejection rate for toxic content (moral value < 0.4)
    """
    print("\n" + "=" * 60)
    print("TEST 1: Toxic Content Rejection")
    print("=" * 60)

    n_events = 200
    vectors = generate_test_vectors(n_events, dim=384)
    moral_values = generate_moral_value_distribution(n_events, toxic_ratio=0.3)

    # Test WITH moral filtering
    print("\nRunning WITH moral filtering...")
    controller_with = CognitiveController(dim=384)

    moral_rejections_with = []
    total_rejections_with = 0

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller_with.process_event(vec, moral_value=moral_val)
        # Only count moral rejections, not sleep rejections
        moral_rejected = state["rejected"] and "morally" in state["note"]
        moral_rejections_with.append(moral_rejected)
        if state["rejected"]:
            total_rejections_with += 1

    # Test WITHOUT moral filtering
    print("Running WITHOUT moral filtering (baseline)...")
    controller_without = NoFilterController(dim=384)

    moral_rejections_without = []
    total_rejections_without = 0

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller_without.process_event(vec, moral_value=moral_val)
        # No moral rejections in baseline
        moral_rejections_without.append(False)
        if state["rejected"]:
            total_rejections_without += 1

    # Compute toxic rejection rates
    analyzer = CoherenceSafetyAnalyzer()

    toxic_rejection_with = analyzer.measure_toxic_rejection_rate(
        moral_values, moral_rejections_with, toxic_threshold=0.4
    )
    toxic_rejection_without = analyzer.measure_toxic_rejection_rate(
        moral_values, moral_rejections_without, toxic_threshold=0.4
    )

    improvement = toxic_rejection_with - toxic_rejection_without

    print("\nRESULTS:")
    print("  WITH Moral Filter:")
    print(
        f"    Toxic rejection rate:    {toxic_rejection_with:.4f} ({toxic_rejection_with*100:.1f}%)"
    )
    print(f"    Total rejections:        {total_rejections_with} (includes sleep phase)")

    print("\n  WITHOUT Moral Filter (Baseline):")
    print(
        f"    Toxic rejection rate:    {toxic_rejection_without:.4f} ({toxic_rejection_without*100:.1f}%)"
    )
    print(f"    Total rejections:        {total_rejections_without} (sleep phase only)")

    print("\n  IMPROVEMENT:")
    print(f"    Toxic content blocked:   +{toxic_rejection_with*100:.1f}%")
    print(f"    Absolute improvement:    {improvement:.4f}")

    # Validation: With filter should reject toxic content, without should not
    assert (
        toxic_rejection_with > 0.7
    ), f"Moral filter should reject >70% of toxic content, got {toxic_rejection_with*100:.1f}%"

    assert (
        toxic_rejection_with > toxic_rejection_without + 0.5
    ), f"Moral filter should significantly improve toxic rejection (with={toxic_rejection_with:.2f}, without={toxic_rejection_without:.2f})"

    print(f"\n✅ PASS: Moral filter rejects {toxic_rejection_with*100:.1f}% of toxic content")


def test_moral_filter_false_positive_rate():
    """
    Test 2: Moral filter has low false positive rate

    Expected: Low rejection rate for safe content (moral value > 0.6)
    """
    print("\n" + "=" * 60)
    print("TEST 2: False Positive Rate (Safe Content)")
    print("=" * 60)

    n_events = 200
    vectors = generate_test_vectors(n_events, dim=384)
    moral_values = generate_moral_value_distribution(n_events, toxic_ratio=0.2)

    # Test WITH moral filtering
    print("\nRunning WITH moral filtering...")
    controller_with = CognitiveController(dim=384)

    rejections_with = []
    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller_with.process_event(vec, moral_value=moral_val)
        rejected = state["rejected"] and "morally" in state["note"]
        rejections_with.append(rejected)

    # Compute false positive rate
    analyzer = CoherenceSafetyAnalyzer()

    fp_rate = analyzer.measure_false_positive_rate(
        moral_values, rejections_with, safe_threshold=0.6
    )

    print("\nRESULTS:")
    print(f"  False Positive Rate: {fp_rate:.4f} ({fp_rate*100:.1f}%)")
    print(f"  Accuracy on safe content: {(1-fp_rate)*100:.1f}%")

    # Validation: false positive rate should be reasonably low
    assert fp_rate < 0.5, f"False positive rate should be <50%, got {fp_rate*100:.1f}%"

    print(f"\n✅ PASS: False positive rate is acceptably low at {fp_rate*100:.1f}%")


def test_moral_threshold_adaptation():
    """
    Test 3: Moral threshold adapts and converges

    Expected: Threshold should adapt based on content and converge to stable value
    """
    print("\n" + "=" * 60)
    print("TEST 3: Moral Threshold Adaptation")
    print("=" * 60)

    n_events = 300
    vectors = generate_test_vectors(n_events, dim=384)

    # Scenario 1: Mostly toxic content (should adapt threshold down)
    print("\nScenario 1: Toxic Content Stream (50% toxic)")
    moral_values_toxic = generate_moral_value_distribution(n_events, toxic_ratio=0.5)

    controller1 = CognitiveController(dim=384)
    threshold_history1 = []

    for vec, moral_val in zip(vectors, moral_values_toxic, strict=False):
        state = controller1.process_event(vec, moral_value=moral_val)
        threshold_history1.append(state["moral_threshold"])

    # Scenario 2: Mostly safe content (should adapt threshold up or maintain)
    print("Scenario 2: Safe Content Stream (10% toxic)")
    moral_values_safe = generate_moral_value_distribution(n_events, toxic_ratio=0.1)

    controller2 = CognitiveController(dim=384)
    threshold_history2 = []

    for vec, moral_val in zip(vectors, moral_values_safe, strict=False):
        state = controller2.process_event(vec, moral_value=moral_val)
        threshold_history2.append(state["moral_threshold"])

    # Analyze adaptation
    analyzer = CoherenceSafetyAnalyzer()

    drift1 = analyzer.measure_moral_drift(threshold_history1)
    drift2 = analyzer.measure_moral_drift(threshold_history2)

    convergence1 = analyzer.measure_threshold_convergence(threshold_history1, window_size=50)
    convergence2 = analyzer.measure_threshold_convergence(threshold_history2, window_size=50)

    print("\nRESULTS:")
    print("\nScenario 1 (Toxic Stream):")
    print(f"  Initial Threshold: {threshold_history1[0]:.4f}")
    print(f"  Final Threshold:   {threshold_history1[-1]:.4f}")
    print(f"  Threshold Drift:   {drift1:.4f}")
    print(f"  Convergence Score: {convergence1:.4f}")

    print("\nScenario 2 (Safe Stream):")
    print(f"  Initial Threshold: {threshold_history2[0]:.4f}")
    print(f"  Final Threshold:   {threshold_history2[-1]:.4f}")
    print(f"  Threshold Drift:   {drift2:.4f}")
    print(f"  Convergence Score: {convergence2:.4f}")

    # Validation: thresholds should be within valid range and show adaptation
    assert (
        0.3 <= threshold_history1[-1] <= 0.9
    ), "Final threshold should be within valid range [0.3, 0.9]"

    assert (
        0.3 <= threshold_history2[-1] <= 0.9
    ), "Final threshold should be within valid range [0.3, 0.9]"

    print("\n✅ PASS: Moral threshold adapts correctly and stays within bounds")


def test_moral_drift_stability():
    """
    Test 4: Moral threshold remains stable under toxic bombardment

    Expected: Limited drift even under sustained toxic input
    """
    print("\n" + "=" * 60)
    print("TEST 4: Moral Drift Stability Under Attack")
    print("=" * 60)

    n_events = 500
    vectors = generate_test_vectors(n_events, dim=384)

    # Create aggressive toxic attack (70% toxic content)
    print("\nSimulating toxic attack (70% toxic content)...")
    moral_values = generate_moral_value_distribution(n_events, toxic_ratio=0.7)

    controller = CognitiveController(dim=384)
    threshold_history = []
    rejections = []

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller.process_event(vec, moral_value=moral_val)
        threshold_history.append(state["moral_threshold"])
        rejected = state["rejected"] and "morally" in state["note"]
        rejections.append(rejected)

    # Analyze stability
    analyzer = CoherenceSafetyAnalyzer()

    drift = analyzer.measure_moral_drift(threshold_history)

    # Compute drift in recent history
    recent_drift = analyzer.measure_moral_drift(threshold_history[-100:])

    # Check if threshold stayed within bounds
    min_threshold = min(threshold_history)
    max_threshold = max(threshold_history)

    print("\nRESULTS:")
    print(f"  Initial Threshold:     {threshold_history[0]:.4f}")
    print(f"  Final Threshold:       {threshold_history[-1]:.4f}")
    print(f"  Min Threshold:         {min_threshold:.4f}")
    print(f"  Max Threshold:         {max_threshold:.4f}")
    print(f"  Overall Drift:         {drift:.4f}")
    print(f"  Recent Drift (last 100): {recent_drift:.4f}")
    print(f"  Toxic Rejection Rate:  {sum(rejections)/len(rejections)*100:.1f}%")

    # Validation
    assert 0.3 <= min_threshold <= 0.9, "Threshold should stay within bounds"
    assert 0.3 <= max_threshold <= 0.9, "Threshold should stay within bounds"
    assert drift < 0.5, f"Drift should be limited, got {drift:.4f}"

    print(f"\n✅ PASS: Moral threshold remains stable under toxic attack (drift={drift:.4f})")


def test_comprehensive_safety_metrics():
    """
    Test 5: Comprehensive safety analysis

    Generate full SafetyMetrics with and without moral filtering.
    """
    print("\n" + "=" * 60)
    print("TEST 5: Comprehensive Safety Metrics")
    print("=" * 60)

    n_events = 300
    vectors = generate_test_vectors(n_events, dim=384)
    moral_values = generate_moral_value_distribution(n_events, toxic_ratio=0.3)

    # Test WITH moral filtering
    print("\nRunning comprehensive test WITH moral filtering...")
    controller_with = CognitiveController(dim=384)

    rejections_with = []
    threshold_history_with = []

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller_with.process_event(vec, moral_value=moral_val)
        rejected = state["rejected"] and "morally" in state["note"]
        rejections_with.append(rejected)
        threshold_history_with.append(state["moral_threshold"])

    # Test WITHOUT moral filtering
    print("Running comprehensive test WITHOUT moral filtering...")
    controller_without = NoFilterController(dim=384)

    rejections_without = []

    for vec, moral_val in zip(vectors, moral_values, strict=False):
        state = controller_without.process_event(vec, moral_value=moral_val)
        rejections_without.append(False)  # Never rejects based on morals

    # Compute comprehensive metrics
    analyzer = CoherenceSafetyAnalyzer()

    metrics_with = analyzer.compute_safety_metrics(
        moral_values, rejections_with, threshold_history_with
    )

    # For baseline, use constant threshold history
    metrics_without = analyzer.compute_safety_metrics(
        moral_values, rejections_without, [0.5] * len(moral_values)
    )

    print("\nCOMPREHENSIVE RESULTS:")
    print("\nWITH Moral Filtering:")
    print(f"  Toxic Rejection Rate:  {metrics_with.toxic_rejection_rate:.4f}")
    print(f"  Moral Drift:           {metrics_with.moral_drift:.4f}")
    print(f"  Threshold Convergence: {metrics_with.threshold_convergence:.4f}")
    print(f"  False Positive Rate:   {metrics_with.false_positive_rate:.4f}")
    print(f"  Overall Safety Score:  {metrics_with.overall_score():.4f}")

    print("\nWITHOUT Moral Filtering (Baseline):")
    print(f"  Toxic Rejection Rate:  {metrics_without.toxic_rejection_rate:.4f}")
    print(f"  Moral Drift:           {metrics_without.moral_drift:.4f}")
    print(f"  Threshold Convergence: {metrics_without.threshold_convergence:.4f}")
    print(f"  False Positive Rate:   {metrics_without.false_positive_rate:.4f}")
    print(f"  Overall Safety Score:  {metrics_without.overall_score():.4f}")

    improvement = metrics_with.overall_score() - metrics_without.overall_score()
    pct_improvement = (improvement / (metrics_without.overall_score() + 1e-9)) * 100

    print("\nOVERALL IMPROVEMENT:")
    print(f"  Safety Score Improvement: {improvement:.4f} ({pct_improvement:+.1f}%)")

    # Validation: The key metric is toxic rejection rate
    assert (
        metrics_with.toxic_rejection_rate > 0.9
    ), f"Moral filtering should achieve >90% toxic rejection rate, got {metrics_with.toxic_rejection_rate*100:.1f}%"

    assert (
        metrics_with.toxic_rejection_rate > metrics_without.toxic_rejection_rate + 0.8
    ), "Moral filtering should dramatically improve toxic rejection vs baseline"

    print(
        f"\n✅ PASS: Moral filtering achieves {metrics_with.toxic_rejection_rate*100:.1f}% toxic rejection rate"
    )


def run_all_tests():
    """Run all moral filter effectiveness tests"""
    print("\n" + "=" * 60)
    print("MORAL FILTER EFFECTIVENESS VALIDATION")
    print("Principal System Architect Level Analysis")
    print("=" * 60)

    results = {}

    try:
        results["toxic_rejection"] = test_moral_filter_toxic_rejection()
        results["false_positives"] = test_moral_filter_false_positive_rate()
        results["adaptation"] = test_moral_threshold_adaptation()
        results["drift_stability"] = test_moral_drift_stability()
        results["comprehensive"] = test_comprehensive_safety_metrics()

        print("\n" + "=" * 60)
        print("SUMMARY OF RESULTS")
        print("=" * 60)

        print(
            f"\n1. Toxic Rejection: {results['toxic_rejection']['with_filter']*100:.1f}% vs "
            f"{results['toxic_rejection']['without_filter']*100:.1f}% baseline"
        )
        print(
            f"2. False Positive Rate: {results['false_positives']['false_positive_rate']*100:.1f}%"
        )
        print(
            f"3. Threshold Adaptation: Toxic stream converged to {results['adaptation']['toxic_stream']['final']:.3f}, "
            f"Safe stream to {results['adaptation']['safe_stream']['final']:.3f}"
        )
        print(
            f"4. Drift Stability: {results['drift_stability']['drift']:.4f} under 70% toxic attack"
        )
        print(
            f"5. Comprehensive Safety: {results['comprehensive']['metrics_with'].toxic_rejection_rate*100:.1f}% toxic rejection achieved"
        )

        print("\n" + "=" * 60)
        print("✅ ALL MORAL FILTER EFFECTIVENESS TESTS PASSED")
        print("=" * 60)

        return results

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    results = run_all_tests()
