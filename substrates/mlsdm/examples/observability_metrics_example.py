"""Example demonstrating observability metrics and health check usage.

This example shows how to:
1. Use the MetricsExporter for Prometheus metrics
2. Track events, errors, and latencies
3. Export metrics in Prometheus format
4. Access health check endpoints
"""

import time

from mlsdm.observability.metrics import PhaseType, get_metrics_exporter


def main():
    """Demonstrate observability metrics and health checks."""
    print("=" * 70)
    print("MLSDM Observability Metrics Example")
    print("=" * 70)
    print()

    # Get metrics exporter (singleton pattern)
    metrics = get_metrics_exporter()
    print("✓ Metrics exporter initialized")
    print()

    # Simulate processing events
    print("Simulating event processing...")
    print("-" * 70)

    # Process 10 events
    for i in range(10):
        correlation_id = f"event-{i}"

        # Start processing timer
        metrics.start_processing_timer(correlation_id)

        # Simulate some processing work
        time.sleep(0.01)

        # Stop timer and record latency
        latency = metrics.stop_processing_timer(correlation_id)
        print(f"  Event {i}: processed in {latency:.2f}ms")

        # Increment counter
        metrics.increment_events_processed()

    print()

    # Simulate rejecting some events
    print("Simulating event rejection...")
    print("-" * 70)
    for _ in range(3):
        metrics.increment_events_rejected()
    print("  Rejected 3 events due to moral filter")
    print()

    # Simulate some errors
    print("Simulating errors...")
    print("-" * 70)
    metrics.increment_errors("validation_error", 2)
    metrics.increment_errors("processing_error", 1)
    print("  2 validation errors")
    print("  1 processing error")
    print()

    # Update gauges
    print("Updating system state...")
    print("-" * 70)
    metrics.set_memory_usage(2048.5)
    metrics.set_moral_threshold(0.65)
    metrics.set_phase(PhaseType.WAKE)
    metrics.set_memory_norms(1.5, 2.3, 3.1)
    print("  Memory usage: 2048.5 bytes")
    print("  Moral threshold: 0.65")
    print("  Phase: WAKE")
    print("  Memory norms: L1=1.5, L2=2.3, L3=3.1")
    print()

    # Simulate memory retrieval
    print("Simulating memory retrieval...")
    print("-" * 70)
    for i in range(5):
        correlation_id = f"retrieval-{i}"
        metrics.start_retrieval_timer(correlation_id)
        time.sleep(0.005)
        latency = metrics.stop_retrieval_timer(correlation_id)
        print(f"  Retrieval {i}: {latency:.2f}ms")
    print()

    # Get current metric values
    print("Current Metric Values:")
    print("=" * 70)
    values = metrics.get_current_values()
    for key, value in values.items():
        print(f"  {key}: {value}")
    print()

    # Export metrics in Prometheus format
    print("Prometheus Metrics Export:")
    print("=" * 70)
    prometheus_text = metrics.get_metrics_text()

    # Show a preview of the Prometheus export
    lines = prometheus_text.split("\n")
    shown_lines = 0
    for line in lines:
        if line.startswith("#") or "mlsdm_" in line:
            print(line)
            shown_lines += 1
            if shown_lines >= 30:  # Show first 30 relevant lines
                print("  ... (more metrics available)")
                break
    print()

    # Health check endpoints information
    print("Health Check Endpoints:")
    print("=" * 70)
    print("When running the API server, the following endpoints are available:")
    print()
    print("  GET /health/liveness")
    print("    - Returns 200 if process is alive")
    print("    - Use for Kubernetes liveness probes")
    print()
    print("  GET /health/readiness")
    print("    - Returns 200 if ready to accept traffic, 503 otherwise")
    print("    - Use for Kubernetes readiness probes")
    print("    - Checks: memory_manager, memory_available, cpu_available")
    print()
    print("  GET /health/detailed")
    print("    - Returns comprehensive system status")
    print("    - Includes memory state, phase, statistics, system resources")
    print("    - Returns 200 if healthy, 503 if unhealthy")
    print()
    print("  GET /health/metrics")
    print("    - Returns Prometheus-formatted metrics")
    print("    - Use for Prometheus scraping")
    print()

    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
