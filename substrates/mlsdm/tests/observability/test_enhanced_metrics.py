"""
Tests for enhanced observability metrics (OBS-001).

These tests verify that the new metrics added for production observability
are properly registered and functional.
"""

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.metrics import MetricsExporter


@pytest.fixture
def fresh_metrics():
    """Create a fresh MetricsExporter with its own registry for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


class TestHTTPLevelMetrics:
    """Tests for HTTP-level metrics (OBS-001 enhancement)."""

    def test_http_requests_total_with_labels(self, fresh_metrics):
        """Test HTTP requests counter with method, endpoint, and status labels."""
        fresh_metrics.increment_http_requests("GET", "/health", "200", 5)
        fresh_metrics.increment_http_requests("POST", "/generate", "200", 10)
        fresh_metrics.increment_http_requests("POST", "/generate", "500", 2)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_http_requests_total" in metrics_text
        assert 'method="GET"' in metrics_text
        assert 'method="POST"' in metrics_text
        assert 'endpoint="/health"' in metrics_text
        assert 'endpoint="/generate"' in metrics_text
        assert 'status="200"' in metrics_text
        assert 'status="500"' in metrics_text

    def test_http_request_latency_histogram(self, fresh_metrics):
        """Test HTTP request latency histogram with endpoint labels."""
        fresh_metrics.observe_http_request_latency(0.05, "/generate")
        fresh_metrics.observe_http_request_latency(0.10, "/generate")
        fresh_metrics.observe_http_request_latency(0.25, "/infer")

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_http_request_latency_seconds_bucket" in metrics_text
        assert "mlsdm_http_request_latency_seconds_bucket_bucket" not in metrics_text
        assert 'endpoint="/generate"' in metrics_text
        assert 'endpoint="/infer"' in metrics_text

    def test_http_requests_in_flight(self, fresh_metrics):
        """Test HTTP requests in-flight gauge."""
        fresh_metrics.increment_http_requests_in_flight()
        fresh_metrics.increment_http_requests_in_flight()
        assert fresh_metrics.http_requests_in_flight._value.get() == 2

        fresh_metrics.decrement_http_requests_in_flight()
        assert fresh_metrics.http_requests_in_flight._value.get() == 1

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_http_requests_in_flight 1" in metrics_text


class TestLLMIntegrationMetrics:
    """Tests for LLM integration metrics (OBS-001 enhancement)."""

    def test_llm_request_latency_by_model(self, fresh_metrics):
        """Test LLM request latency histogram with model labels."""
        fresh_metrics.observe_llm_request_latency(0.5, "gpt-4")
        fresh_metrics.observe_llm_request_latency(1.0, "gpt-4")
        fresh_metrics.observe_llm_request_latency(0.3, "claude-3")

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_llm_request_latency_seconds_bucket" in metrics_text
        assert "mlsdm_llm_request_latency_seconds_bucket_bucket" not in metrics_text
        assert 'model="gpt-4"' in metrics_text
        assert 'model="claude-3"' in metrics_text

    def test_llm_failures_by_reason(self, fresh_metrics):
        """Test LLM failures counter with reason labels."""
        fresh_metrics.increment_llm_failures("timeout", 3)
        fresh_metrics.increment_llm_failures("quota", 1)
        fresh_metrics.increment_llm_failures("safety", 2)
        fresh_metrics.increment_llm_failures("transport", 1)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_llm_failures_total" in metrics_text
        assert 'reason="timeout"' in metrics_text
        assert 'reason="quota"' in metrics_text
        assert 'reason="safety"' in metrics_text
        assert 'reason="transport"' in metrics_text

    def test_llm_tokens_by_direction(self, fresh_metrics):
        """Test LLM tokens counter with direction labels."""
        fresh_metrics.increment_llm_tokens("in", 100)
        fresh_metrics.increment_llm_tokens("out", 50)
        fresh_metrics.increment_llm_tokens("in", 200)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_llm_tokens_total" in metrics_text
        assert 'direction="in"' in metrics_text
        assert 'direction="out"' in metrics_text


class TestCognitiveControllerMetrics:
    """Tests for cognitive controller metrics (OBS-001 enhancement)."""

    def test_cognitive_cycle_duration(self, fresh_metrics):
        """Test cognitive cycle duration histogram."""
        fresh_metrics.observe_cognitive_cycle_duration(0.005)
        fresh_metrics.observe_cognitive_cycle_duration(0.010)
        fresh_metrics.observe_cognitive_cycle_duration(0.025)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_cognitive_cycle_duration_seconds" in metrics_text
        assert "mlsdm_cognitive_cycle_duration_seconds_count 3" in metrics_text

    def test_memory_items_by_level(self, fresh_metrics):
        """Test memory items gauge with level labels."""
        fresh_metrics.set_memory_items("L1", 100)
        fresh_metrics.set_memory_items("L2", 500)
        fresh_metrics.set_memory_items("L3", 1000)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_memory_items_total" in metrics_text
        assert 'level="L1"' in metrics_text
        assert 'level="L2"' in metrics_text
        assert 'level="L3"' in metrics_text

    def test_memory_evictions_by_reason(self, fresh_metrics):
        """Test memory evictions counter with reason labels."""
        fresh_metrics.increment_memory_evictions("decay", 10)
        fresh_metrics.increment_memory_evictions("capacity", 5)
        fresh_metrics.increment_memory_evictions("policy", 2)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_memory_evictions_total" in metrics_text
        assert 'reason="decay"' in metrics_text
        assert 'reason="capacity"' in metrics_text
        assert 'reason="policy"' in metrics_text

    def test_auto_recovery_by_result(self, fresh_metrics):
        """Test auto-recovery counter with result labels."""
        fresh_metrics.increment_auto_recovery("success", 3)
        fresh_metrics.increment_auto_recovery("failure", 1)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_auto_recovery_total" in metrics_text
        assert 'result="success"' in metrics_text
        assert 'result="failure"' in metrics_text


class TestMoralFilterMetrics:
    """Tests for moral filter metrics (OBS-001 enhancement)."""

    def test_moral_filter_decisions_by_type(self, fresh_metrics):
        """Test moral filter decisions counter with decision type labels."""
        fresh_metrics.increment_moral_filter_decision("allow", 100)
        fresh_metrics.increment_moral_filter_decision("block", 10)
        fresh_metrics.increment_moral_filter_decision("moderate", 5)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_moral_filter_decisions_total" in metrics_text
        assert 'decision="allow"' in metrics_text
        assert 'decision="block"' in metrics_text
        assert 'decision="moderate"' in metrics_text

    def test_moral_filter_violation_score(self, fresh_metrics):
        """Test moral filter violation score histogram."""
        # Observe various violation scores
        scores = [0.1, 0.2, 0.5, 0.7, 0.9, 0.3, 0.4]
        for score in scores:
            fresh_metrics.observe_moral_filter_violation_score(score)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_moral_filter_violation_score" in metrics_text
        assert "mlsdm_moral_filter_violation_score_count 7" in metrics_text


class TestTimeoutAndPriorityMetrics:
    """Tests for timeout and priority metrics (OBS-001 enhancement)."""

    def test_timeout_by_endpoint(self, fresh_metrics):
        """Test timeout counter with endpoint labels."""
        fresh_metrics.increment_timeout("/generate", 5)
        fresh_metrics.increment_timeout("/infer", 2)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_timeout_total" in metrics_text
        assert 'endpoint="/generate"' in metrics_text
        assert 'endpoint="/infer"' in metrics_text

    def test_priority_queue_depth_by_level(self, fresh_metrics):
        """Test priority queue depth gauge with priority labels."""
        fresh_metrics.set_priority_queue_depth("high", 5)
        fresh_metrics.set_priority_queue_depth("normal", 20)
        fresh_metrics.set_priority_queue_depth("low", 10)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_priority_queue_depth" in metrics_text
        assert 'priority="high"' in metrics_text
        assert 'priority="normal"' in metrics_text
        assert 'priority="low"' in metrics_text


class TestMetricsExportFormat:
    """Tests to verify metrics export format for Prometheus compatibility."""

    def test_all_new_metrics_in_prometheus_format(self, fresh_metrics):
        """Test that all new metrics are exported in valid Prometheus format."""
        # Exercise all new metrics
        fresh_metrics.increment_http_requests("POST", "/test", "200")
        fresh_metrics.observe_http_request_latency(0.1, "/test")
        fresh_metrics.increment_http_requests_in_flight()
        fresh_metrics.observe_llm_request_latency(1.0, "test-model")
        fresh_metrics.increment_llm_failures("timeout")
        fresh_metrics.increment_llm_tokens("in", 100)
        fresh_metrics.observe_cognitive_cycle_duration(0.01)
        fresh_metrics.set_memory_items("L1", 50)
        fresh_metrics.increment_memory_evictions("decay")
        fresh_metrics.increment_auto_recovery("success")
        fresh_metrics.increment_moral_filter_decision("allow")
        fresh_metrics.observe_moral_filter_violation_score(0.5)
        fresh_metrics.increment_timeout("/test")
        fresh_metrics.set_priority_queue_depth("high", 5)

        metrics_text = fresh_metrics.get_metrics_text()

        # Verify Prometheus format
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text

        # Verify all new metric families are present
        expected_metrics = [
            "mlsdm_http_requests_total",
            "mlsdm_http_request_latency_seconds_bucket",
            "mlsdm_http_requests_in_flight",
            "mlsdm_llm_request_latency_seconds_bucket",
            "mlsdm_llm_failures_total",
            "mlsdm_llm_tokens_total",
            "mlsdm_cognitive_cycle_duration_seconds",
            "mlsdm_memory_items_total",
            "mlsdm_memory_evictions_total",
            "mlsdm_auto_recovery_total",
            "mlsdm_moral_filter_decisions_total",
            "mlsdm_moral_filter_violation_score",
            "mlsdm_timeout_total",
            "mlsdm_priority_queue_depth",
        ]

        for metric_name in expected_metrics:
            assert metric_name in metrics_text, f"Missing metric: {metric_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
