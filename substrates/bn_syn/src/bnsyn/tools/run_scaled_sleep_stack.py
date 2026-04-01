#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any, Literal

import numpy as np

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
from bnsyn.criticality import PhaseTransitionDetector
from bnsyn.emergence import AttractorCrystallizer
from bnsyn.memory import MemoryConsolidator
from bnsyn.provenance.manifest_builder import build_sleep_stack_manifest
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep import SleepCycle, default_human_sleep_cycle
from bnsyn.temperature.schedule import TemperatureSchedule


def _run_once(
    *,
    seed: int,
    N: int,
    steps_wake: int,
    steps_sleep: int,
    backend: Literal["reference", "accelerated"],
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[int, int]]]:
    pack = seed_all(seed)
    rng = pack.np_rng
    net = Network(
        NetworkParams(N=N, ext_rate_hz=12.0, ext_w_nS=0.6),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=rng,
        backend=backend,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    sleep_cycle = SleepCycle(net, temp_schedule, max_memories=1000, rng=rng)
    consolidator = MemoryConsolidator(capacity=1000)
    phase_detector = PhaseTransitionDetector()
    crystallizer = AttractorCrystallizer(state_dim=N, max_buffer_size=500, snapshot_dim=min(100, N))

    sigma_trace: list[float] = []
    rate_trace: list[float] = []
    raster: list[tuple[int, int]] = []

    injected_current = np.full(N, 80.0, dtype=np.float64)
    for step in range(steps_wake):
        m = net.step(external_current_pA=injected_current)
        sigma_trace.append(float(m["sigma"]))
        rate_trace.append(float(m["spike_rate_hz"]))
        for idx in np.nonzero(net.state.spiked)[0][:200]:
            raster.append((step, int(idx)))
        if (step + 1) % 20 == 0:
            importance = min(1.0, m["spike_rate_hz"] / 10.0)
            sleep_cycle.record_memory(importance)
            consolidator.tag(net.state.V_mV, importance)
        phase_detector.observe(m["sigma"], step + 1)
        crystallizer.observe(net.state.V_mV, temp_schedule.T or 1.0)

    if steps_sleep > 0:
        sleep_stages = default_human_sleep_cycle()
        if steps_sleep != 600:
            scale = steps_sleep / 450
            sleep_stages = [
                s.__class__(
                    stage=s.stage,
                    duration_steps=max(1, int(s.duration_steps * scale)),
                    temperature_range=s.temperature_range,
                    replay_active=s.replay_active,
                    replay_noise=s.replay_noise,
                )
                for s in sleep_stages
            ]
        sleep_summary = sleep_cycle.sleep(sleep_stages)
    else:
        sleep_summary = {"total_steps": 0, "stage_stats": {}}

    transitions = phase_detector.get_transitions()
    attractors = crystallizer.get_attractors()
    cryst_state = crystallizer.get_crystallization_state()

    metrics: dict[str, Any] = {
        "backend": backend,
        "wake": {
            "steps": steps_wake,
            "mean_sigma": float(np.mean(sigma_trace)),
            "std_sigma": float(np.std(sigma_trace)),
            "mean_spike_rate": float(np.mean(rate_trace)),
            "std_spike_rate": float(np.std(rate_trace)),
            "memories_recorded": sleep_cycle.get_memory_count(),
        },
        "sleep": sleep_summary,
        "transitions": len(transitions),
        "attractors": {
            "count": len(attractors),
            "crystallization_progress": float(cryst_state.progress),
            "phase": cryst_state.phase.name,
        },
        "consolidation": consolidator.stats(),
        "trace": {"sigma": sigma_trace, "rate": rate_trace},
    }
    manifest = build_sleep_stack_manifest(
        seed=seed,
        steps_wake=steps_wake,
        steps_sleep=steps_sleep,
        N=N,
        package_version="local",
    )
    return manifest, metrics, raster


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_raster_artifacts(out: Path, first_raster: list[tuple[int, int]]) -> None:
    raster_csv = out / "raster.csv"
    raster_csv.write_text("step,neuron\n" + "\n".join(f"{s},{n}" for s, n in first_raster))

    width, height = 1200, 500
    max_step = max((s for s, _ in first_raster), default=1)
    max_neuron = max((n for _, n in first_raster), default=1)
    points: list[str] = []
    for s, n in first_raster[:20000]:
        x = int((s / max_step) * (width - 20)) + 10
        y = int((n / max_neuron) * (height - 20)) + 10
        points.append(f'<circle cx="{x}" cy="{height - y}" r="1" fill="#1f77b4" />')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        + '<rect width="100%" height="100%" fill="white"/>'
        + "".join(points)
        + "</svg>"
    )
    (out / "raster.svg").write_text(svg)


def _write_plot(out: Path, first_raster: list[tuple[int, int]], n: int) -> None:
    try:
        import matplotlib.pyplot as plt

        xs: list[int]
        ys: list[int]
        if first_raster:
            xs_t, ys_t = zip(*first_raster)
            xs = list(xs_t)
            ys = list(ys_t)
        else:
            xs = []
            ys = []
        plt.figure(figsize=(10, 4))
        plt.scatter(xs, ys, s=2, alpha=0.6)
        plt.xlabel("Wake step")
        plt.ylabel("Neuron index")
        plt.title(f"Scaled wake raster N={n}")
        plt.tight_layout()
        plt.savefig(out / "raster.png", dpi=150)
        plt.close()
    except Exception:
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/local_runs/scaled_sleep_stack_n2000")
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--steps-wake", type=int, default=2400)
    ap.add_argument("--steps-sleep", type=int, default=1800)

    ap.add_argument("--baseline-steps-wake", type=int, default=800)
    ap.add_argument("--baseline-steps-sleep", type=int, default=600)
    ap.add_argument("--determinism-runs", type=int, default=3)
    ap.add_argument("--equivalence-steps-wake", type=int, default=1200)
    ap.add_argument("--skip-backend-equivalence", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--no-raster", action="store_true")
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()

    if args.determinism_runs <= 0:
        raise ValueError("--determinism-runs must be > 0")
    if args.baseline_steps_wake < 0 or args.baseline_steps_sleep < 0:
        raise ValueError("baseline steps must be >= 0")
    if args.equivalence_steps_wake <= 0 and not args.skip_backend_equivalence:
        raise ValueError("--equivalence-steps-wake must be > 0 unless skipping equivalence")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tracemalloc.start()
    t0 = time.perf_counter()

    b_metrics: dict[str, Any] | None
    if args.skip_baseline:
        b_metrics = None
    else:
        b_manifest, b_metrics, _ = _run_once(
            seed=args.seed,
            N=200,
            steps_wake=args.baseline_steps_wake,
            steps_sleep=args.baseline_steps_sleep,
            backend="reference",
        )
        bdir = out / "baseline"
        bdir.mkdir(exist_ok=True)
        (bdir / "manifest.json").write_text(json.dumps(b_manifest, indent=2))
        (bdir / "metrics.json").write_text(json.dumps(b_metrics, indent=2))

    hashes: list[dict[str, str]] = []
    first_metrics: dict[str, Any] | None = None
    first_raster: list[tuple[int, int]] = []
    for i in range(args.determinism_runs):
        manifest, metrics, raster = _run_once(
            seed=args.seed,
            N=args.n,
            steps_wake=args.steps_wake,
            steps_sleep=args.steps_sleep,
            backend="reference",
        )
        rdir = out / f"scaled_run{i + 1}"
        rdir.mkdir(exist_ok=True)
        mp = rdir / "manifest.json"
        kp = rdir / "metrics.json"
        mp.write_text(json.dumps(manifest, indent=2))
        kp.write_text(json.dumps(metrics, indent=2))
        hashes.append({"manifest": _sha(mp), "metrics": _sha(kp)})
        if first_metrics is None:
            first_metrics = metrics
            first_raster = raster

    backend_equivalence: dict[str, Any]
    if args.skip_backend_equivalence:
        backend_equivalence = {
            "atol": 1e-8,
            "equivalent": None,
            "max_abs_sigma_diff": None,
            "skipped": True,
        }
    else:
        _, m_ref, _ = _run_once(
            seed=args.seed,
            N=args.n,
            steps_wake=args.equivalence_steps_wake,
            steps_sleep=0,
            backend="reference",
        )
        _, m_acc, _ = _run_once(
            seed=args.seed,
            N=args.n,
            steps_wake=args.equivalence_steps_wake,
            steps_sleep=0,
            backend="accelerated",
        )
        ref_trace = np.asarray(m_ref["trace"]["sigma"], dtype=np.float64)
        acc_trace = np.asarray(m_acc["trace"]["sigma"], dtype=np.float64)
        backend_equivalence = {
            "atol": 1e-8,
            "equivalent": bool(np.allclose(ref_trace, acc_trace, atol=1e-8, rtol=0.0)),
            "max_abs_sigma_diff": float(np.max(np.abs(ref_trace - acc_trace))),
            "skipped": False,
        }

    current, peak = tracemalloc.get_traced_memory()
    elapsed = time.perf_counter() - t0
    tracemalloc.stop()

    if first_metrics is None:
        raise RuntimeError("No scaled runs executed")

    variance_reduction: float | None
    baseline_summary: dict[str, float | int] | None
    if b_metrics is None:
        variance_reduction = None
        baseline_summary = None
    else:
        variance_reduction = 100.0 * (
            (b_metrics["wake"]["std_sigma"] - first_metrics["wake"]["std_sigma"])
            / max(b_metrics["wake"]["std_sigma"], 1e-12)
        )
        baseline_summary = {
            "wake_std_sigma": b_metrics["wake"]["std_sigma"],
            "transitions": b_metrics["transitions"],
            "attractors": b_metrics["attractors"]["count"],
        }

    determinism_identical: bool | None
    if args.determinism_runs < 2:
        determinism_identical = None
    else:
        determinism_identical = all(h == hashes[0] for h in hashes[1:])

    summary = {
        "seed": args.seed,
        "N_scaled": args.n,
        "steps_wake_scaled": args.steps_wake,
        "steps_sleep_scaled": args.steps_sleep,
        "determinism_runs": args.determinism_runs,
        "determinism_hashes": hashes,
        "determinism_identical": determinism_identical,
        "backend_equivalence": backend_equivalence,
        "baseline_skipped": args.skip_baseline,
        "variance_reduction_sigma_std_percent_vs_baseline": variance_reduction,
        "baseline": baseline_summary,
        "scaled": {
            "wake_std_sigma": first_metrics["wake"]["std_sigma"],
            "transitions": first_metrics["transitions"],
            "attractors": first_metrics["attractors"]["count"],
            "crystallization_progress": first_metrics["attractors"]["crystallization_progress"],
        },
        "benchmark": {
            "elapsed_s": elapsed,
            "memory_current_bytes": current,
            "memory_peak_bytes": peak,
        },
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))

    if not args.no_raster:
        _write_raster_artifacts(out, first_raster)
    if not args.no_plots:
        _write_plot(out, first_raster, args.n)


if __name__ == "__main__":  # pragma: no cover
    main()
