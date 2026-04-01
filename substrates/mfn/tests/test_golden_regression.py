"""Golden output regression tests.

Verify that deterministic outputs (fixed seed=42) match known-good values.
If any of these fail, an algorithm or default has silently changed.

Golden data: tests/fixtures/golden_outputs.json
Regenerate: PYTHONPATH=src python -c "..." (see script in fixtures/)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import mycelium_fractal_net as mfn

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "golden_outputs.json").read_text())


class TestSimulationRegression:
    """Verify simulation outputs haven't drifted."""

    def setup_method(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=16, seed=42)
        self.seq = mfn.simulate(spec)
        self.expected = GOLDEN["baseline_simulation"]

    def test_field_shape(self) -> None:
        assert list(self.seq.field.shape) == self.expected["field_shape"]

    def test_field_statistics_stable(self) -> None:
        assert self.seq.field.min() == pytest.approx(self.expected["field_min"], abs=1e-10)
        assert self.seq.field.max() == pytest.approx(self.expected["field_max"], abs=1e-10)
        assert self.seq.field.mean() == pytest.approx(self.expected["field_mean"], abs=1e-10)
        assert self.seq.field.std() == pytest.approx(self.expected["field_std"], abs=1e-10)

    def test_field_checksum(self) -> None:
        """Bitwise-deterministic output check."""
        assert float(np.sum(self.seq.field)) == pytest.approx(
            self.expected["field_checksum"], abs=1e-10
        )

    def test_num_steps(self) -> None:
        assert self.seq.num_steps == self.expected["num_steps"]


class TestNernstRegression:
    """Verify Nernst equation output is biophysically correct."""

    def test_k_potential(self) -> None:
        e_k = mfn.compute_nernst_potential(1, 5e-3, 140e-3)
        expected = GOLDEN["nernst_k_potential"]
        assert e_k == pytest.approx(expected["e_volts"], abs=1e-12)
        e_mv = e_k * 1000
        assert expected["expected_range_mv"][0] <= e_mv <= expected["expected_range_mv"][1]


class TestFeatureExtractionRegression:
    """Verify feature extraction output structure and values are stable."""

    def setup_method(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=16, seed=42)
        seq = mfn.simulate(spec)
        self.descriptor = mfn.extract(seq)
        self.expected = GOLDEN["feature_extraction"]

    def test_descriptor_version(self) -> None:
        assert self.descriptor.version == self.expected["version"]

    def test_stability_keys(self) -> None:
        assert sorted(self.descriptor.stability.keys()) == self.expected["stability_keys"]

    def test_complexity_keys(self) -> None:
        assert sorted(self.descriptor.complexity.keys()) == self.expected["complexity_keys"]

    def test_connectivity_keys(self) -> None:
        assert sorted(self.descriptor.connectivity.keys()) == self.expected["connectivity_keys"]

    def test_embedding_length(self) -> None:
        assert len(self.descriptor.embedding) == self.expected["embedding_length"]

    def test_instability_index_stable(self) -> None:
        assert self.descriptor.stability["instability_index"] == pytest.approx(
            self.expected["instability_index"], abs=1e-10
        )


class TestAnomalyDetectionRegression:
    """Verify anomaly detection produces identical labels and scores."""

    def setup_method(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=16, seed=42)
        seq = mfn.simulate(spec)
        self.anomaly = mfn.detect(seq)
        self.expected = GOLDEN["anomaly_detection"]

    def test_anomaly_label(self) -> None:
        assert self.anomaly.label == self.expected["label"]

    def test_anomaly_score(self) -> None:
        assert self.anomaly.score == pytest.approx(self.expected["score"], abs=1e-10)

    def test_regime_label(self) -> None:
        assert self.anomaly.regime.label == self.expected["regime_label"]

    def test_regime_score(self) -> None:
        assert self.anomaly.regime.score == pytest.approx(self.expected["regime_score"], abs=1e-10)


class TestForecastRegression:
    """Verify forecast structure is stable."""

    def setup_method(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=16, seed=42)
        seq = mfn.simulate(spec)
        self.forecast = mfn.forecast(seq, horizon=4)
        self.expected = GOLDEN["forecast"]

    def test_horizon(self) -> None:
        fd = self.forecast.to_dict()
        assert fd["horizon"] == self.expected["horizon"]

    def test_method(self) -> None:
        fd = self.forecast.to_dict()
        assert fd["method"] == self.expected["method"]


class TestComparisonRegression:
    """Verify self-comparison gives zero distance."""

    def test_self_comparison_distance_zero(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=16, seed=42)
        seq = mfn.simulate(spec)
        comp = mfn.compare(seq, seq)
        expected = GOLDEN["self_comparison"]
        assert comp.distance == pytest.approx(expected["distance"], abs=1e-10)
        assert comp.topology_label == expected["topology_label"]
