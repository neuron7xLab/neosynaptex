import numpy as np

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.neuro_ai import FUNCTIONAL_COVERAGE_MATRIX, NEURO_CONTRACTS
from mlsdm.neuro_ai.adapters import (
    PredictionErrorAdapter,
    RegimeController,
    RegimeState,
    SynapticMemoryAdapter,
)


def test_adapter_default_matches_baseline() -> None:
    rng = np.random.default_rng(42)
    event = rng.standard_normal(12).astype(np.float32)

    baseline = MultiLevelSynapticMemory(dimension=12)
    adapter_memory = MultiLevelSynapticMemory(dimension=12)

    baseline.update(event.copy())
    adapter = SynapticMemoryAdapter(adapter_memory)
    metrics = adapter.update(event.copy())

    baseline_state = baseline.state()
    adapted_state = adapter.get_state()
    for baseline_trace, adapted_trace in zip(baseline_state, adapted_state, strict=True):
        np.testing.assert_allclose(baseline_trace, adapted_trace)
    assert metrics.prediction_error is None
    assert metrics.regime is None


def test_prediction_error_bias_reduces_residual_error() -> None:
    adapter = PredictionErrorAdapter(
        learning_rate=0.3,
        clip_value=1.0,
        max_bias=0.9,
        ema_alpha=0.3,
    )

    residuals: list[float] = []
    for _ in range(6):
        metrics = adapter.update(predicted=0.2, observed=1.0)
        residuals.append(abs(metrics.residual_error))
        assert abs(metrics.delta) <= 1.0
        assert abs(metrics.bias) <= 0.9

    assert residuals[-1] < residuals[0]


def test_regime_controller_hysteresis_limits_flip_flop() -> None:
    controller = RegimeController(
        caution_threshold=0.5,
        defensive_threshold=0.85,
        hysteresis=0.1,
        cooldown=1,
    )

    risks = [0.52, 0.48, 0.53, 0.47, 0.97, 0.82, 0.4, 0.78, 0.76]
    flips = 0
    previous = None
    defensive_seen = False
    for risk in risks:
        decision = controller.step(risk)
        defensive_seen = defensive_seen or decision.state == RegimeState.DEFENSIVE
        if previous is not None and decision.state != previous:
            flips += 1
        previous = decision.state

    assert defensive_seen
    # For this jittery risk sequence with cooldown=1, chatter should stay below 4 flips.
    assert flips <= 4


def test_regime_increases_inhibition_and_reduces_exploration() -> None:
    low = RegimeController().step(0.1)
    high = RegimeController().step(0.95)

    assert high.inhibition_gain > low.inhibition_gain
    assert high.exploration_rate < low.exploration_rate
    assert high.tau_scale <= low.tau_scale


def test_synaptic_memory_risk_modulates_update_gain() -> None:
    dim = 8
    event = np.ones(dim, dtype=np.float32)

    baseline = MultiLevelSynapticMemory(dimension=dim)
    baseline.update(event.copy())

    adapter = SynapticMemoryAdapter(
        MultiLevelSynapticMemory(dimension=dim),
        enable_regime_switching=True,
    )
    adapter.update(event.copy(), risk=0.95)

    baseline_norm = np.linalg.norm(baseline.state()[0])
    adapted_norm = np.linalg.norm(adapter.get_state()[0])
    assert adapted_norm < baseline_norm  # increased inhibition reduces update magnitude


def test_neuro_ai_metrics_remain_bounded_under_sequence() -> None:
    adapter = SynapticMemoryAdapter(
        MultiLevelSynapticMemory(dimension=6),
        enable_adaptation=True,
        enable_regime_switching=True,
    )
    rng = np.random.default_rng(0)

    oscillations: list[float] = []
    for step in range(8):
        event = rng.standard_normal(6).astype(np.float32)
        metrics = adapter.update(
            event,
            predicted=0.0,
            observed=0.1 * step,
            risk=0.2 if step < 4 else 0.9,
        )
        oscillations.append(metrics.oscillation_score)
        assert metrics.oscillation_score >= 0.0

    # Deterministic sequence keeps std-dev of norms well below 5, indicating stable traces.
    assert max(oscillations) < 5.0


def test_functional_coverage_matrix_is_complete() -> None:
    contract_names = set(NEURO_CONTRACTS)
    categories = {"biological", "engineering_abstraction"}
    tags_seen: set[str] = set()

    for record in FUNCTIONAL_COVERAGE_MATRIX:
        assert record.category in categories
        assert record.function_tags
        tags_seen.update(record.function_tags)
        if record.contract is not None:
            assert record.contract in contract_names
            contract_names.remove(record.contract)
        assert record.tests  # every record must cite behavioral tests

    assert not contract_names  # all contracts are covered
    assert {"action_selection", "prediction_error", "regime_switching", "inhibition"}.issubset(tags_seen)
