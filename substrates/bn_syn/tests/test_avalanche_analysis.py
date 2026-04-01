from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import numpy as np

from bnsyn.experiments.declarative import _build_avalanche_report, _segment_avalanches


def test_segment_avalanches_handcrafted_sequence() -> None:
    spike_counts = np.asarray([0, 2, 1, 0, 3, 0, 0, 4, 1, 2, 0], dtype=np.int64)
    sizes, durations = _segment_avalanches(spike_counts)
    assert sizes == [3, 3, 7]
    assert durations == [2, 1, 3]


def test_build_avalanche_report_has_consistent_counts() -> None:
    spike_counts = np.asarray([0, 2, 1, 0, 3, 0, 0, 4, 1, 2, 0], dtype=np.int64)
    report = _build_avalanche_report(
        seed=123,
        n_neurons=10,
        dt_ms=0.1,
        duration_ms=1.1,
        steps=11,
        spike_steps_per_step=spike_counts,
        bin_width_steps=1,
    )
    assert report["avalanche_count"] == 3
    assert report["sizes"] == [3, 3, 7]
    assert report["durations"] == [2, 1, 3]
    assert report["size_max"] == 7
    assert report["duration_max"] == 3


def test_avalanche_report_schema_and_semantics() -> None:
    spike_counts = np.asarray([0, 2, 1, 0, 3, 0, 0, 4, 1, 2, 0], dtype=np.int64)
    report = _build_avalanche_report(
        seed=123,
        n_neurons=10,
        dt_ms=0.1,
        duration_ms=1.1,
        steps=11,
        spike_steps_per_step=spike_counts,
        bin_width_steps=1,
    )
    schema = json.loads(Path("schemas/avalanche-report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)

    assert len(report["sizes"]) == report["avalanche_count"]
    assert len(report["durations"]) == report["avalanche_count"]
    assert report["bin_width_steps"] >= 1
    assert 0.0 <= float(report["active_bin_fraction"]) <= 1.0
    assert 0.0 <= float(report["largest_avalanche_fraction"]) <= 1.0


def test_build_avalanche_report_rebin_and_edge_cases() -> None:
    spike_counts = np.asarray([0, 1, 2, 0, 0, 3], dtype=np.int64)
    report = _build_avalanche_report(
        seed=42,
        n_neurons=8,
        dt_ms=0.5,
        duration_ms=3.0,
        steps=6,
        spike_steps_per_step=spike_counts,
        bin_width_steps=2,
    )
    assert report["sizes"] == [6]
    assert report["durations"] == [3]
    assert report["avalanche_count"] == 1


def test_build_avalanche_report_invalid_bin_width_raises() -> None:
    spike_counts = np.asarray([1, 0, 1], dtype=np.int64)
    try:
        _build_avalanche_report(
            seed=1,
            n_neurons=3,
            dt_ms=1.0,
            duration_ms=3.0,
            steps=3,
            spike_steps_per_step=spike_counts,
            bin_width_steps=0,
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for bin_width_steps <= 0")
