from __future__ import annotations

import json

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.features import MorphologyDescriptor
from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec


def test_simulation_spec_roundtrip() -> None:
    spec = SimulationSpec(grid_size=16, steps=8, seed=11)
    restored = SimulationSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
    assert restored == spec


def test_field_sequence_and_descriptor_roundtrip() -> None:
    seq = mfn.simulate(SimulationSpec(grid_size=16, steps=8, seed=42))
    restored_seq = FieldSequence.from_dict(seq.to_dict(include_arrays=True))
    assert restored_seq.grid_size == seq.grid_size
    desc = mfn.extract(seq)
    restored_desc = MorphologyDescriptor.from_dict(json.loads(json.dumps(desc.to_dict())))
    assert restored_desc.version == desc.version
