"""
Canary deployment manager for progressive LLM rollouts.

Manages gradual rollout of new LLM models/providers with automatic
rollback based on error rates and performance metrics.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class VersionMetrics:
    """Metrics for a deployed version."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        return 1.0 - self.error_rate

    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests


class CanaryManager:
    """Manages canary deployment of new LLM versions.

    Features:
    - Gradual traffic ramp-up to candidate version
    - Automatic rollback on high error rates
    - Error budget management
    - Optional latency-based decision making

    Example:
        >>> manager = CanaryManager(
        ...     current_version="gpt-3.5-turbo",
        ...     candidate_version="gpt-4",
        ...     candidate_ratio=0.1,
        ...     error_budget_threshold=0.05
        ... )
        >>> version = manager.select_version()
        >>> manager.report_outcome(version, success=True, latency_ms=100.0)
    """

    def __init__(
        self,
        current_version: str,
        candidate_version: str,
        candidate_ratio: float = 0.1,
        error_budget_threshold: float = 0.05,
        min_requests_before_decision: int = 100,
        auto_rollback_enabled: bool = True,
        latency_threshold_multiplier: float | None = None,
    ) -> None:
        """Initialize canary manager.

        Args:
            current_version: Stable production version identifier
            candidate_version: New version being tested
            candidate_ratio: Initial traffic ratio for candidate (0.0 to 1.0)
            error_budget_threshold: Maximum acceptable error rate for candidate
            min_requests_before_decision: Minimum requests before making rollback decisions
            auto_rollback_enabled: If True, automatically reduce candidate_ratio on errors
            latency_threshold_multiplier: If set, also consider latency
                                         (candidate avg latency should be < current * multiplier)

        Raises:
            ValueError: If parameters are invalid
        """
        if not 0.0 <= candidate_ratio <= 1.0:
            raise ValueError(f"candidate_ratio must be between 0.0 and 1.0, got {candidate_ratio}")

        if not 0.0 <= error_budget_threshold <= 1.0:
            raise ValueError(
                f"error_budget_threshold must be between 0.0 and 1.0, "
                f"got {error_budget_threshold}"
            )

        if min_requests_before_decision < 1:
            raise ValueError(
                f"min_requests_before_decision must be >= 1, " f"got {min_requests_before_decision}"
            )

        self.current_version = current_version
        self.candidate_version = candidate_version
        self._candidate_ratio = candidate_ratio
        self.error_budget_threshold = error_budget_threshold
        self.min_requests_before_decision = min_requests_before_decision
        self.auto_rollback_enabled = auto_rollback_enabled
        self.latency_threshold_multiplier = latency_threshold_multiplier

        # Metrics tracking
        self._metrics: dict[str, VersionMetrics] = {
            current_version: VersionMetrics(),
            candidate_version: VersionMetrics(),
        }

        self._lock = Lock()
        self._rollback_triggered = False

    @property
    def candidate_ratio(self) -> float:
        """Get current candidate traffic ratio."""
        with self._lock:
            return self._candidate_ratio

    def set_candidate_ratio(self, ratio: float) -> None:
        """Set candidate traffic ratio.

        Args:
            ratio: New ratio (0.0 to 1.0)

        Raises:
            ValueError: If ratio is invalid
        """
        if not 0.0 <= ratio <= 1.0:
            raise ValueError(f"ratio must be between 0.0 and 1.0, got {ratio}")

        with self._lock:
            self._candidate_ratio = ratio

    def select_version(self) -> str:
        """Select version based on current candidate ratio.

        Uses random sampling to distribute traffic.

        Returns:
            Version identifier (current_version or candidate_version)
        """
        with self._lock:
            if self._candidate_ratio == 0.0:
                return self.current_version

            if self._candidate_ratio == 1.0:
                return self.candidate_version

            if random.random() < self._candidate_ratio:
                return self.candidate_version
            return self.current_version

    def report_outcome(
        self,
        version: str,
        success: bool,
        latency_ms: float | None = None,
    ) -> None:
        """Report outcome of a request to a specific version.

        Updates metrics and triggers auto-rollback if error budget is exceeded.

        Args:
            version: Version that handled the request
            success: Whether the request succeeded
            latency_ms: Request latency in milliseconds (optional)
        """
        with self._lock:
            if version not in self._metrics:
                self._metrics[version] = VersionMetrics()

            metrics = self._metrics[version]
            metrics.total_requests += 1

            if success:
                metrics.successful_requests += 1
                if latency_ms is not None:
                    metrics.total_latency_ms += latency_ms
            else:
                metrics.failed_requests += 1

            # Check for auto-rollback conditions
            if self.auto_rollback_enabled and not self._rollback_triggered:
                self._check_and_trigger_rollback()

    def _check_and_trigger_rollback(self) -> None:
        """Check if rollback conditions are met and trigger if necessary.

        Rollback conditions:
        1. Candidate has enough requests for statistical significance
        2. Candidate error rate exceeds threshold
        3. (Optional) Candidate latency significantly worse than current

        Note: This method should be called while holding self._lock
        """
        candidate_metrics = self._metrics[self.candidate_version]

        # Need minimum requests before making decisions
        if candidate_metrics.total_requests < self.min_requests_before_decision:
            return

        # Check error rate
        if candidate_metrics.error_rate > self.error_budget_threshold:
            # Trigger rollback
            self._candidate_ratio = 0.0
            self._rollback_triggered = True
            return

        # Check latency if threshold is set
        if self.latency_threshold_multiplier is not None:
            current_metrics = self._metrics[self.current_version]

            # Need current version metrics for comparison
            if current_metrics.successful_requests >= self.min_requests_before_decision:
                current_avg = current_metrics.average_latency_ms
                candidate_avg = candidate_metrics.average_latency_ms

                # Candidate latency significantly worse
                if candidate_avg > current_avg * self.latency_threshold_multiplier:
                    self._candidate_ratio = 0.0
                    self._rollback_triggered = True
                    return

    def get_metrics(self, version: str | None = None) -> dict[str, Any]:
        """Get metrics for a version or all versions.

        Args:
            version: Version identifier (if None, returns all versions)

        Returns:
            Dictionary with metrics
        """
        with self._lock:
            if version is not None:
                if version not in self._metrics:
                    return {}

                metrics = self._metrics[version]
                return {
                    "version": version,
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "failed_requests": metrics.failed_requests,
                    "error_rate": metrics.error_rate,
                    "success_rate": metrics.success_rate,
                    "average_latency_ms": metrics.average_latency_ms,
                }
            else:
                # Return all metrics
                return {
                    "current_version": self.current_version,
                    "candidate_version": self.candidate_version,
                    "candidate_ratio": self._candidate_ratio,
                    "rollback_triggered": self._rollback_triggered,
                    "versions": {
                        ver: {
                            "total_requests": m.total_requests,
                            "successful_requests": m.successful_requests,
                            "failed_requests": m.failed_requests,
                            "error_rate": m.error_rate,
                            "success_rate": m.success_rate,
                            "average_latency_ms": m.average_latency_ms,
                        }
                        for ver, m in self._metrics.items()
                    },
                }

    def is_rollback_triggered(self) -> bool:
        """Check if automatic rollback has been triggered.

        Returns:
            True if rollback was triggered due to error budget or latency
        """
        with self._lock:
            return self._rollback_triggered

    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing or restarting canary)."""
        with self._lock:
            self._metrics = {
                self.current_version: VersionMetrics(),
                self.candidate_version: VersionMetrics(),
            }
            self._rollback_triggered = False

    def promote_candidate(self) -> None:
        """Promote candidate to current version.

        This sets candidate_ratio to 1.0, effectively making the candidate
        the primary version. In a real deployment, this would typically be
        followed by updating the current_version to the candidate and
        introducing a new candidate.
        """
        with self._lock:
            self._candidate_ratio = 1.0
