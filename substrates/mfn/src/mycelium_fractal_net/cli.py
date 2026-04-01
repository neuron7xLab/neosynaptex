"""Canonical CLI for the Morphology-aware Field Intelligence Engine."""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.artifact_bundle import verify_bundle
from mycelium_fractal_net.core.compare import compare as compare_sequences
from mycelium_fractal_net.core.detect import detect_anomaly
from mycelium_fractal_net.core.forecast import forecast_next
from mycelium_fractal_net.core.simulate import simulate_final, simulate_history
from mycelium_fractal_net.pipelines.reporting import build_analysis_report
from mycelium_fractal_net.types.field import (
    FieldSequence,
    GABAATonicSpec,
    NeuromodulationSpec,
    ObservationNoiseSpec,
    SerotonergicPlasticitySpec,
    SimulationSpec,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _dump_json(payload: dict[str, Any], output: str | None) -> int:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(str(path))
    else:
        print(text)
    return 0


def _wants_json(args: argparse.Namespace) -> bool:
    return getattr(args, "json_output", False) or getattr(args, "output", None) is not None


def _load_npy(path: str) -> FieldSequence:
    arr = np.load(Path(path))
    if arr.ndim == 3:
        return FieldSequence(
            field=arr[-1].astype(np.float64),
            history=arr.astype(np.float64),
            metadata={"source": str(path)},
        )
    if arr.ndim == 2:
        return FieldSequence(
            field=arr.astype(np.float64), history=None, metadata={"source": str(path)}
        )
    raise ValueError(f"expected 2D or 3D array, got ndim={arr.ndim}")


def _neuromod_from_args(args: argparse.Namespace) -> NeuromodulationSpec | None:
    profile = getattr(args, "neuromod_profile", None)
    obs_profile = getattr(args, "observation_noise_profile", None)
    agonist = getattr(args, "agonist_concentration_um", None)
    rest_offset_mv = getattr(args, "rest_offset_mv", None)
    gain_fluidity = getattr(args, "gain_fluidity_coeff", None)
    dt_seconds = float(getattr(args, "dt_seconds", 1.0))
    if not any(
        v is not None for v in [profile, obs_profile, agonist, rest_offset_mv, gain_fluidity]
    ):
        return None
    gabaa = None
    serotonergic = None
    observation_noise = None
    if profile and ("gabaa" in profile or agonist is not None or rest_offset_mv is not None):
        gabaa = GABAATonicSpec(
            profile=profile or "custom-gabaa",
            agonist_concentration_um=float(agonist or 0.0),
            rest_offset_mv=float(rest_offset_mv or 0.0),
            shunt_strength=0.25,
            resting_affinity_um=0.25,
            active_affinity_um=0.20,
            desensitization_rate_hz=0.02,
            recovery_rate_hz=0.02,
        )
    if profile and (
        "serotonergic" in profile or "criticality" in profile or gain_fluidity is not None
    ):
        serotonergic = SerotonergicPlasticitySpec(
            profile=profile or "custom-serotonergic",
            gain_fluidity_coeff=float(gain_fluidity or 0.05),
            reorganization_drive=0.05,
            coherence_bias=0.01,
        )
    if obs_profile:
        observation_noise = ObservationNoiseSpec(
            profile=obs_profile,
            std=0.0012 if obs_profile == "observation_noise_gaussian_temporal" else 0.0005,
            temporal_smoothing=0.35,
        )
    return NeuromodulationSpec(
        profile=profile or obs_profile or "custom-neuromodulation",
        enabled=True,
        dt_seconds=dt_seconds,
        intrinsic_field_jitter=getattr(args, "quantum_jitter", False),
        intrinsic_field_jitter_var=float(getattr(args, "jitter_var", 0.0005)),
        gabaa_tonic=gabaa,
        serotonergic=serotonergic,
        observation_noise=observation_noise,
    )


def _spec_from_args(args: argparse.Namespace) -> SimulationSpec:
    return SimulationSpec(
        grid_size=args.grid_size,
        steps=args.steps,
        alpha=args.alpha,
        spike_probability=args.spike_probability,
        turing_enabled=args.turing_enabled,
        turing_threshold=args.turing_threshold,
        quantum_jitter=args.quantum_jitter,
        jitter_var=args.jitter_var,
        seed=args.seed,
        neuromodulation=_neuromod_from_args(args),
    )


def _sequence_from_args(
    args: argparse.Namespace, *, require_history: bool = False
) -> FieldSequence:
    if getattr(args, "input_npy", None):
        seq = _load_npy(args.input_npy)
    else:
        spec = _spec_from_args(args)
        seq = simulate_history(spec) if require_history else simulate_final(spec)
    if require_history and not seq.has_history:
        raise ValueError(
            "command requires history; provide --input-npy with 3D array or omit it to simulate with history"
        )
    return seq


def _pair_from_args(args: argparse.Namespace) -> tuple[FieldSequence, FieldSequence]:
    left = (
        _load_npy(args.input_a_npy) if args.input_a_npy else simulate_history(_spec_from_args(args))
    )
    if args.input_b_npy:
        right = _load_npy(args.input_b_npy)
    else:
        spec = _spec_from_args(args)
        seed = spec.seed if spec.seed is not None else 42
        right = simulate_history(SimulationSpec(**{**spec.as_runtime_dict(), "seed": seed + 1}))
    return left, right


def cmd_simulate(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_display import format_simulation

    seq = (
        simulate_history(_spec_from_args(args))
        if args.with_history
        else simulate_final(_spec_from_args(args))
    )
    if _wants_json(args):
        payload = seq.to_dict(include_arrays=args.include_arrays)
        payload["command"] = "simulate"
        return _dump_json(payload, args.output)
    print(format_simulation(seq))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_display import format_descriptor

    seq = _sequence_from_args(args)
    descriptor = compute_morphology_descriptor(seq)
    if _wants_json(args):
        return _dump_json(
            {
                "command": "extract",
                "descriptor": descriptor.to_dict(),
                "features": descriptor.features,
            },
            args.output,
        )
    print(format_descriptor(descriptor))
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_display import format_detection

    seq = _sequence_from_args(args)
    detection = detect_anomaly(seq)
    if _wants_json(args):
        payload = detection.to_dict()
        payload.setdefault("anomaly_label", payload["label"])
        payload.setdefault("anomaly_score", payload["score"])
        if payload.get("regime"):
            payload.setdefault("regime_label", payload["regime"]["label"])
        return _dump_json({"command": "detect", "detection": payload}, args.output)
    print(format_detection(detection))
    return 0


def cmd_forecast(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_display import format_forecast

    seq = _sequence_from_args(args, require_history=True)
    result = forecast_next(seq, horizon=args.horizon)
    if _wants_json(args):
        return _dump_json({"command": "forecast", "forecast": result.to_dict()}, args.output)
    print(format_forecast(result))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_display import format_comparison

    left, right = _pair_from_args(args)
    result = compare_sequences(left, right)
    if _wants_json(args):
        payload = result.to_dict()
        payload.setdefault("similarity_label", payload["label"])
        return _dump_json({"command": "compare", "comparison": payload}, args.output)
    print(format_comparison(result))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    seq = _sequence_from_args(args, require_history=True)
    comparison = _load_npy(args.compare_npy) if getattr(args, "compare_npy", None) else None
    if getattr(args, "output_dir", None):
        tmp_root = Path(args.output_dir).parent / (Path(args.output_dir).name + "_tmp_root")
        result = build_analysis_report(
            seq,
            tmp_root,
            horizon=args.horizon,
            comparison_sequence=comparison,
            export_symbolic_context=args.export_symbolic_context,
        )
        src_dir = tmp_root / result.run_id
        dst_dir = Path(args.output_dir)
        if dst_dir.exists():
            import shutil

            shutil.rmtree(dst_dir)
        dst_dir.parent.mkdir(parents=True, exist_ok=True)
        src_dir.replace(dst_dir)
        if tmp_root.exists():
            with contextlib.suppress(OSError):
                tmp_root.rmdir()
        report_dir = str(dst_dir)
    else:
        result = build_analysis_report(
            seq,
            args.output_root,
            horizon=args.horizon,
            comparison_sequence=comparison,
            export_symbolic_context=args.export_symbolic_context,
        )
        report_dir = str(Path(args.output_root) / result.run_id)
    payload = result.to_dict()
    payload.update({"command": "report", "report_dir": report_dir})
    return _dump_json(payload, args.output)


def cmd_verify_bundle(args: argparse.Namespace) -> int:
    payload = verify_bundle(args.path)
    if not payload["ok"]:
        print(json.dumps(payload, indent=2))
        return 1
    return _dump_json(payload, args.output)


def cmd_validate(args: argparse.Namespace) -> int:
    from mycelium_fractal_net import ValidationConfig, run_validation

    cfg = ValidationConfig(
        seed=args.seed,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grid_size=args.grid_size,
        steps=args.steps,
        turing_enabled=args.turing_enabled,
        quantum_jitter=args.quantum_jitter,
    )
    metrics = run_validation(cfg)
    return _dump_json({"command": "validate", "metrics": metrics}, args.output)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_script(path: Path) -> int:
    completed = subprocess.run([sys.executable, str(path)], check=False)
    return int(completed.returncode)


def cmd_benchmark(args: argparse.Namespace) -> int:
    root = _repo_root() / "benchmarks"
    suites = {
        "core": [root / "benchmark_core.py"],
        "scalability": [root / "benchmark_scalability.py"],
        "quality": [root / "benchmark_quality.py"],
        "all": [
            root / "benchmark_core.py",
            root / "benchmark_scalability.py",
            root / "benchmark_quality.py",
        ],
    }
    return max(_run_script(path) for path in suites[args.suite])


def cmd_api(args: argparse.Namespace) -> int:
    import uvicorn

    from mycelium_fractal_net.integration.api_server import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _add_spec(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--grid-size", type=int, default=32)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--alpha", type=float, default=0.18)
    parser.add_argument("--spike-probability", type=float, default=0.25)
    parser.add_argument("--turing-threshold", type=float, default=0.75)
    parser.add_argument("--turing-enabled", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--quantum-jitter", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--jitter-var", type=float, default=0.0005)
    parser.add_argument("--neuromod-profile", type=str, default=None)
    parser.add_argument("--dt-seconds", type=float, default=1.0)
    parser.add_argument("--agonist-concentration-um", type=float, default=None)
    parser.add_argument("--rest-offset-mv", type=float, default=None)
    parser.add_argument("--gain-fluidity-coeff", type=float, default=None)
    parser.add_argument("--observation-noise-profile", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mfn", description="Morphology-aware Field Intelligence Engine CLI"
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="output raw JSON instead of formatted display",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("simulate", help="deterministic field simulation")
    _add_spec(p)
    p.add_argument("--with-history", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--include-arrays", action=argparse.BooleanOptionalAction, default=False)
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("extract", help="morphology-aware feature extraction")
    _add_spec(p)
    p.add_argument("--input-npy", type=str, default=None)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("detect", help="anomaly / regime intelligence")
    _add_spec(p)
    p.add_argument("--input-npy", type=str, default=None)
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("forecast", help="short horizon forecast")
    _add_spec(p)
    p.add_argument("--input-npy", type=str, default=None)
    p.add_argument("--horizon", type=int, default=8)
    p.set_defaults(func=cmd_forecast)

    p = sub.add_parser("compare", help="morphology-aware comparison")
    _add_spec(p)
    p.add_argument("--input-a-npy", type=str, default=None)
    p.add_argument("--input-b-npy", type=str, default=None)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("report", help="build standardized report artifact layout")
    _add_spec(p)
    p.add_argument("--input-npy", type=str, default=None)
    p.add_argument("--compare-npy", type=str, default=None)
    p.add_argument("--horizon", type=int, default=8)
    p.add_argument("--output-root", type=str, default="artifacts/runs")
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument("--export-symbolic-context", action=argparse.BooleanOptionalAction, default=True)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser(
        "verify-bundle",
        help="verify report/release/showcase manifests, hashes, and signatures",
    )
    p.add_argument("path", type=str)
    p.add_argument("--output", type=str, default=None)
    p.set_defaults(func=cmd_verify_bundle)

    p = sub.add_parser("validate", help="run validation cycle")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grid-size", type=int, default=32)
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--turing-enabled", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--quantum-jitter", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--output", type=str, default=None)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("benchmark", help="run benchmark suites")
    p.add_argument("--suite", choices=["core", "scalability", "quality", "all"], default="core")
    p.set_defaults(func=cmd_benchmark)

    p = sub.add_parser("api", help="run FastAPI server")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_api)

    p = sub.add_parser("analyze", help="analyze external data through MFN pipeline")
    p.add_argument("--input", type=str, required=True, help="path to .npy or .csv file")
    p.add_argument(
        "--no-normalize", action="store_true", help="reject out-of-range data instead of rescaling"
    )
    p.set_defaults(func=cmd_analyze)

    sub.add_parser("doctor", help="system health check").set_defaults(func=cmd_doctor)
    sub.add_parser("info", help="system info and metrics").set_defaults(func=cmd_info)
    sub.add_parser("scenarios", help="list available simulation scenarios").set_defaults(
        func=cmd_scenarios
    )
    return parser


def cmd_analyze(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.adapters import FieldAdapter
    from mycelium_fractal_net.cli_display import format_detection, format_simulation

    seq = FieldAdapter.load(args.input, normalize=not args.no_normalize)
    if _wants_json(args):
        payload = seq.to_dict()
        payload["command"] = "analyze"
        payload["source"] = args.input
        return _dump_json(payload, getattr(args, "output", None))
    print(format_simulation(seq))
    print(format_detection(seq.detect()))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_doctor import run_doctor

    print(run_doctor())
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_doctor import run_info

    print(run_info())
    return 0


def cmd_scenarios(args: argparse.Namespace) -> int:
    from mycelium_fractal_net.cli_doctor import run_scenarios

    print(run_scenarios())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except (ValueError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def api_entrypoint() -> None:
    raise SystemExit(main(["api", *sys.argv[1:]]))


def validate_entrypoint() -> None:
    raise SystemExit(main(["validate", *sys.argv[1:]]))


if __name__ == "__main__":
    raise SystemExit(main())
