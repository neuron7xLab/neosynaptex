import numpy as np

from mlsdm.neuro_ai import RegimeController, RegimeState
from mlsdm.neuro_ai.prediction_error import PredictorEMA, compute_delta, update_bounded


def test_regime_flip_rate_stable() -> None:
    controller = RegimeController(hysteresis=0.1, cooldown=2)
    risks = np.linspace(0.3, 0.4, num=20)
    flips = 0
    prev = controller.state
    for risk in risks:
        state = controller.step(float(risk)).state
        if state != prev:
            flips += 1
        prev = state
    assert flips <= 2  # M1: bounded chatter under stationary input


def test_regime_responsiveness_and_risk_sensitivity() -> None:
    controller = RegimeController()
    low = controller.step(0.1)
    high = controller.step(0.95)
    assert high.inhibition_gain > low.inhibition_gain  # M3 monotonicity
    # M2: reach DEFENSIVE within small number of steps after risk spike
    controller = RegimeController()
    steps = 0
    state = controller.state
    while state != RegimeState.DEFENSIVE and steps < 5:
        state = controller.step(0.95).state
        steps += 1
    assert state == RegimeState.DEFENSIVE
    assert steps <= 5


def test_learning_converges_with_bounded_delta() -> None:
    ema = PredictorEMA.from_tau(tau=4.0)
    param = 0.0
    deltas: list[float] = []

    for _ in range(8):
        pred = ema.predict()
        delta = compute_delta(predicted=pred, observed=1.0, clip_value=0.5)
        deltas.append(abs(delta))
        ema.step(1.0)
        result = update_bounded(param, delta, alpha=0.3, bounds=(-0.5, 1.0))
        param = result.updated
        assert -0.5 <= param <= 1.0

    assert deltas[-1] < deltas[0]  # M4: |Δ| shrinks over episodes
