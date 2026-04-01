"""Prometheus-compatible metrics for Aphasia-Broca observability.

This module provides specialized metrics for monitoring aphasia detection and
repair decisions. Metrics are designed to be aggregated by Prometheus without
exposing any sensitive content (prompts, responses, or PII).

Metrics:
- aphasia_events_total: Counter for aphasia detection/repair events
- aphasia_severity_histogram: Histogram of aphasia severity scores
- aphasia_flags_total: Counter for individual aphasia flags detected
"""

from threading import Lock

from prometheus_client import CollectorRegistry, Counter, Histogram


class AphasiaMetricsExporter:
    """Prometheus-compatible metrics exporter for Aphasia-Broca detection.

    Provides:
    - Counters: aphasia_events_total, aphasia_flags_total
    - Histograms: aphasia_severity_histogram
    """

    def __init__(self, registry: CollectorRegistry | None = None):
        """Initialize aphasia metrics exporter.

        Args:
            registry: Optional custom Prometheus registry. If None, creates new one.
        """
        self.registry = registry or CollectorRegistry()
        self._lock = Lock()

        # Counter for aphasia events with labels for mode, detection status, and repair
        self.aphasia_events_total = Counter(
            "mlsdm_aphasia_events_total",
            "Total number of aphasia detection/repair events",
            ["mode", "is_aphasic", "repair_applied"],
            registry=self.registry,
        )

        # Histogram for aphasia severity scores (0.0 to 1.0)
        # Buckets are designed for granular visibility into severity distribution
        self.aphasia_severity_histogram = Histogram(
            "mlsdm_aphasia_severity",
            "Histogram of aphasia severity scores (0.0 to 1.0)",
            buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry,
        )

        # Counter for individual aphasia flags detected
        self.aphasia_flags_total = Counter(
            "mlsdm_aphasia_flags_total",
            "Total count of individual aphasia flags detected",
            ["flag"],
            registry=self.registry,
        )

    def record_aphasia_event(
        self,
        mode: str,
        is_aphasic: bool,
        repair_applied: bool,
        severity: float,
        flags: list[str],
    ) -> None:
        """Record an aphasia detection/repair event.

        This method updates all aphasia-related metrics atomically.
        Only metadata is recorded - no content or PII is stored.

        Args:
            mode: Detection mode ('full', 'monitor', 'disabled')
            is_aphasic: Whether aphasia was detected
            repair_applied: Whether repair was applied to the response
            severity: Aphasia severity score (0.0 to 1.0)
            flags: List of aphasia flags detected (e.g., 'short_sentences')
        """
        with self._lock:
            # Increment event counter with labels
            self.aphasia_events_total.labels(
                mode=mode,
                is_aphasic=str(is_aphasic),
                repair_applied=str(repair_applied),
            ).inc()

            # Record severity in histogram
            self.aphasia_severity_histogram.observe(severity)

            # Increment flag counters
            for flag in flags:
                self.aphasia_flags_total.labels(flag=flag).inc()


# Global instance for convenience
_aphasia_metrics_exporter: AphasiaMetricsExporter | None = None
_aphasia_metrics_exporter_lock = Lock()


def get_aphasia_metrics_exporter(
    registry: CollectorRegistry | None = None,
) -> AphasiaMetricsExporter:
    """Get or create the aphasia metrics exporter instance.

    This function is thread-safe and implements the singleton pattern.

    Note:
        The registry parameter is only used when creating the singleton instance.
        Subsequent calls with a different registry parameter will be ignored
        and the existing singleton will be returned.

    Args:
        registry: Optional custom Prometheus registry (only used on first call)

    Returns:
        AphasiaMetricsExporter instance
    """
    global _aphasia_metrics_exporter

    # Double-checked locking pattern for thread-safe singleton
    if _aphasia_metrics_exporter is None:
        with _aphasia_metrics_exporter_lock:
            if _aphasia_metrics_exporter is None:
                _aphasia_metrics_exporter = AphasiaMetricsExporter(registry=registry)

    return _aphasia_metrics_exporter


def reset_aphasia_metrics_exporter() -> None:
    """Reset the global aphasia metrics exporter instance.

    This is primarily used for testing to ensure a clean state between tests.
    """
    global _aphasia_metrics_exporter

    with _aphasia_metrics_exporter_lock:
        _aphasia_metrics_exporter = None
