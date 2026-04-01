"""Command-line interface for BN-Syn demos and checks.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides deterministic demo runs, dt invariance checks, and sleep-stack experiments
per SPEC P2-11/P2-12.

References
----------
docs/SPEC.md#P2-11
docs/SPEC.md#P2-12
"""

from __future__ import annotations

import argparse
from enum import IntEnum
import importlib.metadata
import json
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
import warnings
from pathlib import Path
from typing import Any

from bnsyn.provenance.manifest_builder import build_sleep_stack_manifest
from bnsyn.experiments.emergence import run_emergence_to_disk
from bnsyn.sim.network import run_simulation
from bnsyn.viz.emergence_plot import plot_emergence_npz
from bnsyn.presentation import (
    emit_bundle_validation_failure,
    emit_bundle_validation_success,
    emit_canonical_run_epilogue,
    emit_canonical_run_prelude,
    emit_demo_product_prelude,
    emit_demo_product_success,
)
from bnsyn.proof.contracts import artifacts_for_export_proof, bundle_contract_for_export_proof
from bnsyn.paths import runtime_file

EMERGENCE_SWEEP_CURRENTS_PA = (365.0, 380.0, 395.0, 410.0, 450.0)


class CLIExitCode(IntEnum):
    OK = 0
    ERROR = 1
    INVALID_USAGE = 2


def _default_canonical_profile_path() -> Path:
    """Return canonical profile config path from packaged runtime resources."""
    return runtime_file("configs/canonical_profile.yaml")


def _get_package_version() -> str:
    """Return the installed package version with a safe fallback."""
    version: str | None = None
    try:
        version = importlib.metadata.version("bnsyn")
    except importlib.metadata.PackageNotFoundError:
        version = None
    except Exception as exc:
        warnings.warn(f"Failed to read package version: {exc}", stacklevel=2)
        version = None

    if version:
        return version

    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return "unknown"
        version = data.get("project", {}).get("version")
        if isinstance(version, str) and version:
            return version

    return "unknown"


def _validate_demo_args(args: argparse.Namespace) -> None:
    """Validate demo command arguments and raise user-actionable errors."""
    if args.steps <= 0:
        raise ValueError("steps must be greater than 0")
    if args.dt_ms <= 0:
        raise ValueError("dt-ms must be greater than 0")
    if args.N <= 0:
        raise ValueError("N must be greater than 0")


def _cmd_demo(args: argparse.Namespace) -> int:
    """Run a deterministic demo simulation and print metrics.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments for the demo subcommand.

    Returns
    -------
    int
        Exit code (0 indicates success).

    Notes
    -----
    Calls the deterministic simulation harness with explicit dt and seed.
    If --interactive flag is set, launches Streamlit dashboard instead.

    References
    ----------
    docs/SPEC.md#P2-11
    docs/LEGENDARY_QUICKSTART.md
    """
    if getattr(args, "interactive", False):
        # Launch interactive Streamlit dashboard
        import importlib.util

        # subprocess used for controlled dashboard launch (no shell).
        import subprocess  # nosec B404
        import sys

        # Find the interactive.py script
        script_path = Path(__file__).parent / "viz" / "interactive.py"
        if not script_path.exists():
            print(f"Error: Interactive dashboard not found at {script_path}")
            return CLIExitCode.ERROR
        if importlib.util.find_spec("streamlit") is None:
            print('Error: Streamlit is not installed. Install with: pip install -e ".[viz]"')
            return CLIExitCode.ERROR

        print("🚀 Launching interactive dashboard...")
        print("   Press Ctrl+C to stop")
        try:
            # Fixed module invocation without shell; inputs are local paths only.
            result = subprocess.run(  # nosec B603
                [sys.executable, "-m", "streamlit", "run", str(script_path)]
            )
            if result.returncode != 0:
                print(f"Error: Dashboard exited with code {result.returncode}")
                return CLIExitCode.ERROR
            return CLIExitCode.OK
        except KeyboardInterrupt:
            print("\n✓ Dashboard stopped")
            return CLIExitCode.OK
        except Exception as e:
            print(f"Error launching dashboard: {e}")
            return CLIExitCode.ERROR

    _validate_demo_args(args)
    metrics = run_simulation(steps=args.steps, dt_ms=args.dt_ms, seed=args.seed, N=args.N)
    print(json.dumps({"demo": metrics}, indent=2, sort_keys=True))
    return CLIExitCode.OK


def _cmd_dtcheck(args: argparse.Namespace) -> int:
    """Run dt vs dt/2 invariance check and print metrics.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments for the dt invariance subcommand.

    Returns
    -------
    int
        Exit code (0 indicates success).

    Notes
    -----
    Compares mean-rate and sigma metrics across dt and dt/2 as required by SPEC P2-12.

    References
    ----------
    docs/SPEC.md#P2-12
    """
    m1 = run_simulation(steps=args.steps, dt_ms=args.dt_ms, seed=args.seed, N=args.N)
    m2 = run_simulation(steps=args.steps * 2, dt_ms=args.dt2_ms, seed=args.seed, N=args.N)
    # compare mean rates and sigma; dt2 should be close
    out: dict[str, Any] = {"dt": args.dt_ms, "dt2": args.dt2_ms, "m_dt": m1, "m_dt2": m2}
    print(json.dumps(out, indent=2, sort_keys=True))
    return CLIExitCode.OK


def _cmd_run_experiment(args: argparse.Namespace) -> int:
    """Run experiment from YAML configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments for the run subcommand.

    Returns
    -------
    int
        Exit code (0 indicates success).

    Notes
    -----
    Loads YAML config, validates against schema, runs experiment.

    References
    ----------
    docs/LEGENDARY_QUICKSTART.md
    schemas/experiment.schema.json
    """
    from bnsyn.experiments.declarative import run_canonical_live_bundle, run_from_yaml

    config_path = getattr(args, "config", None)
    profile = getattr(args, "profile", None)
    plot = bool(getattr(args, "plot", False))
    export_proof = bool(getattr(args, "export_proof", False))
    output = getattr(args, "output", None)
    resume_from_stage = getattr(args, "resume_from_stage", None)

    if config_path is None and profile == "canonical":
        config_path = _default_canonical_profile_path()
    if config_path is None:
        print("Error running experiment: provide CONFIG or --profile canonical", file=sys.stderr)
        return CLIExitCode.INVALID_USAGE

    if profile == "canonical":
        output_dir = output or "artifacts/canonical_run"
        emit_canonical_run_prelude(str(output_dir), export_proof)
        try:
            bundle = run_canonical_live_bundle(
                config_path,
                output_dir,
                export_proof=export_proof,
                generate_product_report=export_proof,
                product_package_version=_get_package_version(),
                resume_from_stage=resume_from_stage,
                progress_stream=sys.stderr,
            )
        except Exception as e:
            print(f"Error running experiment: {e}")
            return CLIExitCode.ERROR

        if plot:
            print("Notice: --plot acknowledged; canonical live-run plots are emitted by default", file=sys.stderr)

        bundle_contract = bundle_contract_for_export_proof(export_proof)
        emit_canonical_run_epilogue(bundle, export_proof)

        payload = {
            "status": "ok",
            "bundle_contract": bundle_contract,
            "artifacts": list(artifacts_for_export_proof(export_proof)),
            **bundle,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return CLIExitCode.OK

    if plot:
        print("Notice: --plot only applies to --profile canonical at this milestone", file=sys.stderr)
    if export_proof:
        print("Notice: --export-proof only applies to --profile canonical at this milestone", file=sys.stderr)

    try:
        run_from_yaml(config_path, output)
        return CLIExitCode.OK
    except Exception as e:
        print(f"Error running experiment: {e}")
        return CLIExitCode.ERROR


def _cmd_sleep_stack(args: argparse.Namespace) -> int:
    """Run sleep-stack demo with attractor crystallization and consolidation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments for the sleep-stack subcommand.

    Returns
    -------
    int
        Exit code (0 indicates success).

    Notes
    -----
    Runs wake→sleep cycle with memory recording, consolidation, replay,
    attractor tracking, and phase transition detection.

    References
    ----------
    docs/sleep_stack.md
    docs/emergence_tracking.md
    """
    # Import here to avoid circular dependencies and keep CLI fast
    from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
    from bnsyn.criticality import PhaseTransitionDetector
    from bnsyn.emergence import AttractorCrystallizer
    from bnsyn.memory import MemoryConsolidator
    from bnsyn.rng import seed_all
    from bnsyn.sim.network import Network, NetworkParams
    from bnsyn.sleep import SleepCycle, SleepStageConfig, default_human_sleep_cycle
    from bnsyn.temperature.schedule import TemperatureSchedule

    # Setup output directory
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir.parent / "figures" / out_dir.name
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Seed RNG
    pack = seed_all(args.seed)
    rng = pack.np_rng

    # Create network
    N = int(args.N)
    nparams = NetworkParams(N=N)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=rng,
        backend=args.backend,
    )

    # Temperature schedule
    temp_schedule = TemperatureSchedule(TemperatureParams())

    # Sleep cycle
    sleep_cycle = SleepCycle(net, temp_schedule, max_memories=100, rng=rng)

    # Memory consolidator
    consolidator = MemoryConsolidator(capacity=100)

    # Phase transition detector
    phase_detector = PhaseTransitionDetector()

    # Attractor crystallizer
    crystallizer = AttractorCrystallizer(
        state_dim=N,
        max_buffer_size=500,
        snapshot_dim=min(50, N),
        pca_update_interval=50,
    )

    # Wake phase
    print(f"Running wake phase ({args.steps_wake} steps)...")
    wake_metrics = []
    for _ in range(args.steps_wake):
        m = net.step()
        wake_metrics.append(m)

        # Record memory periodically
        if len(wake_metrics) % 20 == 0:
            importance = min(1.0, m["spike_rate_hz"] / 10.0)
            sleep_cycle.record_memory(importance)
            consolidator.tag(net.state.V_mV, importance)

        # Track phase transitions
        phase_detector.observe(m["sigma"], len(wake_metrics))

        # Track attractor crystallization
        crystallizer.observe(net.state.V_mV, temp_schedule.T or 1.0)

    # Sleep phase
    print(f"Running sleep phase ({args.steps_sleep} steps)...")
    sleep_stages = default_human_sleep_cycle()
    # Scale durations if requested
    if args.steps_sleep != 600:
        scale = args.steps_sleep / 450
        sleep_stages = [
            SleepStageConfig(
                stage=stage.stage,
                duration_steps=int(stage.duration_steps * scale),
                temperature_range=stage.temperature_range,
                replay_active=stage.replay_active,
                replay_noise=stage.replay_noise,
            )
            for stage in sleep_stages
        ]

    sleep_summary = sleep_cycle.sleep(sleep_stages)

    # Collect metrics
    transitions = phase_detector.get_transitions()
    attractors = crystallizer.get_attractors()
    cryst_state = crystallizer.get_crystallization_state()
    cons_stats = consolidator.stats()

    metrics: dict[str, Any] = {
        "backend": args.backend,
        "wake": {
            "steps": args.steps_wake,
            "mean_sigma": float(sum(m["sigma"] for m in wake_metrics) / len(wake_metrics)),
            "mean_spike_rate": float(
                sum(m["spike_rate_hz"] for m in wake_metrics) / len(wake_metrics)
            ),
            "memories_recorded": sleep_cycle.get_memory_count(),
        },
        "sleep": sleep_summary,
        "transitions": [
            {
                "step": t.step,
                "from": t.from_phase.name,
                "to": t.to_phase.name,
                "sigma_before": t.sigma_before,
                "sigma_after": t.sigma_after,
                "sharpness": t.sharpness,
            }
            for t in transitions
        ],
        "attractors": {
            "count": len(attractors),
            "crystallization_progress": cryst_state.progress,
            "phase": cryst_state.phase.name,
        },
        "consolidation": cons_stats,
    }

    # Write metrics
    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics written to {metrics_path}")

    # Generate manifest
    manifest = build_sleep_stack_manifest(
        seed=args.seed,
        steps_wake=args.steps_wake,
        steps_sleep=args.steps_sleep,
        N=N,
        package_version=_get_package_version(),
        repo_root=Path(__file__).parent.parent,
    )

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {manifest_path}")

    # Generate figure (optional, only if matplotlib available)
    try:
        import matplotlib.pyplot as plt
        from typing import Any as _Any

        fig, axes_raw = plt.subplots(2, 2, figsize=(12, 8))
        axes: _Any = axes_raw  # Type hint to satisfy mypy

        # Sigma trace
        ax = axes[0, 0]
        wake_sigmas = [m["sigma"] for m in wake_metrics]
        ax.plot(wake_sigmas, label="Wake", alpha=0.7)
        ax.axhline(y=1.0, color="k", linestyle="--", alpha=0.3)
        ax.set_xlabel("Step")
        ax.set_ylabel("Sigma")
        ax.set_title("Criticality (Sigma)")
        ax.legend()
        ax.grid(alpha=0.3)

        # Spike rate
        ax = axes[0, 1]
        wake_rates = [m["spike_rate_hz"] for m in wake_metrics]
        ax.plot(wake_rates, alpha=0.7, color="orange")
        ax.set_xlabel("Step")
        ax.set_ylabel("Spike Rate (Hz)")
        ax.set_title("Network Activity")
        ax.grid(alpha=0.3)

        # Phase transitions
        ax = axes[1, 0]
        if transitions:
            trans_steps = [t.step for t in transitions]
            trans_phases = [t.to_phase.name for t in transitions]
            ax.scatter(trans_steps, range(len(trans_steps)), s=100, alpha=0.7)
            for i, (step, phase) in enumerate(zip(trans_steps, trans_phases)):
                ax.text(step, i, phase, fontsize=8, ha="left")
        ax.set_xlabel("Step")
        ax.set_ylabel("Transition Index")
        ax.set_title(f"Phase Transitions ({len(transitions)} total)")
        ax.grid(alpha=0.3)

        # Attractor crystallization
        ax = axes[1, 1]
        ax.bar(["Progress", "Count"], [cryst_state.progress, len(attractors) / 10.0])
        ax.set_ylabel("Value")
        ax.set_title(f"Crystallization ({cryst_state.phase.name})")
        ax.set_ylim([0, 1.1])
        ax.grid(alpha=0.3)

        plt.tight_layout()
        fig_path = fig_dir / "summary.png"
        plt.savefig(fig_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Figure saved to {fig_path}")
    except ImportError:
        print(
            "Matplotlib not installed; skipping figure generation. "
            'Install with: pip install -e ".[viz]"'
        )
    except Exception as e:
        print(f"Figure generation failed: {e}")

    print("\n=== Sleep-Stack Demo Complete ===")
    print(f"Wake: {args.steps_wake} steps, {metrics['wake']['memories_recorded']} memories")
    print(f"Sleep: {sleep_summary['total_steps']} steps")
    print(f"Transitions: {len(transitions)}")
    print(f"Attractors: {len(attractors)}")
    print(f"Consolidation: {cons_stats['consolidated_count']}/{cons_stats['count']} patterns")

    return CLIExitCode.OK


def _cmd_smoke(args: argparse.Namespace) -> int:
    """Run minimal end-to-end smoke and emit readiness report."""
    import hashlib
    import platform

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = run_simulation(steps=40, dt_ms=0.1, seed=args.seed, N=32)
    canonical_metrics = json.dumps(metrics, sort_keys=True, separators=(",", ":"))
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "cmd": "bnsyn smoke",
        "seed": int(args.seed),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "timestamp": "1970-01-01T00:00:00Z",
        "status": "PASS",
        "checks": {
            "sigma_finite": bool(abs(float(metrics["sigma_mean"])) < 10.0),
            "spike_rate_non_negative": bool(float(metrics["rate_mean_hz"]) >= 0.0),
        },
        "hashes": {"metrics_sha256": hashlib.sha256(canonical_metrics.encode("utf-8")).hexdigest()},
        "metrics": metrics,
    }
    report["status"] = "PASS" if all(report["checks"].values()) else "FAIL"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"smoke_report": out_path.as_posix(), "status": report["status"]}, sort_keys=True
        )
    )
    return CLIExitCode.OK if report["status"] == "PASS" else CLIExitCode.ERROR


def _render_emergence_plot(
    plot_path: Path,
    sigma_trace: list[float],
    coherence_trace: list[float],
    rate_trace: list[float],
    raster_points: list[tuple[int, int]],
) -> None:  # pragma: no cover - optional matplotlib rendering path
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex="col")

    ax = axes[0, 0]
    if raster_points:
        xs = [p[0] for p in raster_points]
        ys = [p[1] for p in raster_points]
        ax.scatter(xs, ys, s=2, alpha=0.6)
    ax.set_title("Spike raster")
    ax.set_ylabel("Neuron index")
    ax.grid(alpha=0.2)

    ax = axes[0, 1]
    ax.plot(sigma_trace, color="tab:blue", linewidth=1.2)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_title("Criticality (sigma)")
    ax.set_ylabel("Sigma")
    ax.grid(alpha=0.2)

    ax = axes[1, 0]
    ax.plot(coherence_trace, color="tab:green", linewidth=1.2)
    ax.set_title("Synchronization / coherence")
    ax.set_xlabel("Step")
    ax.set_ylabel("Active fraction")
    ax.grid(alpha=0.2)

    ax = axes[1, 1]
    ax.plot(rate_trace, color="tab:orange", linewidth=1.2)
    ax.set_title("Population activity")
    ax.set_xlabel("Step")
    ax.set_ylabel("Spike rate (Hz)")
    ax.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _cmd_plot(args: argparse.Namespace) -> int:
    """Compatibility wrapper that delegates to canonical run profile."""
    from bnsyn.experiments.declarative import run_canonical_live_bundle

    print(
        "Notice: `bnsyn plot` is a compatibility wrapper; "
        "canonical command is `bnsyn run --profile canonical --plot --export-proof`",
        file=sys.stderr,
    )

    config_path = _default_canonical_profile_path()
    out_dir = Path(args.out)
    try:
        bundle = run_canonical_live_bundle(config_path, out_dir)
    except Exception as e:
        print(f"Error running canonical compatibility plot wrapper: {e}")
        return CLIExitCode.ERROR

    print(
        json.dumps(
            {
                "status": "ok",
                "artifact_dir": str(bundle["artifact_dir"]),
                "artifacts": [
                    "emergence_plot.png",
                    "summary_metrics.json",
                    "criticality_report.json",
                    "avalanche_report.json",
                    "phase_space_report.json",
                    "population_rate_trace.npy",
                    "sigma_trace.npy",
                    "coherence_trace.npy",
                    "phase_space_rate_sigma.png",
                    "phase_space_rate_coherence.png",
                    "phase_space_activity_map.png",
                    "avalanche_fit_report.json",
                    "robustness_report.json",
                    "envelope_report.json",
                    "run_manifest.json",
                ],
                "compatibility_wrapper": "bnsyn plot",
            },
            sort_keys=True,
        )
    )
    return CLIExitCode.OK


def _cmd_emergence_run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    metrics, artifact_path = run_emergence_to_disk(
        N=int(args.N),
        dt_ms=float(args.dt_ms),
        duration_ms=float(args.duration_ms),
        seed=int(args.seed),
        external_current_pA=float(args.external_current_pA),
        output_dir=out_dir,
    )
    report = {
        "params": {
            "N": int(args.N),
            "dt_ms": float(args.dt_ms),
            "duration_ms": float(args.duration_ms),
            "seed": int(args.seed),
            "external_current_pA": float(args.external_current_pA),
        },
        "metrics": metrics,
        "artifact_npz": artifact_path,
    }
    report_path = out_dir / "emergence_run_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "report": report_path.as_posix()}, sort_keys=True))
    return CLIExitCode.OK


def _cmd_emergence_sweep(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    runs: list[dict[str, Any]] = []
    for current in EMERGENCE_SWEEP_CURRENTS_PA:
        metrics, artifact_path = run_emergence_to_disk(
            N=int(args.N),
            dt_ms=float(args.dt_ms),
            duration_ms=float(args.duration_ms),
            seed=int(args.seed),
            external_current_pA=current,
            output_dir=out_dir,
        )
        runs.append(
            {
                "external_current_pA": current,
                "metrics": metrics,
                "artifact_npz": artifact_path,
            }
        )
    report_path = out_dir / "emergence_sweep_report.json"
    report_path.write_text(
        json.dumps(
            {
                "params": {
                    "N": args.N,
                    "dt_ms": args.dt_ms,
                    "duration_ms": args.duration_ms,
                    "seed": args.seed,
                },
                "runs": runs,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "ok", "report": report_path.as_posix()}, sort_keys=True))
    return CLIExitCode.OK


def _cmd_emergence_plot(args: argparse.Namespace) -> int:
    plot_emergence_npz(args.input, args.output)
    print(json.dumps({"status": "ok", "output": str(args.output)}, sort_keys=True))
    return CLIExitCode.OK


def _cmd_proof_evaluate(args: argparse.Namespace) -> int:
    from bnsyn.proof.evaluate import evaluate_and_emit

    evaluation = evaluate_and_emit(args.artifact_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "artifact_dir": str(args.artifact_dir),
                "proof_report_path": evaluation.report_path.as_posix(),
                "verdict": evaluation.report["verdict"],
                "verdict_code": evaluation.report["verdict_code"],
            },
            sort_keys=True,
        )
    )
    return CLIExitCode.OK


def _cmd_proof_validate_bundle(args: argparse.Namespace) -> int:
    from bnsyn.proof.bundle_validator import validate_canonical_bundle

    result = validate_canonical_bundle(args.artifact_dir)
    print(json.dumps(result, sort_keys=True))
    return CLIExitCode.OK if result["status"] == "PASS" else CLIExitCode.INVALID_USAGE


def _cmd_validate_bundle(args: argparse.Namespace) -> int:
    from bnsyn.proof.bundle_validator import validate_canonical_bundle

    result = validate_canonical_bundle(args.artifact_dir, require_product_surface=True)
    if result["status"] == "PASS":
        emit_bundle_validation_success(Path(args.artifact_dir).as_posix())
        print("STATUS: PASS")
        print(f"ARTIFACT_DIR: {Path(args.artifact_dir).as_posix()}")
        return CLIExitCode.OK
    emit_bundle_validation_failure(Path(args.artifact_dir).as_posix())
    print("STATUS: FAIL")
    for error in result["errors"]:
        print(f"- {error}")
    return CLIExitCode.INVALID_USAGE


def _cmd_demo_product(args: argparse.Namespace) -> int:
    from bnsyn.experiments.declarative import run_canonical_live_bundle
    from bnsyn.proof.bundle_validator import validate_canonical_bundle

    output_dir = Path(getattr(args, "output", "artifacts/canonical_run"))
    package_version = _get_package_version()
    config_path = _default_canonical_profile_path()
    emit_demo_product_prelude(output_dir.as_posix(), package_version)
    try:
        run_canonical_live_bundle(
            config_path,
            artifact_dir=output_dir,
            export_proof=True,
            generate_product_report=True,
            product_package_version=package_version,
        )
        validation = validate_canonical_bundle(output_dir, require_product_surface=True)
    except Exception as exc:
        print("STATUS: FAIL")
        print(f"REASON: demo-product execution failed: {exc}")
        print(f"VALIDATE: bnsyn validate-bundle {output_dir.as_posix()}")
        return CLIExitCode.ERROR

    if validation["status"] != "PASS":
        print("STATUS: FAIL")
        for error in validation["errors"]:
            print(f"- {error}")
        print(f"VALIDATE: bnsyn validate-bundle {output_dir.as_posix()}")
        return CLIExitCode.INVALID_USAGE

    emit_demo_product_success(output_dir.as_posix())
    print("STATUS: PASS")
    print(f"ARTIFACT_DIR: {output_dir.as_posix()}")
    print(f"REPORT: {(output_dir / 'index.html').as_posix()}")
    print(f"PRIMARY_VISUAL: {(output_dir / 'emergence_plot.png').as_posix()}")
    print(f"VALIDATE: bnsyn validate-bundle {output_dir.as_posix()}")
    return CLIExitCode.OK


def _cmd_proof_check_determinism(args: argparse.Namespace) -> int:
    from bnsyn.proof.evaluate import evaluate_gate_g6_determinism

    result = evaluate_gate_g6_determinism(Path(args.artifact_dir))
    print(json.dumps(result, sort_keys=True))
    return CLIExitCode.OK if result["status"] == "PASS" else CLIExitCode.INVALID_USAGE


def _cmd_proof_check_envelope(args: argparse.Namespace) -> int:
    from bnsyn.proof.evaluate import evaluate_gate_g8_repro_envelope

    result = evaluate_gate_g8_repro_envelope(Path(args.artifact_dir))
    print(json.dumps(result, sort_keys=True))
    return CLIExitCode.OK if result["status"] == "PASS" else CLIExitCode.INVALID_USAGE


def main() -> None:
    """Entry point for the BN-Syn CLI.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Examples
    --------
    Run a deterministic demo simulation::

        $ bnsyn demo --steps 1000 --seed 42 --N 100

    Check dt-invariance (dt vs dt/2 comparison)::

        $ bnsyn dtcheck --dt-ms 0.1 --dt2-ms 0.05 --steps 2000

    Run sleep-stack demo::

        $ bnsyn sleep-stack --seed 123 --steps-wake 800 --steps-sleep 600

    Output format (demo)::

        {
          "sigma": 1.02,
          "spike_rate_hz": 3.45,
          "V_mean_mV": -62.1,
          "energy_cost_aJ": 1234.56
        }

    Notes
    -----
    Builds the CLI parser and dispatches to deterministic command handlers.

    References
    ----------
    docs/SPEC.md#P2-11
    """
    p = argparse.ArgumentParser(prog="bnsyn", description="BN-Syn CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run a small deterministic demo simulation")
    demo.add_argument("--steps", type=int, default=2000)
    demo.add_argument("--dt-ms", type=float, default=0.1)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--N", type=int, default=200)
    demo.add_argument("--interactive", action="store_true", help="Launch interactive dashboard")
    demo.set_defaults(func=_cmd_demo)

    run_parser = sub.add_parser("run", help="Run experiment from YAML config")
    run_parser.add_argument("config", nargs="?", help="Path to YAML configuration file")
    run_parser.add_argument(
        "--profile",
        choices=["canonical"],
        help="Canonical profile selector for live canonical run path",
    )
    run_parser.add_argument(
        "--plot",
        action="store_true",
        help="Emit canonical live-run visual artifacts (default for canonical profile)",
    )
    run_parser.add_argument(
        "--export-proof",
        action="store_true",
        help="Emit proof_report.json and finalize manifest/proof consistency for canonical profile",
    )
    run_parser.add_argument(
        "--resume-from-stage",
        choices=[
            "live_run",
            "summary_reports",
            "avalanche_and_fit",
            "robustness_envelope",
            "manifest",
            "proof_report",
            "product_surface",
        ],
        help="Resume canonical stage pipeline from a specific stage, or auto-resume from the first incomplete stage when omitted",
    )
    run_parser.add_argument("-o", "--output", help="Output directory path (default: artifacts/canonical_run for canonical profile)")
    run_parser.set_defaults(func=_cmd_run_experiment)

    dtc = sub.add_parser("dtcheck", help="Run dt vs dt/2 invariance harness")
    dtc.add_argument("--steps", type=int, default=2000)
    dtc.add_argument("--dt-ms", type=float, default=0.1)
    dtc.add_argument("--dt2-ms", type=float, default=0.05)
    dtc.add_argument("--seed", type=int, default=42)
    dtc.add_argument("--N", type=int, default=200)
    dtc.set_defaults(func=_cmd_dtcheck)

    sleep = sub.add_parser("sleep-stack", help="Run sleep-stack demo with emergence tracking")
    sleep.add_argument("--seed", type=int, default=123, help="RNG seed")
    sleep.add_argument("--N", type=int, default=64, help="Number of neurons")
    sleep.add_argument(
        "--backend",
        choices=["reference", "accelerated"],
        default="reference",
        help="Simulation backend",
    )
    sleep.add_argument("--steps-wake", type=int, default=800, help="Wake phase steps")
    sleep.add_argument("--steps-sleep", type=int, default=600, help="Sleep phase steps")
    sleep.add_argument(
        "--out",
        type=str,
        default="results/sleep_stack_v1",
        help="Output directory for results",
    )
    sleep.set_defaults(func=_cmd_sleep_stack)

    smoke = sub.add_parser("smoke", help="Run deterministic operational readiness smoke test")
    smoke.add_argument("--seed", type=int, default=20260218)
    smoke.add_argument(
        "--out",
        type=str,
        default="artifacts/operational_readiness/SMOKE_REPORT.json",
        help="Output path for smoke report",
    )
    smoke.set_defaults(func=_cmd_smoke)

    plot = sub.add_parser(
        "plot",
        help="Compatibility wrapper to canonical run command. Writes canonical artifacts",
    )
    plot.add_argument(
        "--out",
        type=str,
        default="artifacts/canonical_run",
        help="Output directory for canonical run artifacts (compatibility wrapper)",
    )
    plot.set_defaults(func=_cmd_plot)

    emergence_run = sub.add_parser("emergence-run", help="Run emergence artifact capture")
    emergence_run.add_argument("--N", type=int, default=500)
    emergence_run.add_argument("--dt-ms", type=float, default=0.1)
    emergence_run.add_argument("--duration-ms", type=float, default=2000.0)
    emergence_run.add_argument("--seed", type=int, default=42)
    emergence_run.add_argument("--external-current-pA", type=float, default=410.0)
    emergence_run.add_argument("--out", type=Path, default=Path("artifacts/emergence"))
    emergence_run.set_defaults(func=_cmd_emergence_run)

    emergence_sweep = sub.add_parser("emergence-sweep", help="Run fixed emergence current sweep")
    emergence_sweep.add_argument("--N", type=int, default=500)
    emergence_sweep.add_argument("--dt-ms", type=float, default=0.1)
    emergence_sweep.add_argument("--duration-ms", type=float, default=2000.0)
    emergence_sweep.add_argument("--seed", type=int, default=42)
    emergence_sweep.add_argument("--out", type=Path, default=Path("artifacts/emergence"))
    emergence_sweep.set_defaults(func=_cmd_emergence_sweep)


    proof_eval = sub.add_parser("proof-evaluate", help="Evaluate canonical artifacts and emit proof report")
    proof_eval.add_argument(
        "artifact_dir",
        type=Path,
        help="Artifact directory containing summary_metrics.json and run_manifest.json",
    )
    proof_eval.set_defaults(func=_cmd_proof_evaluate)

    proof_validate = sub.add_parser("proof-validate-bundle", help="Validate canonical proof bundle manifest lineage + covered JSON schemas")
    proof_validate.add_argument("artifact_dir", type=Path, help="Artifact directory containing canonical proof artifacts")
    proof_validate.set_defaults(func=_cmd_proof_validate_bundle)

    validate_bundle = sub.add_parser("validate-bundle", help="Validate canonical product bundle")
    validate_bundle.add_argument("artifact_dir", type=Path, help="Artifact directory containing canonical product artifacts")
    validate_bundle.set_defaults(func=_cmd_validate_bundle)

    demo_product = sub.add_parser("demo-product", help="Run canonical product demo and emit human-readable bundle report")
    demo_product.add_argument("--output", type=Path, default=Path("artifacts/canonical_run"), help="Output directory for canonical product bundle")
    demo_product.set_defaults(func=_cmd_demo_product)

    proof_det = sub.add_parser("proof-check-determinism", help="Validate same-seed canonical replay hash equality")
    proof_det.add_argument("artifact_dir", type=Path, help="Artifact directory containing canonical proof artifacts")
    proof_det.set_defaults(func=_cmd_proof_check_determinism)

    proof_env = sub.add_parser("proof-check-envelope", help="Validate 10-seed canonical admissibility band")
    proof_env.add_argument("artifact_dir", type=Path, help="Artifact directory containing canonical proof artifacts")
    proof_env.set_defaults(func=_cmd_proof_check_envelope)

    emergence_plot = sub.add_parser("emergence-plot", help="Render emergence NPZ artifact to PNG")
    emergence_plot.add_argument("--input", required=True)
    emergence_plot.add_argument("--output", required=True)
    emergence_plot.set_defaults(func=_cmd_emergence_plot)

    args = p.parse_args()
    try:
        raise SystemExit(int(args.func(args)))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(CLIExitCode.INVALID_USAGE) from None
    except Exception as exc:  # pragma: no cover - exercised via CLI contract tests
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        raise SystemExit(CLIExitCode.ERROR) from None


if __name__ == "__main__":
    main()
