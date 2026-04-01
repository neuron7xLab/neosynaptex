"""Metrics exporters for NeuroCognitiveEngine.

This module provides exporters that can output metrics in various formats:
- PrometheusPullExporter: Prometheus text format
- StdoutJsonExporter: JSON format for logging/debugging
"""

import json
from typing import Any


class PrometheusPullExporter:
    """Exporter for Prometheus pull-based scraping.

    Converts MetricsRegistry data to Prometheus text format.
    """

    def __init__(self, metrics_registry: Any) -> None:
        """Initialize exporter with metrics registry.

        Args:
            metrics_registry: MetricsRegistry instance to export
        """
        self.metrics_registry = metrics_registry

    def render_text(self) -> str:
        """Render metrics in Prometheus text exposition format.

        Returns:
            String in Prometheus format
        """
        snapshot = self.metrics_registry.get_snapshot()
        lines: list[str] = []

        # Requests total
        lines.append("# HELP neurocognitive_requests_total Total number of requests")
        lines.append("# TYPE neurocognitive_requests_total counter")
        lines.append(f"neurocognitive_requests_total {snapshot['requests_total']}")
        lines.append("")

        # Rejections total (with labels)
        lines.append("# HELP neurocognitive_rejections_total Total number of rejections by stage")
        lines.append("# TYPE neurocognitive_rejections_total counter")
        for rejected_at, count in snapshot["rejections_total"].items():
            lines.append(f'neurocognitive_rejections_total{{rejected_at="{rejected_at}"}} {count}')
        if not snapshot["rejections_total"]:
            lines.append('neurocognitive_rejections_total{rejected_at="none"} 0')
        lines.append("")

        # Errors total (with labels)
        lines.append("# HELP neurocognitive_errors_total Total number of errors by type")
        lines.append("# TYPE neurocognitive_errors_total counter")
        for error_type, count in snapshot["errors_total"].items():
            lines.append(f'neurocognitive_errors_total{{error_type="{error_type}"}} {count}')
        if not snapshot["errors_total"]:
            lines.append('neurocognitive_errors_total{error_type="none"} 0')
        lines.append("")

        # Latency histograms
        summary = self.metrics_registry.get_summary()

        for latency_type, stats in summary["latency_stats"].items():
            metric_name = f"neurocognitive_latency_{latency_type}"
            lines.append(f"# HELP {metric_name} Latency for {latency_type}")
            lines.append(f"# TYPE {metric_name} summary")

            if stats["count"] > 0:
                lines.append(f'{metric_name}{{quantile="0.5"}} {stats["p50"]:.2f}')
                lines.append(f'{metric_name}{{quantile="0.95"}} {stats["p95"]:.2f}')
                lines.append(f'{metric_name}{{quantile="0.99"}} {stats["p99"]:.2f}')
                lines.append(f'{metric_name}_sum {stats["mean"] * stats["count"]:.2f}')
                lines.append(f'{metric_name}_count {stats["count"]}')
            else:
                lines.append(f'{metric_name}{{quantile="0.5"}} 0')
                lines.append(f'{metric_name}{{quantile="0.95"}} 0')
                lines.append(f'{metric_name}{{quantile="0.99"}} 0')
                lines.append(f"{metric_name}_sum 0")
                lines.append(f"{metric_name}_count 0")
            lines.append("")

        return "\n".join(lines)


class StdoutJsonExporter:
    """Exporter that outputs metrics summary as JSON to stdout.

    Useful for debugging and logging.
    """

    def __init__(self, metrics_registry: Any) -> None:
        """Initialize exporter with metrics registry.

        Args:
            metrics_registry: MetricsRegistry instance to export
        """
        self.metrics_registry = metrics_registry

    def export(self, pretty: bool = True) -> str:
        """Export metrics as JSON string.

        Args:
            pretty: If True, format JSON with indentation

        Returns:
            JSON string representation of metrics
        """
        summary = self.metrics_registry.get_summary()

        if pretty:
            return json.dumps(summary, indent=2, sort_keys=True)
        return json.dumps(summary, sort_keys=True)

    def print(self, pretty: bool = True) -> None:
        """Print metrics to stdout as JSON.

        Args:
            pretty: If True, format JSON with indentation
        """
        print(self.export(pretty=pretty))
