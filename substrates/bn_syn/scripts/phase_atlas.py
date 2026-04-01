"""Generate deterministic BN-Syn phase-atlas artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bnsyn.criticality.phase_transition import CriticalPhase, PhaseTransitionDetector

SCHEMA_VERSION = "1.0.0"
ATLAS_VERSION = "2026.02"
DEFAULT_SEED = 20260218
FLOAT_DIGITS = 6


@dataclass(frozen=True)
class GridPoint:
    temperature: float
    sigma_target: float
    gain_clamp: float
    sleep_replay: float


SMALL_GRID: tuple[GridPoint, ...] = (
    GridPoint(0.9, 0.90, 0.08, 0.0),
    GridPoint(1.0, 1.00, 0.12, 0.2),
    GridPoint(1.1, 1.10, 0.25, 0.6),
)


def _round(value: float) -> float:
    return float(f"{value:.{FLOAT_DIGITS}f}")


def _classify_sigma(sigma_value: float) -> str:
    detector = PhaseTransitionDetector(subcritical_threshold=0.95, supercritical_threshold=1.05)
    detector.observe(sigma=sigma_value, step=0)
    phase = detector.current_phase()
    if phase is CriticalPhase.SUBCRITICAL:
        return "SUB"
    if phase is CriticalPhase.SUPERCRITICAL:
        return "SUPER"
    return "CRIT"


def _deterministic_sigma(point: GridPoint) -> float:
    sigma = point.sigma_target + 0.05 * (point.temperature - 1.0) + 0.02 * point.sleep_replay
    return _round(sigma)


def _build_record(index: int, point: GridPoint) -> dict[str, Any]:
    sigma = _deterministic_sigma(point)
    return {
        "grid_id": f"small-{index:03d}",
        "temperature": _round(point.temperature),
        "criticality": {
            "sigma_target": _round(point.sigma_target),
            "gain_clamp": _round(point.gain_clamp),
            "estimator_window": 200,
        },
        "sleep": {
            "stages": ["NREM", "REM"],
            "replay_strength": _round(point.sleep_replay),
            "noise_scale": _round(0.05 + point.sleep_replay * 0.1),
        },
        "metrics": {
            "sigma_estimate": sigma,
            "stability_score": _round(max(0.0, 1.0 - abs(sigma - 1.0))),
            "attractor_score": _round(point.sleep_replay * 0.5 + point.temperature * 0.1),
        },
        "regime": _classify_sigma(sigma),
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _source_hash() -> str:
    root = _repo_root()
    tracked = [
        Path(__file__).resolve(),
        root / "src" / "bnsyn" / "criticality" / "phase_transition.py",
        root / "schemas" / "phase_atlas.schema.json",
    ]
    digest = hashlib.sha1()
    for path in sorted(tracked, key=lambda item: item.as_posix()):
        rel = path.resolve().relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_phase_atlas(seed: int) -> dict[str, Any]:
    records = [_build_record(i + 1, point) for i, point in enumerate(SMALL_GRID)]
    payload: dict[str, Any] = {
        "atlas_version": ATLAS_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "meta": {
            "code_sha": _source_hash(),
            "grid": "small",
            "classifier": {
                "subcritical_max": 0.95,
                "critical_min": 0.95,
                "critical_max": 1.05,
                "supercritical_min": 1.05,
            },
        },
        "records": records,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    meta = payload.get("meta")
    if isinstance(meta, dict):
        meta["payload_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_log(log_path: Path, command: str, output_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"cmd:{command}",
        f"python:{platform.python_version()}",
        f"platform:{platform.platform()}",
        f"output:{output_path.as_posix()}",
    ]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic phase atlas artifact.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/scientific_product/PHASE_ATLAS.json"),
        help="Output atlas JSON path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Authoritative deterministic seed.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("artifacts/scientific_product/logs/phase_atlas.log"),
        help="Execution log path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    atlas = build_phase_atlas(seed=args.seed)
    _write_json(args.output, atlas)
    _write_log(args.log, "python -m scripts.phase_atlas --output ... --seed ...", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
