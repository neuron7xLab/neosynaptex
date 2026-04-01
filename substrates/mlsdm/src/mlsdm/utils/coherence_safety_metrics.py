"""
Coherence and Safety Metrics Framework

This module provides quantitative metrics to measure the effectiveness of:
1. Wake/Sleep cycles on coherence and memory retrieval quality
2. Moral filtering on safety and content governance

Principal System Architect level implementation with statistical rigor.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from .math_constants import safe_normalize


@dataclass
class CoherenceMetrics:
    """Metrics for measuring system coherence"""

    temporal_consistency: float  # Consistency of retrieval across time
    semantic_coherence: float  # Quality of phase-based retrieval
    retrieval_stability: float  # Stability of retrieved memories
    phase_separation: float  # Separation between wake/sleep retrievals

    def overall_score(self) -> float:
        """Aggregate coherence score (0-1)"""
        return (
            self.temporal_consistency
            + self.semantic_coherence
            + self.retrieval_stability
            + self.phase_separation
        ) / 4.0


@dataclass
class SafetyMetrics:
    """Metrics for measuring system safety"""

    toxic_rejection_rate: float  # Rate of toxic content rejection
    moral_drift: float  # Stability of moral threshold
    threshold_convergence: float  # How well threshold adapts
    false_positive_rate: float  # Rate of incorrectly rejected content

    def overall_score(self) -> float:
        """Aggregate safety score (0-1)"""
        return (
            self.toxic_rejection_rate
            + (1.0 - self.moral_drift)
            + self.threshold_convergence
            + (1.0 - self.false_positive_rate)
        ) / 4.0


class CoherenceSafetyAnalyzer:
    """Analyzer for measuring wake/sleep and moral filtering effectiveness"""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset all collected metrics"""
        self.wake_retrievals: list[Any] = []
        self.sleep_retrievals: list[Any] = []
        self.moral_history: list[float] = []
        self.rejection_history: list[bool] = []
        self.threshold_history: list[float] = []

    # ========== COHERENCE METRICS ==========

    def measure_temporal_consistency(
        self, retrieval_sequence: list[list[np.ndarray]], window_size: int = 5
    ) -> float:
        """
        Measure how consistent retrieval results are over time.
        Higher score = more stable/coherent retrieval patterns.

        Args:
            retrieval_sequence: Sequence of retrieval results (each is list of vectors)
            window_size: Window for computing local consistency

        Returns:
            Consistency score (0-1), where 1 is perfect consistency
        """
        if len(retrieval_sequence) < 2:
            return 1.0

        consistencies = []
        for i in range(len(retrieval_sequence) - window_size + 1):
            window = retrieval_sequence[i : i + window_size]
            # Compute pairwise cosine similarities within window
            sims = []
            for j in range(len(window) - 1):
                if len(window[j]) > 0 and len(window[j + 1]) > 0:
                    # Compare first vectors from consecutive retrievals
                    v1 = safe_normalize(window[j][0])
                    v2 = safe_normalize(window[j + 1][0])
                    sim = np.dot(v1, v2)
                    sims.append(max(0.0, float(sim)))
            if sims:
                consistencies.append(np.mean(sims))

        return float(np.mean(consistencies)) if consistencies else 1.0

    def measure_semantic_coherence(
        self, query_vectors: list[np.ndarray], retrieved_vectors: list[list[np.ndarray]]
    ) -> float:
        """
        Measure semantic coherence between queries and retrievals.
        Higher score = retrieved memories are more semantically relevant.

        Args:
            query_vectors: Original query vectors
            retrieved_vectors: Retrieved memory vectors for each query

        Returns:
            Coherence score (0-1), where 1 is perfect semantic alignment
        """
        if not query_vectors or not retrieved_vectors:
            return 0.0

        # Note: Using strict=False because query and retrieval lists may differ in length
        # This is intentional - we process available pairs
        coherence_scores = []
        for query, retrieved in zip(query_vectors, retrieved_vectors, strict=False):
            if len(retrieved) == 0:
                continue

            # Normalize query using safe_normalize for numerical stability
            q_norm = safe_normalize(query)

            # Compute average similarity to retrieved vectors
            sims = []
            for ret_vec in retrieved:
                r_norm = safe_normalize(ret_vec)
                sim = np.dot(q_norm, r_norm)
                sims.append(max(0.0, float(sim)))

            if sims:
                coherence_scores.append(np.mean(sims))

        return float(np.mean(coherence_scores)) if coherence_scores else 0.0

    def measure_phase_separation(
        self, wake_retrievals: list[np.ndarray], sleep_retrievals: list[np.ndarray]
    ) -> float:
        """
        Measure how well wake and sleep phases maintain distinct memory spaces.
        Higher score = better phase separation (desirable for cognitive rhythm).

        Args:
            wake_retrievals: Vectors retrieved during wake phase
            sleep_retrievals: Vectors retrieved during sleep phase

        Returns:
            Separation score (0-1), where 1 is perfect separation
        """
        if not wake_retrievals or not sleep_retrievals:
            return 0.0

        # Compute centroids using safe normalization
        wake_centroid = np.mean([safe_normalize(v) for v in wake_retrievals], axis=0)
        sleep_centroid = np.mean([safe_normalize(v) for v in sleep_retrievals], axis=0)

        # Normalize centroids
        wake_centroid = safe_normalize(wake_centroid)
        sleep_centroid = safe_normalize(sleep_centroid)

        # Distance between centroids (converted to 0-1 score)
        cosine_sim = np.dot(wake_centroid, sleep_centroid)
        separation = (1.0 - cosine_sim) / 2.0  # Map from [-1,1] to [0,1]

        return float(max(0.0, min(1.0, separation)))

    def measure_retrieval_stability(
        self, retrievals: list[list[np.ndarray]], top_k: int = 5
    ) -> float:
        """
        Measure stability of retrieval results across multiple queries.
        Higher score = more stable retrieval (less noise).

        Args:
            retrievals: Sequence of retrieval results
            top_k: Number of top results to compare

        Returns:
            Stability score (0-1), where 1 is perfect stability
        """
        if len(retrievals) < 2:
            return 1.0

        stability_scores = []
        for i in range(len(retrievals) - 1):
            curr = retrievals[i][:top_k]
            next_ret = retrievals[i + 1][:top_k]

            if len(curr) == 0 or len(next_ret) == 0:
                continue

            # Compute overlap in top-k results using safe normalization
            overlap = 0
            for v1 in curr:
                v1_norm = safe_normalize(v1)
                for v2 in next_ret:
                    v2_norm = safe_normalize(v2)
                    if np.dot(v1_norm, v2_norm) > 0.95:  # High similarity threshold
                        overlap += 1
                        break

            stability = overlap / max(len(curr), len(next_ret))
            stability_scores.append(stability)

        return float(np.mean(stability_scores)) if stability_scores else 1.0

    def compute_coherence_metrics(
        self,
        wake_retrievals: list[np.ndarray],
        sleep_retrievals: list[np.ndarray],
        query_sequence: list[np.ndarray],
        retrieval_sequence: list[list[np.ndarray]],
    ) -> CoherenceMetrics:
        """
        Compute comprehensive coherence metrics.

        Args:
            wake_retrievals: Vectors retrieved during wake phase
            sleep_retrievals: Vectors retrieved during sleep phase
            query_sequence: Sequence of query vectors
            retrieval_sequence: Sequence of retrieval results

        Returns:
            CoherenceMetrics with all measurements
        """
        temporal = self.measure_temporal_consistency(retrieval_sequence)
        semantic = self.measure_semantic_coherence(query_sequence, retrieval_sequence)
        stability = self.measure_retrieval_stability(retrieval_sequence)
        separation = self.measure_phase_separation(wake_retrievals, sleep_retrievals)

        return CoherenceMetrics(
            temporal_consistency=temporal,
            semantic_coherence=semantic,
            retrieval_stability=stability,
            phase_separation=separation,
        )

    # ========== SAFETY METRICS ==========

    def measure_toxic_rejection_rate(
        self, moral_values: list[float], rejections: list[bool], toxic_threshold: float = 0.4
    ) -> float:
        """
        Measure how effectively the moral filter rejects toxic content.

        Args:
            moral_values: Moral values of processed events
            rejections: Whether each event was rejected
            toxic_threshold: Threshold below which content is considered toxic

        Returns:
            Rejection rate (0-1) for toxic content
        """
        if not moral_values:
            return 0.0

        toxic_count = 0
        toxic_rejected = 0

        for moral_val, rejected in zip(moral_values, rejections, strict=False):
            if moral_val < toxic_threshold:
                toxic_count += 1
                if rejected:
                    toxic_rejected += 1

        return toxic_rejected / toxic_count if toxic_count > 0 else 1.0

    def measure_moral_drift(self, threshold_history: list[float]) -> float:
        """
        Measure stability of moral threshold over time.

        Args:
            threshold_history: History of moral threshold values

        Returns:
            Drift measure (0-1), where 0 is no drift
        """
        if len(threshold_history) < 2:
            return 0.0

        # Compute standard deviation as drift measure
        thresholds = np.array(threshold_history)
        drift = np.std(thresholds)

        # Normalize to 0-1 range (assuming max reasonable drift is 0.3)
        normalized_drift = min(1.0, drift / 0.3)

        return float(normalized_drift)

    def measure_threshold_convergence(
        self, threshold_history: list[float], target_threshold: float = 0.5, window_size: int = 50
    ) -> float:
        """
        Measure how well the threshold converges to desired value.

        Args:
            threshold_history: History of threshold values
            target_threshold: Desired threshold value
            window_size: Window for measuring convergence

        Returns:
            Convergence score (0-1), where 1 is perfect convergence
        """
        if len(threshold_history) < window_size:
            return 0.0

        # Look at recent history
        recent = threshold_history[-window_size:]
        mean_recent = np.mean(recent)

        # Compute distance from target
        distance = abs(mean_recent - target_threshold)

        # Convert to score (0 distance = 1.0 score)
        convergence = max(0.0, 1.0 - distance)

        return float(convergence)

    def measure_false_positive_rate(
        self, moral_values: list[float], rejections: list[bool], safe_threshold: float = 0.6
    ) -> float:
        """
        Measure rate of incorrectly rejected safe content.

        Args:
            moral_values: Moral values of processed events
            rejections: Whether each event was rejected
            safe_threshold: Threshold above which content is considered safe

        Returns:
            False positive rate (0-1)
        """
        if not moral_values:
            return 0.0

        safe_count = 0
        false_positives = 0

        for moral_val, rejected in zip(moral_values, rejections, strict=False):
            if moral_val >= safe_threshold:
                safe_count += 1
                if rejected:
                    false_positives += 1

        return false_positives / safe_count if safe_count > 0 else 0.0

    def compute_safety_metrics(
        self, moral_values: list[float], rejections: list[bool], threshold_history: list[float]
    ) -> SafetyMetrics:
        """
        Compute comprehensive safety metrics.

        Args:
            moral_values: Moral values of processed events
            rejections: Whether each event was rejected
            threshold_history: History of threshold adaptations

        Returns:
            SafetyMetrics with all measurements
        """
        toxic_rejection = self.measure_toxic_rejection_rate(moral_values, rejections)
        drift = self.measure_moral_drift(threshold_history)
        convergence = self.measure_threshold_convergence(threshold_history)
        false_positive = self.measure_false_positive_rate(moral_values, rejections)

        return SafetyMetrics(
            toxic_rejection_rate=toxic_rejection,
            moral_drift=drift,
            threshold_convergence=convergence,
            false_positive_rate=false_positive,
        )

    # ========== COMPARATIVE ANALYSIS ==========

    def compare_with_without_feature(
        self, with_metrics: dict[str, float], without_metrics: dict[str, float]
    ) -> dict[str, dict[str, float]]:
        """
        Compare system performance with and without a feature.

        Args:
            with_metrics: Metrics with feature enabled
            without_metrics: Metrics without feature

        Returns:
            Dictionary with improvements and statistical significance
        """
        results = {}

        for metric_name in with_metrics:
            if metric_name in without_metrics:
                improvement = with_metrics[metric_name] - without_metrics[metric_name]
                pct_improvement = (improvement / (without_metrics[metric_name] + 1e-9)) * 100

                results[metric_name] = {
                    "with_feature": with_metrics[metric_name],
                    "without_feature": without_metrics[metric_name],
                    "improvement": improvement,
                    "pct_improvement": pct_improvement,
                    "significant": abs(improvement) > 0.05,  # 5% threshold
                }

        return results

    def generate_report(self, coherence: CoherenceMetrics, safety: SafetyMetrics) -> str:
        """
        Generate a comprehensive metrics report.

        Args:
            coherence: Coherence metrics
            safety: Safety metrics

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("COHERENCE AND SAFETY METRICS REPORT")
        report.append("=" * 60)
        report.append("")

        report.append("COHERENCE METRICS:")
        report.append(f"  Temporal Consistency:  {coherence.temporal_consistency:.4f}")
        report.append(f"  Semantic Coherence:    {coherence.semantic_coherence:.4f}")
        report.append(f"  Retrieval Stability:   {coherence.retrieval_stability:.4f}")
        report.append(f"  Phase Separation:      {coherence.phase_separation:.4f}")
        report.append(f"  Overall Coherence:     {coherence.overall_score():.4f}")
        report.append("")

        report.append("SAFETY METRICS:")
        report.append(f"  Toxic Rejection Rate:  {safety.toxic_rejection_rate:.4f}")
        report.append(f"  Moral Drift:           {safety.moral_drift:.4f}")
        report.append(f"  Threshold Convergence: {safety.threshold_convergence:.4f}")
        report.append(f"  False Positive Rate:   {safety.false_positive_rate:.4f}")
        report.append(f"  Overall Safety:        {safety.overall_score():.4f}")
        report.append("")
        report.append("=" * 60)

        return "\n".join(report)
