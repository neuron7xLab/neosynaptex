from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.compare import compare
from mycelium_fractal_net.core.detect import detect_anomaly, detect_regime_shift
from mycelium_fractal_net.core.forecast import forecast_next
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.types.forecast import validate_forecast_payload


@dataclass
class QualityResult:
    task: str
    engine_score: float
    baseline_score: float
    delta: float
    label: str


def _clip01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def _raw_stats_baseline_score(sequence) -> float:
    history = sequence.history if sequence.history is not None else sequence.field[None, :, :]
    final = history[-1]
    return _clip01(float(np.std(final) / (abs(np.mean(final)) + 1e-9)) * 0.25)


def _naive_regime_baseline(sequence) -> float:
    history = sequence.history if sequence.history is not None else sequence.field[None, :, :]
    if history.shape[0] < 2:
        return 0.0
    mean_abs_delta = float(np.mean(np.abs(np.diff(history, axis=0))))
    return _clip01(mean_abs_delta / 0.02)


def _persistence_forecast_score(sequence) -> float:
    history = sequence.history if sequence.history is not None else sequence.field[None, :, :]
    forecast = forecast_next(sequence, horizon=4)
    validate_forecast_payload(forecast.to_dict())
    predicted = np.asarray(forecast.predicted_states[-1], dtype=np.float64)
    baseline = history[-1]
    target = sequence.field
    engine_error = float(np.mean(np.abs(predicted - target)))
    baseline_error = float(np.mean(np.abs(baseline - target)))
    return _clip01(1.0 - baseline_error * 25.0), engine_error, baseline_error


def _texture_descriptor(sequence) -> np.ndarray:
    history = sequence.history if sequence.history is not None else sequence.field[None, :, :]
    frame = history[-1]
    gx = np.diff(frame, axis=1)
    gy = np.diff(frame, axis=0)
    return np.asarray(
        [
            float(np.mean(frame)),
            float(np.std(frame)),
            float(np.mean(np.abs(gx))) if gx.size else 0.0,
            float(np.mean(np.abs(gy))) if gy.size else 0.0,
            float(np.max(frame) - np.min(frame)),
        ],
        dtype=np.float64,
    )


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 1.0


def main() -> int:
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    synthetic = simulate_scenario("synthetic_morphology")
    anomaly_case = simulate_scenario("sensor_grid_anomaly")
    regime_case = simulate_scenario("regime_transition")

    anomaly = detect_anomaly(anomaly_case)
    regime = detect_regime_shift(regime_case)
    comp = compare(synthetic, regime_case)
    fc = forecast_next(synthetic, horizon=4)
    fc_payload = validate_forecast_payload(fc.to_dict())

    anomaly_engine = _clip01(1.0 - abs(anomaly.score - 0.6))
    anomaly_baseline = _clip01(1.0 - abs(_raw_stats_baseline_score(anomaly_case) - 0.6))

    regime_engine = float(regime.confidence)
    regime_baseline = _naive_regime_baseline(regime_case)

    forecast_baseline_score, engine_error, baseline_error = _persistence_forecast_score(synthetic)
    forecast_engine = _clip01(
        1.0 - float(fc_payload["benchmark_metrics"]["forecast_structural_error"]) * 25.0
    )

    synthetic_tex = _texture_descriptor(synthetic)
    regime_tex = _texture_descriptor(regime_case)
    baseline_cosine = max(0.0, _cosine(synthetic_tex, regime_tex))
    comparison_engine = _clip01(max(0.0, comp.cosine_similarity))

    desc_s = compute_morphology_descriptor(synthetic)
    desc_r = compute_morphology_descriptor(regime_case)
    pca_like_baseline = _clip01(
        max(
            0.0,
            _cosine(np.asarray(desc_s.embedding[:8]), np.asarray(desc_r.embedding[:8])),
        )
    )

    rows = [
        QualityResult(
            "anomaly_detection_quality",
            anomaly_engine,
            anomaly_baseline,
            anomaly_engine - anomaly_baseline,
            anomaly.label,
        ),
        QualityResult(
            "regime_detection_quality",
            regime_engine,
            regime_baseline,
            regime_engine - regime_baseline,
            regime.label,
        ),
        QualityResult(
            "forecast_structural_quality",
            forecast_engine,
            forecast_baseline_score,
            forecast_engine - forecast_baseline_score,
            fc.method,
        ),
        QualityResult(
            "morphology_comparison_quality",
            comparison_engine,
            max(baseline_cosine, pca_like_baseline),
            comparison_engine - max(baseline_cosine, pca_like_baseline),
            comp.label,
        ),
    ]
    summary = {
        "mean_engine_score": sum(item.engine_score for item in rows) / len(rows),
        "mean_baseline_score": sum(item.baseline_score for item in rows) / len(rows),
        "mean_delta": sum(item.delta for item in rows) / len(rows),
        "min_engine_score": min(item.engine_score for item in rows),
        "max_engine_score": max(item.engine_score for item in rows),
        "forecast_engine_error": engine_error,
        "forecast_persistence_error": baseline_error,
    }

    json_path = results_dir / "benchmark_quality.json"
    csv_path = results_dir / "benchmark_quality.csv"
    json_path.write_text(
        json.dumps({"results": [asdict(r) for r in rows], "summary": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["task", "engine_score", "baseline_score", "delta", "label"]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    print(json_path)
    print(csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
