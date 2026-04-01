import numpy as np

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.neuro_ai import (
    NeuroContractMetadata,
    NeuroHybridFlags,
    NeuroModuleAdapter,
    NeuroSignalPack,
    SynapticMemoryAdapter,
)
from mlsdm.neuro_ai.prediction_error import BoundedUpdateResult, compute_delta, update_bounded


def test_default_off_matches_legacy(monkeypatch) -> None:
    """Global flags off -> adapter output matches legacy memory."""
    for name in (
        "MLSDM_NEURO_HYBRID_ENABLE",
        "MLSDM_NEURO_LEARNING_ENABLE",
        "MLSDM_NEURO_REGIME_ENABLE",
    ):
        monkeypatch.delenv(name, raising=False)

    flags = NeuroHybridFlags.from_env_and_config()
    dim = 12
    rng = np.random.default_rng(7)
    event = rng.standard_normal(dim).astype(np.float32)

    baseline = MultiLevelSynapticMemory(dimension=dim)
    baseline.update(event.copy())

    adapted_memory = MultiLevelSynapticMemory(dimension=dim)
    adapter = SynapticMemoryAdapter(adapted_memory)
    contract = NeuroContractMetadata(
        name="MultiLevelSynapticMemory",
        inputs=("event",),
        outputs=("l1", "l2", "l3"),
        invariants=("bounded update",),
        bounds=(0.0, float("inf")),
        time_constant=1.0,
        failure_mode="no-op on invalid",
    )
    wrapper = NeuroModuleAdapter(adapter, metadata=contract, enable=flags.hybrid_enabled)

    result = wrapper.step(NeuroSignalPack(observation=event))
    for left, right in zip(baseline.state(), adapted_memory.state(), strict=True):
        np.testing.assert_allclose(left, right)
    assert result.regime is None
    assert result.prediction_error is None


def test_bounded_update_clamps_and_reports_delta() -> None:
    res: BoundedUpdateResult = update_bounded(
        param=0.5,
        delta=compute_delta(predicted=0.0, observed=2.0, clip_value=0.6),
        alpha=0.5,
        bounds=(0.0, 1.0),
        delta_max=0.5,
    )
    assert 0.0 <= res.updated <= 1.0
    assert abs(res.applied_delta) <= 0.5
