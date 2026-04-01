"""Integration tests for BioExtension — all 5 biological mechanisms."""

from __future__ import annotations

import json

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.bio import BioConfig, BioExtension, BioReport
from mycelium_fractal_net.types.field import SimulationSpec


@pytest.fixture(scope="module")
def base_seq() -> mfn.FieldSequence:
    return mfn.simulate(SimulationSpec(grid_size=16, steps=20, seed=42))


def test_from_sequence(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq)
    assert isinstance(bio, BioExtension)
    assert bio.step_count == 0
    assert bio.N == 16


def test_step_increments(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq)
    bio2 = bio.step(n=3)
    assert bio2.step_count == 3
    assert bio.step_count == 0


def test_report_fields(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq).step(n=2)
    report = bio.report()
    assert isinstance(report, BioReport)
    assert "conductivity_max" in report.physarum
    assert "tip_density_mean" in report.anastomosis
    assert "spiking_fraction" in report.fhn
    assert "airborne_spores_total" in report.dispersal
    assert "gradient_alignment" in report.chemotaxis


def test_report_summary(base_seq: mfn.FieldSequence) -> None:
    s = BioExtension.from_sequence(base_seq).step(n=1).report().summary()
    assert "BIO" in s
    assert "physarum" in s


def test_effective_diffusion(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq).step(n=2)
    D = bio.effective_diffusion(base_D=0.18)
    assert D.shape == (16, 16)
    assert float(np.min(D)) >= 0.18


def test_conductivity_map(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq).step(n=2)
    cmap = bio.conductivity_map()
    assert cmap.shape == (16, 16)
    assert np.all(np.isfinite(cmap))


def test_physarum_adapts(base_seq: mfn.FieldSequence) -> None:
    bio0 = BioExtension.from_sequence(base_seq)
    bio10 = bio0.step(n=10)
    assert (
        bio0.physarum_state.to_dict()["conductivity_max"]
        != bio10.physarum_state.to_dict()["conductivity_max"]
    )


def test_anastomosis_grows(base_seq: mfn.FieldSequence) -> None:
    bio = BioExtension.from_sequence(base_seq).step(n=5)
    assert bio.anastomosis_state.to_dict()["hyphal_density_mean"] > 0.0


def test_to_dict_json_safe(base_seq: mfn.FieldSequence) -> None:
    d = BioExtension.from_sequence(base_seq).step(n=1).report().to_dict()
    s = json.dumps(d)
    assert len(s) > 50
    assert "physarum" in s


def test_skip_mechanisms(base_seq: mfn.FieldSequence) -> None:
    cfg = BioConfig(enable_fhn=False, enable_dispersal=False, enable_chemotaxis=False)
    bio = BioExtension.from_sequence(base_seq, config=cfg).step(n=3)
    assert isinstance(bio.report(), BioReport)


def test_smoke_32x32() -> None:
    seq = mfn.simulate(SimulationSpec(grid_size=32, steps=30, seed=7))
    bio = BioExtension.from_sequence(seq).step(n=5)
    assert bio.step_count == 5
    r = bio.report()
    assert r.field_shape == (32, 32)
