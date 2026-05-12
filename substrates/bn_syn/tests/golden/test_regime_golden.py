from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bnsyn.regime import RegimeController

pytestmark = pytest.mark.golden


def test_regime_golden() -> None:
    payload = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "regime_golden.json").read_text())
    tolerance = float(payload.get("tolerance", 1e-12))
    controller = RegimeController(learning_rate=0.01, rest_threshold=0.6)
    weights = np.array(payload["weights"], dtype=float)
    grad = np.array(payload["grad"], dtype=float)
    activations = np.ones(512)
    for idx, entropy in enumerate(payload["entropy"]):
        weights, diag = controller.step(weights, grad, activations, entropy=entropy)
        assert abs(diag.gate_signal - payload["expected_gate"][idx]) < tolerance
