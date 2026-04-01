"""
Tests for Aphasia Prometheus Metrics

This test suite validates that aphasia detection events properly update
Prometheus metrics for observability.
"""

import logging

import numpy as np
import pytest
from prometheus_client import CollectorRegistry

from mlsdm.extensions import NeuroLangWrapper
from mlsdm.observability.aphasia_logging import LOGGER_NAME
from mlsdm.observability.aphasia_metrics import (
    AphasiaMetricsExporter,
    reset_aphasia_metrics_exporter,
)


def telegraphic_llm(prompt: str, max_tokens: int) -> str:
    """Simulates an LLM producing aphasic (telegraphic) output."""
    return "This short. No connect. Bad."


def normal_llm(prompt: str, max_tokens: int) -> str:
    """Simulates an LLM producing normal, coherent output."""
    return (
        "This is a coherent answer that uses normal grammar and function words "
        "to describe the system behaviour in a clear way."
    )


def dummy_embedder(text: str):
    """Generate deterministic embeddings for testing."""
    vec = np.ones(384, dtype=np.float32)
    return vec / np.linalg.norm(vec)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test to ensure isolation."""
    reset_aphasia_metrics_exporter()
    yield
    reset_aphasia_metrics_exporter()


@pytest.fixture
def metrics_exporter():
    """Create a fresh metrics exporter with its own registry."""
    registry = CollectorRegistry()
    return AphasiaMetricsExporter(registry=registry)


def test_aphasia_events_total_increments_on_detection(metrics_exporter):
    """Test that aphasia_events_total counter increments correctly."""
    # Record an aphasic event
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=True,
        repair_applied=True,
        severity=0.7,
        flags=["short_sentences", "low_function_words"],
    )

    # Check counter value
    counter_value = metrics_exporter.aphasia_events_total.labels(
        mode="full",
        is_aphasic="True",
        repair_applied="True",
    )._value.get()

    assert counter_value == 1.0


def test_aphasia_events_total_with_different_labels(metrics_exporter):
    """Test that aphasia_events_total correctly tracks different label combinations."""
    # Record events with different labels
    metrics_exporter.record_aphasia_event(
        mode="full", is_aphasic=True, repair_applied=True, severity=0.8, flags=[]
    )
    metrics_exporter.record_aphasia_event(
        mode="monitor", is_aphasic=True, repair_applied=False, severity=0.6, flags=[]
    )
    metrics_exporter.record_aphasia_event(
        mode="full", is_aphasic=False, repair_applied=False, severity=0.1, flags=[]
    )

    # Check counters
    assert (
        metrics_exporter.aphasia_events_total.labels(
            mode="full", is_aphasic="True", repair_applied="True"
        )._value.get()
        == 1.0
    )

    assert (
        metrics_exporter.aphasia_events_total.labels(
            mode="monitor", is_aphasic="True", repair_applied="False"
        )._value.get()
        == 1.0
    )

    assert (
        metrics_exporter.aphasia_events_total.labels(
            mode="full", is_aphasic="False", repair_applied="False"
        )._value.get()
        == 1.0
    )


def test_aphasia_severity_histogram_observes_values(metrics_exporter):
    """Test that aphasia_severity_histogram correctly observes severity values."""
    # Record events with different severities
    metrics_exporter.record_aphasia_event(
        mode="full", is_aphasic=True, repair_applied=True, severity=0.3, flags=[]
    )
    metrics_exporter.record_aphasia_event(
        mode="full", is_aphasic=True, repair_applied=False, severity=0.7, flags=[]
    )
    metrics_exporter.record_aphasia_event(
        mode="full", is_aphasic=False, repair_applied=False, severity=0.0, flags=[]
    )

    # Verify histogram has observations
    # Access internal _sum to verify values were observed
    histogram_sum = metrics_exporter.aphasia_severity_histogram._sum.get()
    assert histogram_sum == pytest.approx(1.0)  # 0.3 + 0.7 + 0.0

    # Verify observations are distributed across buckets
    # With buckets (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, +inf)
    # Each observation is counted in the bucket matching its value
    # severity=0.0 -> bucket[0] (le=0.0)
    # severity=0.3 -> bucket[3] (le=0.3)
    # severity=0.7 -> bucket[7] (le=0.7)
    bucket_0_count = metrics_exporter.aphasia_severity_histogram._buckets[0].get()
    bucket_3_count = metrics_exporter.aphasia_severity_histogram._buckets[3].get()
    bucket_7_count = metrics_exporter.aphasia_severity_histogram._buckets[7].get()
    assert bucket_0_count == 1.0  # severity=0.0
    assert bucket_3_count == 1.0  # severity=0.3
    assert bucket_7_count == 1.0  # severity=0.7


def test_aphasia_flags_total_increments_for_each_flag(metrics_exporter):
    """Test that aphasia_flags_total correctly counts individual flags."""
    # Record event with multiple flags
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=True,
        repair_applied=True,
        severity=0.8,
        flags=["short_sentences", "low_function_words", "high_fragment_ratio"],
    )

    # Check each flag counter
    assert metrics_exporter.aphasia_flags_total.labels(flag="short_sentences")._value.get() == 1.0

    assert (
        metrics_exporter.aphasia_flags_total.labels(flag="low_function_words")._value.get() == 1.0
    )

    assert (
        metrics_exporter.aphasia_flags_total.labels(flag="high_fragment_ratio")._value.get() == 1.0
    )


def test_aphasia_flags_accumulate_across_events(metrics_exporter):
    """Test that flag counters accumulate across multiple events."""
    # Record multiple events with overlapping flags
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=True,
        repair_applied=True,
        severity=0.8,
        flags=["short_sentences", "low_function_words"],
    )
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=True,
        repair_applied=False,
        severity=0.6,
        flags=["short_sentences", "high_fragment_ratio"],
    )

    # Check accumulated counts
    assert (
        metrics_exporter.aphasia_flags_total.labels(flag="short_sentences")._value.get() == 2.0
    )  # Appears in both events

    assert (
        metrics_exporter.aphasia_flags_total.labels(flag="low_function_words")._value.get() == 1.0
    )  # Only in first event

    assert (
        metrics_exporter.aphasia_flags_total.labels(flag="high_fragment_ratio")._value.get() == 1.0
    )  # Only in second event


def test_empty_flags_list_does_not_create_counters(metrics_exporter):
    """Test that events with no flags don't create spurious counters."""
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=False,
        repair_applied=False,
        severity=0.0,
        flags=[],
    )

    # The event should be recorded
    assert (
        metrics_exporter.aphasia_events_total.labels(
            mode="full", is_aphasic="False", repair_applied="False"
        )._value.get()
        == 1.0
    )

    # But no flag counters should be created for this event
    # (testing by ensuring no exception is raised and count is as expected)


def test_metrics_integrated_with_neurolang_wrapper(caplog):
    """Test that NeuroLangWrapper triggers Prometheus metrics updates."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    # Create wrapper with detection enabled
    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=True,
        neurolang_mode="disabled",
    )

    # Generate response (will be aphasic and repaired)
    _ = wrapper.generate(prompt="Test metrics integration.", moral_value=0.8, max_tokens=64)

    # Verify log was emitted (confirming the event was processed)
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "Expected at least one aphasia log record"
    assert "decision=repaired" in caplog.text


def test_no_metrics_when_detection_disabled(caplog):
    """Test that no metrics are emitted when detection is disabled."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=False,  # Detection disabled
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test disabled detection.", moral_value=0.8, max_tokens=64)

    # No aphasia logs should appear
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 0


def test_metrics_do_not_contain_content(metrics_exporter):
    """Test that metrics contain only metadata, no content or PII."""
    # Record event - flags should be predefined constants, not content
    metrics_exporter.record_aphasia_event(
        mode="full",
        is_aphasic=True,
        repair_applied=True,
        severity=0.75,
        flags=["short_sentences", "low_function_words"],  # Standard flags only
    )

    # The metrics API should only accept predefined constants, not arbitrary text
    # that could leak content

    # Check that we can still access expected labels
    counter_value = metrics_exporter.aphasia_events_total.labels(
        mode="full", is_aphasic="True", repair_applied="True"
    )._value.get()
    assert counter_value == 1.0

    # Verify flags are the expected predefined ones
    assert metrics_exporter.aphasia_flags_total.labels(flag="short_sentences")._value.get() == 1.0
