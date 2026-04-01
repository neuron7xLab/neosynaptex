from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path


def _load():
    module_path = Path(__file__).resolve().parents[2] / "src" / "mlsdm" / "core" / "iteration_loop.py"
    loader = importlib.machinery.SourceFileLoader("iteration_loop", str(module_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


iteration_loop = _load()
IterationContext = iteration_loop.IterationContext
IterationMetricsEmitter = iteration_loop.IterationMetricsEmitter


def test_metrics_emitter_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "iteration" / "iteration-metrics.jsonl"
    emitter = IterationMetricsEmitter(enabled=True, output_path=out)
    ctx = IterationContext(dt=1.0, timestamp=1.0, seed=7, threat=0.2, risk=0.3)
    trace = {
        "regime": "normal",
        "prediction_error": {"delta": [0.1], "abs_delta": 0.1, "clipped_delta": [0.1]},
        "action": {"id": "a"},
        "dynamics": {"learning_rate": 0.1},
        "safety": {"allow_next": True, "reason": "stable"},
    }

    emitter.emit(ctx, trace)

    data = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
    assert data
    record = data[0]
    assert record["seed"] == 7
    assert record["prediction_error"]["abs_delta"] == 0.1
    assert record["regime"] == "normal"
