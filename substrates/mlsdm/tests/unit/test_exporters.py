"""Unit tests for metrics exporters."""

import json

import pytest

from mlsdm.observability.exporters import PrometheusPullExporter, StdoutJsonExporter
from mlsdm.observability.metrics import MetricsRegistry


@pytest.fixture
def populated_registry():
    """Create a MetricsRegistry with sample data."""
    registry = MetricsRegistry()

    # Add sample data
    registry.increment_requests_total(100)
    registry.increment_rejections_total("pre_flight", 10)
    registry.increment_rejections_total("generation", 5)
    registry.increment_errors_total("moral_precheck", 3)
    registry.increment_errors_total("mlsdm_rejection", 7)

    # Add latency data
    for i in range(50):
        registry.record_latency_total(float(i + 10))
        registry.record_latency_pre_flight(float(i * 0.1))
        registry.record_latency_generation(float(i + 5))

    return registry


def test_prometheus_exporter_initialization(populated_registry):
    """Test PrometheusPullExporter initialization."""
    exporter = PrometheusPullExporter(populated_registry)
    assert exporter.metrics_registry == populated_registry


def test_prometheus_render_text_format(populated_registry):
    """Test that Prometheus text format is correct."""
    exporter = PrometheusPullExporter(populated_registry)
    text = exporter.render_text()

    # Check that output contains expected sections
    assert "# HELP neurocognitive_requests_total" in text
    assert "# TYPE neurocognitive_requests_total counter" in text
    assert "neurocognitive_requests_total 100" in text

    assert "# HELP neurocognitive_rejections_total" in text
    assert 'neurocognitive_rejections_total{rejected_at="pre_flight"} 10' in text
    assert 'neurocognitive_rejections_total{rejected_at="generation"} 5' in text

    assert "# HELP neurocognitive_errors_total" in text
    assert 'neurocognitive_errors_total{error_type="moral_precheck"} 3' in text
    assert 'neurocognitive_errors_total{error_type="mlsdm_rejection"} 7' in text


def test_prometheus_render_text_latency_metrics(populated_registry):
    """Test that latency metrics are rendered correctly."""
    exporter = PrometheusPullExporter(populated_registry)
    text = exporter.render_text()

    # Check latency sections
    assert "# HELP neurocognitive_latency_total_ms" in text
    assert "# TYPE neurocognitive_latency_total_ms summary" in text
    assert 'neurocognitive_latency_total_ms{quantile="0.5"}' in text
    assert 'neurocognitive_latency_total_ms{quantile="0.95"}' in text
    assert 'neurocognitive_latency_total_ms{quantile="0.99"}' in text
    assert "neurocognitive_latency_total_ms_sum" in text
    assert "neurocognitive_latency_total_ms_count 50" in text


def test_prometheus_render_text_empty_registry():
    """Test Prometheus export with empty registry."""
    registry = MetricsRegistry()
    exporter = PrometheusPullExporter(registry)
    text = exporter.render_text()

    # Should have all sections but with zero values
    assert "neurocognitive_requests_total 0" in text
    assert 'neurocognitive_rejections_total{rejected_at="none"} 0' in text
    assert 'neurocognitive_errors_total{error_type="none"} 0' in text
    assert "neurocognitive_latency_total_ms_count 0" in text


def test_stdout_json_exporter_initialization(populated_registry):
    """Test StdoutJsonExporter initialization."""
    exporter = StdoutJsonExporter(populated_registry)
    assert exporter.metrics_registry == populated_registry


def test_stdout_json_export_format(populated_registry):
    """Test that JSON export is valid and contains expected data."""
    exporter = StdoutJsonExporter(populated_registry)
    json_str = exporter.export(pretty=False)

    # Parse JSON
    data = json.loads(json_str)

    # Check structure
    assert "requests_total" in data
    assert "rejections_total" in data
    assert "errors_total" in data
    assert "latency_stats" in data

    # Check values
    assert data["requests_total"] == 100
    assert data["rejections_total"]["pre_flight"] == 10
    assert data["rejections_total"]["generation"] == 5
    assert data["errors_total"]["moral_precheck"] == 3
    assert data["errors_total"]["mlsdm_rejection"] == 7


def test_stdout_json_export_pretty(populated_registry):
    """Test that pretty JSON formatting works."""
    exporter = StdoutJsonExporter(populated_registry)

    pretty_json = exporter.export(pretty=True)
    compact_json = exporter.export(pretty=False)

    # Pretty JSON should be longer (has indentation and newlines)
    assert len(pretty_json) > len(compact_json)
    assert "\n" in pretty_json
    assert "  " in pretty_json  # Indentation


def test_stdout_json_export_latency_stats(populated_registry):
    """Test that latency statistics are included in JSON."""
    exporter = StdoutJsonExporter(populated_registry)
    json_str = exporter.export()
    data = json.loads(json_str)

    # Check latency stats structure
    assert "total_ms" in data["latency_stats"]
    assert "pre_flight_ms" in data["latency_stats"]
    assert "generation_ms" in data["latency_stats"]

    # Check that percentiles are present
    total_stats = data["latency_stats"]["total_ms"]
    assert "count" in total_stats
    assert "p50" in total_stats
    assert "p95" in total_stats
    assert "p99" in total_stats
    assert "min" in total_stats
    assert "max" in total_stats
    assert "mean" in total_stats

    # Verify counts
    assert total_stats["count"] == 50


def test_stdout_json_export_empty_registry():
    """Test JSON export with empty registry."""
    registry = MetricsRegistry()
    exporter = StdoutJsonExporter(registry)
    json_str = exporter.export()
    data = json.loads(json_str)

    # Should have structure but zero values
    assert data["requests_total"] == 0
    assert data["rejections_total"] == {}
    assert data["errors_total"] == {}

    # All latency counts should be zero
    for latency_type in ["total_ms", "pre_flight_ms", "generation_ms"]:
        assert data["latency_stats"][latency_type]["count"] == 0


def test_stdout_json_print(populated_registry, capsys):
    """Test that print() outputs to stdout."""
    exporter = StdoutJsonExporter(populated_registry)
    exporter.print(pretty=True)

    captured = capsys.readouterr()

    # Should have printed valid JSON
    data = json.loads(captured.out)
    assert data["requests_total"] == 100
