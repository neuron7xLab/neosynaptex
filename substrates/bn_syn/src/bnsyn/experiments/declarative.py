"""Declarative experiment execution from YAML configurations.

Provides YAML-driven experiment runner with schema validation.

References
----------
docs/LEGENDARY_QUICKSTART.md
schemas/experiment.schema.json
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import struct
import tempfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, TextIO, cast

import numpy as np
import yaml  # type: ignore[import-untyped]

from bnsyn.experiments.emergence import run_emergence_to_disk
from bnsyn.experiments.phase_space import (
    build_activity_map,
    build_phase_space_report,
    build_phase_trajectory_image,
)
from bnsyn.numerics import compute_steps_exact
from bnsyn.schemas.experiment import BNSynExperimentConfig
from bnsyn.sim.network import run_simulation
from bnsyn.proof.contracts import bundle_contract_for_export_proof, command_for_export_proof, manifest_self_hash
from bnsyn.rng import seed_all
from bnsyn.viz.product_report import write_product_report_bundle
from bnsyn.paths import runtime_file

CANONICAL_REPRO_SEEDS: tuple[int, ...] = (11, 23, 37, 41, 53, 67, 79, 83, 97, 101)
ENVELOPE_SPEC_PATH = runtime_file("ci/envelope_spec.json")
STAT_POWER_CONFIG_PATH = runtime_file("ci/statistical_power_config.json")
PIPELINE_SCHEMA_VERSION = "1.1.0"
STAGE_ORDER: tuple[str, ...] = (
    "live_run",
    "summary_reports",
    "avalanche_and_fit",
    "robustness_envelope",
    "manifest",
    "proof_report",
    "product_surface",
)


def _derive_subseed(seed: int, *, context: str) -> int:
    payload = f"{context}:{seed}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:4], "big")


def _powerlaw_mle_alpha(tail: np.ndarray, xmin: int) -> float:
    logs = np.log(tail / (float(xmin) - 0.5))
    return 1.0 + float(tail.size) / float(np.sum(logs))


def _powerlaw_ks_distance(tail: np.ndarray, alpha: float, xmin: int) -> float:
    uniq = np.sort(np.unique(tail))
    n = float(tail.size)
    ecdf = np.array([np.count_nonzero(tail <= x) / n for x in uniq], dtype=np.float64)
    cdf = 1.0 - (uniq / (float(xmin) - 0.5)) ** (1.0 - alpha)
    cdf = np.clip(cdf, 0.0, 1.0)
    return float(np.max(np.abs(ecdf - cdf)))


def _fit_power_law(sizes: list[int], seed: int) -> dict[str, Any]:
    policy = json.loads(STAT_POWER_CONFIG_PATH.read_text(encoding="utf-8"))
    min_tail = int(policy["avalanche_admission"]["min_tail_count"])
    p_thresh = float(policy["avalanche_admission"]["p_value_threshold"])
    ks_max = float(policy["avalanche_admission"]["ks_max"])
    monte_carlo_sims = int(policy["avalanche_admission"]["monte_carlo_simulations"])

    all_sizes = np.asarray(sizes, dtype=np.int64)
    positive = all_sizes[all_sizes >= 1]
    if positive.size == 0:
        return {"schema_version":"1.0.0","fit_method":"clauset_continuous_mle_gridsearch","tau_meaning":"tau is the avalanche size-distribution exponent estimated as alpha","alpha":0.0,"tau":0.0,"xmin":0,"ks_distance":1.0,"p_value":0.0,"likelihood_ratio":0.0,"sample_size":0,"validity":{"verdict":"FAIL","reasons":["no positive avalanches"],"thresholds":{"min_tail_count":min_tail,"p_value_min":p_thresh,"ks_max":ks_max}}}

    best: dict[str, Any] | None = None
    for xmin in sorted(set(int(x) for x in positive.tolist())):
        tail = positive[positive >= xmin]
        if tail.size < max(5, min_tail):
            continue
        alpha = _powerlaw_mle_alpha(tail.astype(np.float64), xmin)
        if not math.isfinite(alpha) or alpha <= 1.0:
            continue
        ks = _powerlaw_ks_distance(tail.astype(np.float64), alpha, xmin)
        if best is None or ks < best["ks"]:
            best = {"xmin":xmin,"tail":tail.astype(np.float64),"alpha":alpha,"ks":ks}

    if best is None:
        return {"schema_version":"1.0.0","fit_method":"clauset_continuous_mle_gridsearch","tau_meaning":"tau is the avalanche size-distribution exponent estimated as alpha","alpha":0.0,"tau":0.0,"xmin":0,"ks_distance":1.0,"p_value":0.0,"likelihood_ratio":0.0,"sample_size":int(positive.size),"validity":{"verdict":"FAIL","reasons":["insufficient tail sample for fit"],"thresholds":{"min_tail_count":min_tail,"p_value_min":p_thresh,"ks_max":ks_max}}}

    tail = cast(np.ndarray, best["tail"])
    alpha = float(best["alpha"])
    xmin = int(best["xmin"])
    ks = float(best["ks"])
    rng = seed_all(_derive_subseed(seed, context="avalanche_fit_monte_carlo")).np_rng
    sims = monte_carlo_sims
    sim_ks = []
    for _ in range(sims):
        u = rng.random(tail.size)
        sim = (float(xmin) - 0.5) * (1.0 - u) ** (-1.0 / (alpha - 1.0))
        sim_ks.append(_powerlaw_ks_distance(sim, alpha, xmin))
    p_value = float(np.mean(np.asarray(sim_ks, dtype=np.float64) >= ks))

    ll_power = float(np.sum(np.log((alpha - 1.0) / (float(xmin) - 0.5)) - alpha * np.log(tail / (float(xmin) - 0.5))))
    lam = 1.0 / max(np.mean(tail - float(xmin)), 1e-12)
    ll_exp = float(np.sum(np.log(lam) - lam * (tail - float(xmin))))
    lr = ll_power - ll_exp

    reasons: list[str] = []
    if tail.size < min_tail:
        reasons.append("tail sample below min_tail_count")
    if p_value < p_thresh:
        reasons.append("p_value below threshold")
    if ks > ks_max:
        reasons.append("ks_distance above threshold")
    verdict = "PASS" if not reasons else "FAIL"

    return {
        "schema_version": "1.0.0",
        "fit_method": "clauset_continuous_mle_gridsearch",
        "tau_meaning": "tau is the avalanche size-distribution exponent estimated as alpha",
        "alpha": alpha,
        "tau": alpha,
        "xmin": xmin,
        "ks_distance": ks,
        "p_value": p_value,
        "likelihood_ratio": float(lr),
        "sample_size": int(tail.size),
        "validity": {
            "verdict": verdict,
            "reasons": reasons,
            "thresholds": {"min_tail_count": min_tail, "p_value_min": p_thresh, "ks_max": ks_max},
        },
    }


def _build_repro_reports(config: BNSynExperimentConfig) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = json.loads(ENVELOPE_SPEC_PATH.read_text(encoding="utf-8"))
    metrics_by_seed: list[dict[str, Any]] = []
    replay_hashes: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="bnsyn_repro_") as tmp:
        tmp_root = Path(tmp)
        for seed in CANONICAL_REPRO_SEEDS:
            metrics, npz_path = run_emergence_to_disk(
                N=config.network.size,
                dt_ms=config.simulation.dt_ms,
                duration_ms=config.simulation.duration_ms,
                seed=seed,
                external_current_pA=config.simulation.external_current_pA,
                output_dir=tmp_root / f"seed_{seed}",
            )
            with np.load(npz_path) as data:
                spike_steps = np.asarray(data["spike_steps"], dtype=np.int64)
                steps = int(np.asarray(data["steps"]).item())
            per_step = np.bincount(spike_steps, minlength=steps) if steps > 0 else np.zeros(0, dtype=np.int64)
            aval = _build_avalanche_report(seed=seed,n_neurons=config.network.size,dt_ms=config.simulation.dt_ms,duration_ms=config.simulation.duration_ms,steps=steps,spike_steps_per_step=per_step,bin_width_steps=1)
            fit = _fit_power_law(cast(list[int], aval["sizes"]), seed=seed)
            metrics_by_seed.append({
                "seed": seed,
                "rate_mean_hz": float(metrics["rate_mean_hz"]),
                "sigma_mean": float(metrics["sigma_mean"]),
                "avalanche_count": int(cast(int, aval["avalanche_count"])),
                "avalanche_exponent": float(fit["alpha"]),
            })
            if seed == CANONICAL_REPRO_SEEDS[0]:
                # deterministic replay check for required traces
                replay_traces: dict[str, dict[str, np.ndarray]] = {}
                for run_name in ("run_a", "run_b"):
                    run_dir = tmp_root / run_name
                    _, replay_npz = run_emergence_to_disk(
                        N=config.network.size,
                        dt_ms=config.simulation.dt_ms,
                        duration_ms=config.simulation.duration_ms,
                        seed=seed,
                        external_current_pA=config.simulation.external_current_pA,
                        output_dir=run_dir,
                    )
                    with np.load(replay_npz) as replay_data:
                        replay_traces[run_name] = {
                            "rate_trace_hz": np.asarray(replay_data["rate_trace_hz"], dtype=np.float64),
                            "sigma_trace": np.asarray(replay_data["sigma_trace"], dtype=np.float64),
                            "coherence_trace": np.asarray(replay_data["coherence_trace"], dtype=np.float64),
                        }

                trace_names = (
                    ("population_rate_trace.npy", "rate_trace_hz"),
                    ("sigma_trace.npy", "sigma_trace"),
                    ("coherence_trace.npy", "coherence_trace"),
                )
                for artifact_name, trace_key in trace_names:
                    run_a_trace = replay_traces["run_a"][trace_key]
                    run_b_trace = replay_traces["run_b"][trace_key]
                    h1 = hashlib.sha256(run_a_trace.tobytes()).hexdigest()
                    h2 = hashlib.sha256(run_b_trace.tobytes()).hexdigest()
                    replay_hashes.append({"artifact": artifact_name, "run_a": h1, "run_b": h2})

    tolerances = spec["tolerances"]
    envelope_checks: dict[str, dict[str, Any]] = {}
    fail_reasons: list[str] = []
    for metric in ("rate_mean_hz", "sigma_mean", "avalanche_count", "avalanche_exponent"):
        vals = [float(row[metric]) for row in metrics_by_seed]
        lo = float(min(vals))
        hi = float(max(vals))
        allowed_lo = float(tolerances[metric]["min"])
        allowed_hi = float(tolerances[metric]["max"])
        ok = lo >= allowed_lo and hi <= allowed_hi
        if not ok:
            fail_reasons.append(metric)
        envelope_checks[metric] = {"observed_min": lo, "observed_max": hi, "allowed_min": allowed_lo, "allowed_max": allowed_hi, "status": "PASS" if ok else "FAIL"}

    replay_ok = all(entry["run_a"] == entry["run_b"] for entry in replay_hashes)
    robustness = {
        "schema_version": "1.0.0",
        "seed_set": list(CANONICAL_REPRO_SEEDS),
        "replay_check": {"seed": CANONICAL_REPRO_SEEDS[0], "required_traces": ["population_rate_trace.npy", "sigma_trace.npy", "coherence_trace.npy"], "hashes": replay_hashes, "identical": replay_ok},
        "runs": metrics_by_seed,
    }
    envelope = {
        "schema_version": "1.0.0",
        "spec_version": str(spec["spec_version"]),
        "seed_set": list(CANONICAL_REPRO_SEEDS),
        "metric_checks": envelope_checks,
        "verdict": "PASS" if not fail_reasons else "FAIL",
        "failure_reasons": fail_reasons,
    }
    return robustness, envelope


def load_config(config_path: str | Path) -> BNSynExperimentConfig:
    """Load and validate experiment configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML object, got {type(data).__name__}")

    try:
        return BNSynExperimentConfig(**data)
    except Exception as e:
        msg = f"❌ Config validation failed: {config_path}\n\nError: {e}"
        raise ValueError(msg) from e


def run_experiment(config: BNSynExperimentConfig) -> dict[str, Any]:
    """Run experiment from validated configuration."""
    results: dict[str, Any] = {
        "config": {
            "name": config.experiment.name,
            "version": config.experiment.version,
            "network_size": config.network.size,
            "duration_ms": config.simulation.duration_ms,
            "dt_ms": config.simulation.dt_ms,
            "external_current_pA": config.simulation.external_current_pA,
        },
        "runs": [],
    }

    steps = compute_steps_exact(config.simulation.duration_ms, config.simulation.dt_ms)

    for seed in config.experiment.seeds:
        if config.simulation.artifact_dir is None:
            metrics = run_simulation(
                steps=steps,
                dt_ms=config.simulation.dt_ms,
                seed=seed,
                N=config.network.size,
                external_current_pA=config.simulation.external_current_pA,
            )
            results["runs"].append({"seed": seed, "metrics": metrics})
        else:
            metrics, artifact_npz = run_emergence_to_disk(
                N=config.network.size,
                dt_ms=config.simulation.dt_ms,
                duration_ms=config.simulation.duration_ms,
                seed=seed,
                external_current_pA=config.simulation.external_current_pA,
                output_dir=config.simulation.artifact_dir,
            )
            results["runs"].append({"seed": seed, "metrics": metrics, "artifact_npz": artifact_npz})

    return results


def run_from_yaml(config_path: str | Path, output_path: str | Path | None = None) -> None:
    """Load config from YAML, run experiment, and save results."""
    config = load_config(config_path)
    print(f"✓ Config validated: {config.experiment.name} {config.experiment.version}")
    print(
        f"  Network: N={config.network.size}, "
        f"Duration: {config.simulation.duration_ms}ms, "
        f"dt: {config.simulation.dt_ms}ms"
    )
    print(f"  external_current_pA: {config.simulation.external_current_pA}")
    print(f"  Seeds: {len(config.experiment.seeds)} runs")

    results = run_experiment(config)

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(results, f, indent=2, sort_keys=True)
        print(f"✓ Results saved to {output_path}")
    else:
        print(json.dumps(results, indent=2, sort_keys=True))


def _write_grayscale_png(image: np.ndarray, output_path: Path) -> None:
    """Write a uint8 grayscale image to PNG without external plotting deps."""
    if image.dtype != np.uint8:
        raise ValueError("image must be uint8")
    if image.ndim != 2:
        raise ValueError("image must be 2-D")

    height, width = image.shape
    raw = b"".join(b"\x00" + image[row].tobytes() for row in range(height))
    compressed = zlib.compress(raw, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    output_path.write_bytes(png)


def _build_raster_image(spike_steps: np.ndarray, spike_neurons: np.ndarray, steps: int, n_neurons: int) -> np.ndarray:
    """Build monochrome raster image (white background, black spikes)."""
    width = max(steps, 2)
    height = max(n_neurons, 2)
    image = np.full((height, width), 255, dtype=np.uint8)
    for step, neuron in zip(spike_steps.tolist(), spike_neurons.tolist()):
        if 0 <= step < width and 0 <= neuron < height:
            image[height - 1 - neuron, step] = 0
    return image


def _build_rate_image(rate_trace_hz: np.ndarray, width: int = 1000, height: int = 300) -> np.ndarray:
    """Build monochrome line-plot style image for population-rate trace."""
    image = np.full((height, width), 255, dtype=np.uint8)
    if rate_trace_hz.size == 0:
        return image

    max_rate = float(np.max(rate_trace_hz))
    if max_rate <= 0:
        max_rate = 1.0

    sample_x = np.linspace(0, rate_trace_hz.size - 1, width)
    sampled = np.interp(sample_x, np.arange(rate_trace_hz.size), rate_trace_hz)

    for x, value in enumerate(sampled):
        y = int(round((1.0 - min(1.0, max(0.0, float(value) / max_rate))) * (height - 1)))
        image[y, x] = 0
        if y + 1 < height:
            image[y + 1, x] = 60
        if y > 0:
            image[y - 1, x] = 60

    image[height - 1, :] = 0
    return image


def _build_emergence_image(raster_image: np.ndarray, rate_image: np.ndarray) -> np.ndarray:
    """Build canonical emergence image as a composite of raster + rate traces."""
    if raster_image.ndim != 2 or rate_image.ndim != 2:
        raise ValueError("raster_image and rate_image must be 2D arrays")

    width = max(raster_image.shape[1], rate_image.shape[1])

    def _pad_to_width(image: np.ndarray, target_width: int) -> np.ndarray:
        if image.shape[1] == target_width:
            return image
        pad = np.full((image.shape[0], target_width - image.shape[1]), 255, dtype=np.uint8)
        return np.hstack((image, pad))

    raster = _pad_to_width(raster_image, width)
    rate = _pad_to_width(rate_image, width)
    separator = np.full((4, width), 180, dtype=np.uint8)
    return np.vstack((raster, separator, rate))


def _segment_avalanches(spike_counts: np.ndarray) -> tuple[list[int], list[int]]:
    """Segment contiguous nonzero bins into avalanche sizes and durations."""
    sizes: list[int] = []
    durations: list[int] = []
    current_size = 0
    current_duration = 0

    for count in spike_counts.tolist():
        count_i = int(count)
        if count_i > 0:
            current_size += count_i
            current_duration += 1
            continue
        if current_duration > 0:
            sizes.append(current_size)
            durations.append(current_duration)
            current_size = 0
            current_duration = 0

    if current_duration > 0:
        sizes.append(current_size)
        durations.append(current_duration)

    return sizes, durations


def _build_avalanche_report(
    *,
    seed: int,
    n_neurons: int,
    dt_ms: float,
    duration_ms: float,
    steps: int,
    spike_steps_per_step: np.ndarray,
    bin_width_steps: int = 1,
) -> dict[str, float | int | str | list[int]]:
    """Build deterministic avalanche analysis metrics from per-step spike counts."""
    if bin_width_steps <= 0:
        raise ValueError("bin_width_steps must be >= 1")
    if bin_width_steps != 1:
        usable = (spike_steps_per_step.size // bin_width_steps) * bin_width_steps
        rebinned = spike_steps_per_step[:usable].reshape(-1, bin_width_steps).sum(axis=1)
    else:
        rebinned = spike_steps_per_step

    sizes, durations = _segment_avalanches(np.asarray(rebinned, dtype=np.int64))
    nonempty_bins = int(np.count_nonzero(rebinned > 0))
    total_spikes = int(np.sum(rebinned))
    largest_size = max(sizes) if sizes else 0

    return {
        "schema_version": "1.0.0",
        "seed": seed,
        "N": int(n_neurons),
        "dt_ms": float(dt_ms),
        "duration_ms": float(duration_ms),
        "steps": int(steps),
        "bin_width_steps": int(bin_width_steps),
        "avalanche_count": int(len(sizes)),
        "active_bin_fraction": float(nonempty_bins / rebinned.size) if rebinned.size > 0 else 0.0,
        "size_mean": float(np.mean(sizes)) if sizes else 0.0,
        "size_max": int(largest_size),
        "duration_mean": float(np.mean(durations)) if durations else 0.0,
        "duration_max": int(max(durations)) if durations else 0,
        "sizes": sizes,
        "durations": durations,
        "nonempty_bins": nonempty_bins,
        "largest_avalanche_fraction": float(largest_size / total_spikes) if total_spikes > 0 else 0.0,
        "size_variance": float(np.var(sizes)) if sizes else 0.0,
        "duration_variance": float(np.var(durations)) if durations else 0.0,
    }


def _build_phase_space_report(
    *,
    seed: int,
    n_neurons: int,
    dt_ms: float,
    duration_ms: float,
    steps: int,
    rate_trace_hz: np.ndarray,
    sigma_trace: np.ndarray,
    coherence_trace: np.ndarray,
) -> dict[str, Any]:
    """Build deterministic state-space trajectory report from canonical traces."""
    return build_phase_space_report(
        seed=seed,
        n_neurons=n_neurons,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        steps=steps,
        rate_trace_hz=rate_trace_hz,
        sigma_trace=sigma_trace,
        coherence_trace=coherence_trace,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PipelineContext:
    config: BNSynExperimentConfig
    artifact_dir: Path
    export_proof: bool
    generate_product_report: bool
    product_package_version: str
    resume_from_stage: str | None
    progress_stream: TextIO | None = None
    seed: int = field(init=False)
    steps: int = field(init=False)
    run_manifest_path: Path = field(init=False)
    product_summary_path: Path = field(init=False)
    index_html_path: Path = field(init=False)
    proof_report_path: Path = field(init=False)
    artifact_npz_path: Path | None = None
    emergence_metrics: dict[str, Any] | None = None
    spike_steps: np.ndarray | None = None
    sigma_trace: np.ndarray | None = None
    rate_trace_hz: np.ndarray | None = None
    coherence_trace: np.ndarray | None = None
    spike_neurons: np.ndarray | None = None
    n_neurons: int | None = None
    summary_metrics: dict[str, Any] | None = None
    criticality_report: dict[str, Any] | None = None
    phase_space_report: dict[str, Any] | None = None
    population_rate_trace: np.ndarray | None = None
    phase_space_rate_sigma_image: np.ndarray | None = None
    phase_space_rate_coherence_image: np.ndarray | None = None
    phase_space_activity_map_image: np.ndarray | None = None
    raster_image: np.ndarray | None = None
    population_rate_image: np.ndarray | None = None
    emergence_image: np.ndarray | None = None
    avalanche_report: dict[str, Any] | None = None
    avalanche_fit_report: dict[str, Any] | None = None
    robustness_report: dict[str, Any] | None = None
    envelope_report: dict[str, Any] | None = None
    proof_report: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.seed = int(self.config.experiment.seeds[0])
        self.steps = compute_steps_exact(self.config.simulation.duration_ms, self.config.simulation.dt_ms)
        self.run_manifest_path = self.artifact_dir / "run_manifest.json"
        self.product_summary_path = self.artifact_dir / "product_summary.json"
        self.index_html_path = self.artifact_dir / "index.html"
        self.proof_report_path = self.artifact_dir / "proof_report.json"


def _atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")




def _write_summary_reports_outputs(context: PipelineContext, ctx: PipelineContext) -> dict[str, Any]:
    _write_json(context.artifact_dir / "summary_metrics.json", _require_report(ctx.summary_metrics, "summary_metrics"))
    _write_json(context.artifact_dir / "criticality_report.json", _require_report(ctx.criticality_report, "criticality_report"))
    _write_json(context.artifact_dir / "phase_space_report.json", _require_report(ctx.phase_space_report, "phase_space_report"))
    np.save(context.artifact_dir / "population_rate_trace.npy", _require_array(ctx.population_rate_trace, "population_rate_trace"))
    np.save(context.artifact_dir / "sigma_trace.npy", _require_array(ctx.sigma_trace, "sigma_trace"))
    np.save(context.artifact_dir / "coherence_trace.npy", _require_array(ctx.coherence_trace, "coherence_trace"))
    _write_grayscale_png(_require_array(ctx.phase_space_rate_sigma_image, "phase_space_rate_sigma_image"), context.artifact_dir / "phase_space_rate_sigma.png")
    _write_grayscale_png(_require_array(ctx.phase_space_rate_coherence_image, "phase_space_rate_coherence_image"), context.artifact_dir / "phase_space_rate_coherence.png")
    _write_grayscale_png(_require_array(ctx.phase_space_activity_map_image, "phase_space_activity_map_image"), context.artifact_dir / "phase_space_activity_map.png")
    _write_grayscale_png(_require_array(ctx.raster_image, "raster_image"), context.artifact_dir / "raster_plot.png")
    _write_grayscale_png(_require_array(ctx.population_rate_image, "population_rate_image"), context.artifact_dir / "population_rate_plot.png")
    _write_grayscale_png(_require_array(ctx.emergence_image, "emergence_image"), context.artifact_dir / "emergence_plot.png")
    return {
        "summary_metrics_path": (context.artifact_dir / "summary_metrics.json").as_posix(),
        "criticality_report_path": (context.artifact_dir / "criticality_report.json").as_posix(),
        "phase_space_report_path": (context.artifact_dir / "phase_space_report.json").as_posix(),
        "population_rate_trace_path": (context.artifact_dir / "population_rate_trace.npy").as_posix(),
        "sigma_trace_path": (context.artifact_dir / "sigma_trace.npy").as_posix(),
        "coherence_trace_path": (context.artifact_dir / "coherence_trace.npy").as_posix(),
        "phase_space_rate_sigma_path": (context.artifact_dir / "phase_space_rate_sigma.png").as_posix(),
        "phase_space_rate_coherence_path": (context.artifact_dir / "phase_space_rate_coherence.png").as_posix(),
        "phase_space_activity_map_path": (context.artifact_dir / "phase_space_activity_map.png").as_posix(),
        "raster_plot_path": (context.artifact_dir / "raster_plot.png").as_posix(),
        "population_rate_plot_path": (context.artifact_dir / "population_rate_plot.png").as_posix(),
        "emergence_plot_path": (context.artifact_dir / "emergence_plot.png").as_posix(),
    }


def _write_avalanche_outputs(context: PipelineContext, ctx: PipelineContext) -> dict[str, Any]:
    _write_json(context.artifact_dir / "avalanche_report.json", _require_report(ctx.avalanche_report, "avalanche_report"))
    _write_json(context.artifact_dir / "avalanche_fit_report.json", _require_report(ctx.avalanche_fit_report, "avalanche_fit_report"))
    return {
        "avalanche_report_path": (context.artifact_dir / "avalanche_report.json").as_posix(),
        "avalanche_fit_report_path": (context.artifact_dir / "avalanche_fit_report.json").as_posix(),
    }


def _write_robustness_outputs(context: PipelineContext, ctx: PipelineContext) -> dict[str, Any]:
    _write_json(context.artifact_dir / "robustness_report.json", _require_report(ctx.robustness_report, "robustness_report"))
    _write_json(context.artifact_dir / "envelope_report.json", _require_report(ctx.envelope_report, "envelope_report"))
    return {
        "robustness_report_path": (context.artifact_dir / "robustness_report.json").as_posix(),
        "envelope_report_path": (context.artifact_dir / "envelope_report.json").as_posix(),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_manifest_path(artifact_dir: Path, stage_name: str) -> Path:
    return artifact_dir / f"stage_{stage_name}.json"


def _artifact_hashes_for_outputs(outputs: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, value in outputs.items():
        if not isinstance(value, str):
            continue
        path = Path(value)
        if path.is_file():
            hashes[name] = _sha256_file(path)
    return hashes


def _pipeline_policy(context: PipelineContext) -> dict[str, Any]:
    return {
        "seed": context.seed,
        "steps": context.steps,
        "N": int(context.config.network.size),
        "dt_ms": float(context.config.simulation.dt_ms),
        "duration_ms": float(context.config.simulation.duration_ms),
        "external_current_pA": float(context.config.simulation.external_current_pA),
        "export_proof": bool(context.export_proof),
    }


def _write_stage_record(
    artifact_dir: Path,
    *,
    stage_name: str,
    status: str,
    started_at: str,
    finished_at: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    failure_reason: str | None,
) -> None:
    _write_json(
        _stage_manifest_path(artifact_dir, stage_name),
        {
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "inputs": inputs,
            "outputs": outputs,
            "artifact_hashes": _artifact_hashes_for_outputs(outputs),
            "failure_reason": failure_reason,
        },
    )


def _load_stage_record(artifact_dir: Path, stage_name: str) -> dict[str, Any] | None:
    path = _stage_manifest_path(artifact_dir, stage_name)
    if not path.is_file():
        return None
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema_version") != PIPELINE_SCHEMA_VERSION:
        raise ValueError(
            f"{path.name} schema_version {payload.get('schema_version')!r} is incompatible with {PIPELINE_SCHEMA_VERSION}"
        )
    return payload


def _require_artifacts(stage_name: str, required_paths: dict[str, Path]) -> None:
    missing = [name for name, path in required_paths.items() if not path.exists()]
    if missing:
        joined = ", ".join(sorted(missing))
        raise FileNotFoundError(f"stage_{stage_name} missing required upstream artifacts: {joined}")


def _completed_stage_names(artifact_dir: Path) -> list[str]:
    completed: list[str] = []
    for stage_name in STAGE_ORDER:
        payload = _load_stage_record(artifact_dir, stage_name)
        if payload is None or payload.get("status") != "completed":
            break
        completed.append(stage_name)
    return completed


def _validate_stage_output_hashes(stage_name: str, stage_record: dict[str, Any]) -> bool:
    outputs = stage_record.get("outputs")
    artifact_hashes = stage_record.get("artifact_hashes")
    if not isinstance(outputs, dict) or not isinstance(artifact_hashes, dict):
        return False
    for output_name, output_path in outputs.items():
        if not isinstance(output_path, str):
            return False
        path = Path(output_path)
        expected_hash = artifact_hashes.get(output_name)
        if not path.is_file() or not isinstance(expected_hash, str):
            return False
        if _sha256_file(path) != expected_hash:
            return False
    return True


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return cast(dict[str, Any], payload)


def _first_stage_requiring_rerun(artifact_dir: Path) -> str | None:
    for stage_name in STAGE_ORDER:
        payload = _load_stage_record(artifact_dir, stage_name)
        if payload is None:
            return stage_name
        if payload.get("status") != "completed":
            return stage_name
        if not _validate_stage_output_hashes(stage_name, payload):
            return stage_name
    return None


def _resolve_resume_stage(artifact_dir: Path, resume_from_stage: str | None) -> str | None:
    first_invalid_stage = _first_stage_requiring_rerun(artifact_dir)
    if resume_from_stage is not None:
        if resume_from_stage not in STAGE_ORDER:
            raise ValueError(f"Unknown resume stage: {resume_from_stage}")
        if first_invalid_stage is not None and STAGE_ORDER.index(first_invalid_stage) < STAGE_ORDER.index(resume_from_stage):
            raise ValueError(
                f"Cannot resume from {resume_from_stage}: upstream artifact integrity requires rerun from {first_invalid_stage}"
            )
        for stage_name in STAGE_ORDER[:STAGE_ORDER.index(resume_from_stage)]:
            payload = _load_stage_record(artifact_dir, stage_name)
            if payload is None or payload.get("status") != "completed":
                raise ValueError(
                    f"Cannot resume from {resume_from_stage}: stage_{stage_name}.json is not completed"
                )
        return resume_from_stage
    return first_invalid_stage


def _earlier_stage(current_stage: str | None, candidate_stage: str) -> str:
    if current_stage is None:
        return candidate_stage
    return candidate_stage if STAGE_ORDER.index(candidate_stage) < STAGE_ORDER.index(current_stage) else current_stage


def _artifact_npz_path(artifact_dir: Path, stage_record: dict[str, Any]) -> Path:
    outputs = stage_record.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("stage_live_run outputs must be an object")
    artifact_npz = outputs.get("artifact_npz")
    if not isinstance(artifact_npz, str):
        raise ValueError("stage_live_run outputs must include artifact_npz")
    path = Path(artifact_npz)
    _require_artifacts("summary_reports", {"artifact_npz": path})
    return path


def _load_existing_manifest(artifact_dir: Path) -> dict[str, Any] | None:
    path = artifact_dir / "run_manifest.json"
    if not path.is_file():
        return None
    payload = _load_json_dict(path)
    schema_version = payload.get("schema_version")
    if schema_version != PIPELINE_SCHEMA_VERSION:
        raise ValueError(
            f"run_manifest.json schema_version {schema_version!r} is incompatible with {PIPELINE_SCHEMA_VERSION}; use a fresh artifact directory"
        )
    return payload


def _validate_resume_policy(context: PipelineContext, manifest: dict[str, Any] | None) -> None:
    policy = _pipeline_policy(context)
    if manifest is not None:
        manifest_policy = {
            "seed": manifest.get("seed"),
            "steps": manifest.get("steps"),
            "N": manifest.get("N"),
            "dt_ms": manifest.get("dt_ms"),
            "duration_ms": manifest.get("duration_ms"),
            "export_proof": manifest.get("export_proof"),
        }
        for key, value in manifest_policy.items():
            if value != policy[key]:
                raise ValueError(f"Resume policy mismatch for {key}; use a fresh artifact directory")

    live_stage = _load_stage_record(context.artifact_dir, "live_run")
    if live_stage is None:
        return
    inputs = live_stage.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("stage_live_run.json inputs must be an object")
    recorded_policy = inputs.get("policy")
    if not isinstance(recorded_policy, dict):
        raise ValueError("stage_live_run.json missing policy snapshot")
    for key, value in policy.items():
        if recorded_policy.get(key) != value:
            raise ValueError(f"Resume policy mismatch for {key}; use a fresh artifact directory")


def _require_array(value: np.ndarray | None, field_name: str) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise ValueError(f"PipelineContext.{field_name} must be loaded before this stage")
    return value


def _require_report(value: dict[str, Any] | None, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"PipelineContext.{field_name} must be available before writing outputs")
    return value


def _load_live_run_artifacts(context: PipelineContext) -> PipelineContext:
    artifact_dir = context.artifact_dir
    stage_record = _load_stage_record(artifact_dir, "live_run")
    if stage_record is None:
        raise FileNotFoundError("stage_live_run.json not found")
    artifact_npz = _artifact_npz_path(artifact_dir, stage_record)
    with np.load(artifact_npz) as data:
        context.artifact_npz_path = artifact_npz
        context.spike_steps = np.asarray(data["spike_steps"], dtype=np.int64)
        context.sigma_trace = np.asarray(data["sigma_trace"], dtype=np.float64)
        context.rate_trace_hz = np.asarray(data["rate_trace_hz"], dtype=np.float64)
        context.coherence_trace = np.asarray(data["coherence_trace"], dtype=np.float64)
        context.spike_neurons = np.asarray(data["spike_neurons"], dtype=np.int64)
        context.steps = int(np.asarray(data["steps"]).item())
        context.n_neurons = int(np.asarray(data["N"]).item())
    return context


@contextmanager
def _artifact_dir_lock(artifact_dir: Path) -> Iterator[None]:
    lock_path = artifact_dir / ".lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Artifact directory is locked: {lock_path}") from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "started_at": _utc_now_iso()}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()


def _emit_stage_progress(
    context: PipelineContext,
    *,
    completed: set[str],
    skipped: set[str],
    running: str | None,
    failed: str | None = None,
) -> None:
    if context.progress_stream is None:
        return
    tokens: list[str] = []
    for stage_name in STAGE_ORDER:
        if stage_name == failed:
            state = "FAIL"
        elif stage_name == running:
            state = "RUN"
        elif stage_name in skipped:
            state = "SKIP"
        elif stage_name in completed:
            state = "DONE"
        else:
            state = "PEND"
        tokens.append(f"[{state}] {stage_name}")
    print(" -> ".join(tokens), file=context.progress_stream)


def stage_live_run(context: PipelineContext) -> PipelineContext:
    metrics, artifact_npz = run_emergence_to_disk(
        N=context.config.network.size,
        dt_ms=context.config.simulation.dt_ms,
        duration_ms=context.config.simulation.duration_ms,
        seed=context.seed,
        external_current_pA=context.config.simulation.external_current_pA,
        output_dir=context.artifact_dir,
    )
    context.artifact_npz_path = Path(artifact_npz)
    context.emergence_metrics = metrics
    return context


def stage_summary_reports(context: PipelineContext) -> PipelineContext:
    spike_steps = _require_array(context.spike_steps, "spike_steps")
    sigma_trace = _require_array(context.sigma_trace, "sigma_trace")
    rate_trace_hz = _require_array(context.rate_trace_hz, "rate_trace_hz")
    coherence_trace = _require_array(context.coherence_trace, "coherence_trace")
    spike_neurons = _require_array(context.spike_neurons, "spike_neurons")
    steps = context.steps
    n_neurons = int(cast(int, context.n_neurons))

    summary_metrics: dict[str, float | int] = {
        "spike_events": int(spike_steps.size),
        "rate_mean_hz": float(np.mean(rate_trace_hz)),
        "rate_peak_hz": float(np.max(rate_trace_hz)),
        "rate_variance": float(np.var(rate_trace_hz)),
        "sigma_mean": float(np.mean(sigma_trace)),
        "sigma_final": float(sigma_trace[-1]) if sigma_trace.size else 0.0,
        "sigma_variance": float(np.var(sigma_trace)),
        "seed": context.seed,
        "N": int(context.config.network.size),
        "steps": steps,
        "duration_ms": float(context.config.simulation.duration_ms),
        "dt_ms": float(context.config.simulation.dt_ms),
        "external_current_pA": float(context.config.simulation.external_current_pA),
    }

    spike_steps_per_step = np.bincount(spike_steps, minlength=steps) if steps > 0 else np.zeros(0, dtype=np.int64)
    active_steps = int(np.count_nonzero(spike_steps_per_step)) if steps > 0 else 0
    nonzero_rate_steps = int(np.count_nonzero(rate_trace_hz > 0.0))
    sigma_band = np.abs(sigma_trace - 1.0) <= 0.2
    sigma_distance = np.abs(sigma_trace - 1.0)

    criticality_report: dict[str, float | int | str] = {
        "schema_version": "1.0.0",
        "seed": context.seed,
        "N": int(context.config.network.size),
        "dt_ms": float(context.config.simulation.dt_ms),
        "duration_ms": float(context.config.simulation.duration_ms),
        "steps": steps,
        "sigma_mean": float(np.mean(sigma_trace)),
        "sigma_final": float(sigma_trace[-1]) if sigma_trace.size else 0.0,
        "sigma_variance": float(np.var(sigma_trace)),
        "rate_mean_hz": float(np.mean(rate_trace_hz)),
        "rate_peak_hz": float(np.max(rate_trace_hz)),
        "spike_events": int(spike_steps.size),
        "sigma_distance_from_1": float(np.mean(sigma_distance)) if sigma_distance.size else 0.0,
        "sigma_within_band_fraction": float(np.mean(sigma_band)) if sigma_band.size else 0.0,
        "active_steps_fraction": float(active_steps / steps) if steps > 0 else 0.0,
        "nonzero_rate_steps_fraction": float(nonzero_rate_steps / steps) if steps > 0 else 0.0,
        "rate_cv": float(np.std(rate_trace_hz) / np.mean(rate_trace_hz)) if np.mean(rate_trace_hz) > 0 else 0.0,
        "burstiness_proxy": float(np.var(spike_steps_per_step) / np.mean(spike_steps_per_step))
        if np.mean(spike_steps_per_step) > 0
        else 0.0,
    }

    phase_space_report = _build_phase_space_report(
        seed=context.seed,
        n_neurons=int(context.config.network.size),
        dt_ms=float(context.config.simulation.dt_ms),
        duration_ms=float(context.config.simulation.duration_ms),
        steps=steps,
        rate_trace_hz=rate_trace_hz,
        sigma_trace=sigma_trace,
        coherence_trace=coherence_trace,
    )
    phase_space_rate_sigma = build_phase_trajectory_image(rate_trace_hz, sigma_trace)
    phase_space_rate_coherence = build_phase_trajectory_image(rate_trace_hz, coherence_trace)
    phase_space_activity_map, _ = build_activity_map(rate_trace_hz, sigma_trace)
    raster_image = _build_raster_image(spike_steps, spike_neurons, steps, n_neurons)
    rate_image = _build_rate_image(rate_trace_hz)
    emergence_image = _build_emergence_image(raster_image, rate_image)

    context.summary_metrics = summary_metrics
    context.criticality_report = criticality_report
    context.phase_space_report = phase_space_report
    context.population_rate_trace = rate_trace_hz
    context.phase_space_rate_sigma_image = phase_space_rate_sigma
    context.phase_space_rate_coherence_image = phase_space_rate_coherence
    context.phase_space_activity_map_image = phase_space_activity_map
    context.raster_image = raster_image
    context.population_rate_image = rate_image
    context.emergence_image = emergence_image
    return context


def stage_avalanche_and_fit(context: PipelineContext) -> PipelineContext:
    steps = context.steps
    spike_steps = _require_array(context.spike_steps, "spike_steps")
    spike_steps_per_step = np.bincount(spike_steps, minlength=steps) if steps > 0 else np.zeros(0, dtype=np.int64)
    avalanche_report = _build_avalanche_report(
        seed=context.seed,
        n_neurons=int(context.config.network.size),
        dt_ms=float(context.config.simulation.dt_ms),
        duration_ms=float(context.config.simulation.duration_ms),
        steps=steps,
        spike_steps_per_step=spike_steps_per_step,
        bin_width_steps=1,
    )
    context.avalanche_report = avalanche_report
    context.avalanche_fit_report = _fit_power_law(cast(list[int], avalanche_report["sizes"]), seed=context.seed)
    return context


def stage_robustness_envelope(context: PipelineContext) -> PipelineContext:
    robustness_report, envelope_report = _build_repro_reports(context.config)
    context.robustness_report = robustness_report
    context.envelope_report = envelope_report
    return context


def stage_manifest(
    context: PipelineContext,
    *,
    completed_stages: list[str],
    failed_stage: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    artifacts: dict[str, str] = {}
    artifact_names = [
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
        "raster_plot.png",
        "population_rate_plot.png",
    ]
    for artifact_name in artifact_names:
        path = context.artifact_dir / artifact_name
        if path.is_file():
            artifacts[artifact_name] = _sha256_file(path)

    if context.export_proof:
        proof_path = context.proof_report_path
        artifacts["proof_report.json"] = _sha256_file(proof_path) if proof_path.is_file() else "0" * 64

    manifest: dict[str, Any] = {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "cmd": command_for_export_proof(context.export_proof),
        "bundle_contract": bundle_contract_for_export_proof(context.export_proof),
        "export_proof": bool(context.export_proof),
        "seed": context.seed,
        "steps": context.steps,
        "N": int(context.config.network.size),
        "dt_ms": float(context.config.simulation.dt_ms),
        "duration_ms": float(context.config.simulation.duration_ms),
        "completed_stages": completed_stages,
        "failed_stage": failed_stage,
        "failure_reason": failure_reason,
        "artifacts": artifacts,
    }
    manifest["artifacts"]["run_manifest.json"] = manifest_self_hash(manifest)
    return manifest


def stage_proof_report(
    context: PipelineContext,
    *,
    refresh_manifest: Callable[[], Path],
) -> PipelineContext:
    if not context.export_proof:
        context.proof_report = None
        return context

    from bnsyn.proof.evaluate import emit_proof_report, evaluate_all_gates

    provisional_report = evaluate_all_gates(context.artifact_dir)
    emit_proof_report(provisional_report, context.artifact_dir)
    refresh_manifest()
    final_report = evaluate_all_gates(context.artifact_dir)
    final_path = emit_proof_report(final_report, context.artifact_dir)
    refresh_manifest()

    consistency_report = evaluate_all_gates(context.artifact_dir)
    report = final_report
    report_path = final_path
    if consistency_report != final_report:
        report = consistency_report
        report_path = emit_proof_report(consistency_report, context.artifact_dir)
        refresh_manifest()

    context.proof_report = report
    context.proof_report_path = report_path
    return context


def stage_product_surface(
    context: PipelineContext,
) -> PipelineContext:
    if not context.generate_product_report:
        return context
    product_paths = write_product_report_bundle(
        artifact_dir=context.artifact_dir,
        profile="canonical",
        seed=context.seed,
        package_version=context.product_package_version,
    )
    context.product_summary_path = product_paths["product_summary"]
    context.index_html_path = product_paths["index_html"]
    return context

def run_canonical_live_bundle(
    config_path: str | Path,
    artifact_dir: str | Path = "artifacts/canonical_run",
    export_proof: bool = False,
    generate_product_report: bool = False,
    product_package_version: str = "unknown",
    resume_from_stage: str | None = None,
    progress_stream: TextIO | None = None,
) -> dict[str, Any]:
    """Execute canonical profile with resumable stage-oriented coordination."""
    context = PipelineContext(
        config=load_config(config_path),
        artifact_dir=Path(artifact_dir),
        export_proof=export_proof,
        generate_product_report=generate_product_report,
        product_package_version=product_package_version,
        resume_from_stage=resume_from_stage,
        progress_stream=progress_stream,
    )
    context.artifact_dir.mkdir(parents=True, exist_ok=True)

    def _write_manifest_snapshot(*, failed_stage: str | None = None, failure_reason: str | None = None) -> Path:
        manifest_payload = stage_manifest(
            context,
            completed_stages=_completed_stage_names(context.artifact_dir),
            failed_stage=failed_stage,
            failure_reason=failure_reason,
        )
        _write_json(context.run_manifest_path, manifest_payload)
        return context.run_manifest_path

    def _run_stage(
        stage_name: str,
        *,
        inputs: dict[str, Any],
        required_artifacts: dict[str, Path],
        compute: Callable[[], PipelineContext],
        write_outputs: Callable[[PipelineContext], dict[str, Any]] | None = None,
    ) -> None:
        started_at = _utc_now_iso()
        skipped_before = set(_completed_stage_names(context.artifact_dir))
        _emit_stage_progress(context, completed=set(), skipped=skipped_before, running=stage_name)
        try:
            _require_artifacts(stage_name, required_artifacts)
            compute()
            outputs = write_outputs(context) if write_outputs is not None else {}
            finished_at = _utc_now_iso()
            _write_stage_record(
                context.artifact_dir,
                stage_name=stage_name,
                status="completed",
                started_at=started_at,
                finished_at=finished_at,
                inputs=inputs,
                outputs=outputs,
                failure_reason=None,
            )
        except Exception as exc:
            finished_at = _utc_now_iso()
            _emit_stage_progress(
                context,
                completed=set(_completed_stage_names(context.artifact_dir)),
                skipped=set(),
                running=None,
                failed=stage_name,
            )
            _write_stage_record(
                context.artifact_dir,
                stage_name=stage_name,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                inputs=inputs,
                outputs={},
                failure_reason=f"{exc.__class__.__name__}: {exc}",
            )
            _write_manifest_snapshot(failed_stage=stage_name, failure_reason=f"{exc.__class__.__name__}: {exc}")
            raise

    with _artifact_dir_lock(context.artifact_dir):
        existing_manifest = _load_existing_manifest(context.artifact_dir)
        if existing_manifest is not None and existing_manifest.get("export_proof") is not export_proof:
            raise ValueError("Existing run_manifest.json contract is immutable; use a fresh artifact directory for a different --export-proof mode")
        _validate_resume_policy(context, existing_manifest)

        resume_stage = _resolve_resume_stage(context.artifact_dir, resume_from_stage)
        if context.export_proof and not context.proof_report_path.is_file():
            resume_stage = _earlier_stage(resume_stage, "proof_report")
        if context.generate_product_report and (
            not context.product_summary_path.is_file() or not context.index_html_path.is_file()
        ):
            resume_stage = _earlier_stage(resume_stage, "product_surface")
        start_index = STAGE_ORDER.index(resume_stage) if resume_stage is not None else len(STAGE_ORDER)
        skipped = set(STAGE_ORDER[:start_index])
        _emit_stage_progress(context, completed=set(), skipped=skipped, running=resume_stage)

        if start_index <= STAGE_ORDER.index("live_run"):
            _run_stage(
                "live_run",
                inputs={"config_path": str(config_path), "artifact_dir": context.artifact_dir.as_posix(), "policy": _pipeline_policy(context)},
                required_artifacts={},
                compute=lambda: stage_live_run(context),
                write_outputs=lambda ctx: {"artifact_npz": cast(Path, ctx.artifact_npz_path).as_posix()},
            )
        _load_live_run_artifacts(context)

        if start_index <= STAGE_ORDER.index("summary_reports"):
            _run_stage(
                "summary_reports",
                inputs={"artifact_npz": cast(Path, context.artifact_npz_path).as_posix(), "policy": _pipeline_policy(context)},
                required_artifacts={"artifact_npz": cast(Path, context.artifact_npz_path)},
                compute=lambda: stage_summary_reports(context),
                write_outputs=lambda ctx: _write_summary_reports_outputs(context, ctx),
            )
        else:
            context.summary_metrics = json.loads((context.artifact_dir / "summary_metrics.json").read_text(encoding="utf-8"))
            context.criticality_report = json.loads((context.artifact_dir / "criticality_report.json").read_text(encoding="utf-8"))
            context.phase_space_report = json.loads((context.artifact_dir / "phase_space_report.json").read_text(encoding="utf-8"))

        if start_index <= STAGE_ORDER.index("avalanche_and_fit"):
            _run_stage(
                "avalanche_and_fit",
                inputs={"artifact_npz": cast(Path, context.artifact_npz_path).as_posix(), "policy": _pipeline_policy(context)},
                required_artifacts={"artifact_npz": cast(Path, context.artifact_npz_path)},
                compute=lambda: stage_avalanche_and_fit(context),
                write_outputs=lambda ctx: _write_avalanche_outputs(context, ctx),
            )
        else:
            context.avalanche_report = json.loads((context.artifact_dir / "avalanche_report.json").read_text(encoding="utf-8"))
            context.avalanche_fit_report = json.loads((context.artifact_dir / "avalanche_fit_report.json").read_text(encoding="utf-8"))

        if start_index <= STAGE_ORDER.index("robustness_envelope"):
            _run_stage(
                "robustness_envelope",
                inputs={"canonical_repro_seeds": list(CANONICAL_REPRO_SEEDS), "policy": _pipeline_policy(context)},
                required_artifacts={"artifact_npz": cast(Path, context.artifact_npz_path)},
                compute=lambda: stage_robustness_envelope(context),
                write_outputs=lambda ctx: _write_robustness_outputs(context, ctx),
            )
        else:
            context.robustness_report = json.loads((context.artifact_dir / "robustness_report.json").read_text(encoding="utf-8"))
            context.envelope_report = json.loads((context.artifact_dir / "envelope_report.json").read_text(encoding="utf-8"))

        if start_index <= STAGE_ORDER.index("manifest"):
            _run_stage(
                "manifest",
                inputs={"export_proof": context.export_proof, "policy": _pipeline_policy(context)},
                required_artifacts={
                    "summary_metrics.json": context.artifact_dir / "summary_metrics.json",
                    "criticality_report.json": context.artifact_dir / "criticality_report.json",
                    "avalanche_report.json": context.artifact_dir / "avalanche_report.json",
                    "avalanche_fit_report.json": context.artifact_dir / "avalanche_fit_report.json",
                    "robustness_report.json": context.artifact_dir / "robustness_report.json",
                    "envelope_report.json": context.artifact_dir / "envelope_report.json",
                    "phase_space_report.json": context.artifact_dir / "phase_space_report.json",
                    "emergence_plot.png": context.artifact_dir / "emergence_plot.png",
                },
                compute=lambda: context,
                write_outputs=lambda _ctx: {"run_manifest_path": _write_manifest_snapshot().as_posix()},
            )

        if start_index <= STAGE_ORDER.index("proof_report"):
            _run_stage(
                "proof_report",
                inputs={"export_proof": context.export_proof, "policy": _pipeline_policy(context)},
                required_artifacts={"run_manifest.json": context.run_manifest_path},
                compute=lambda: stage_proof_report(context, refresh_manifest=_write_manifest_snapshot),
                write_outputs=lambda _ctx: {
                    **({"proof_report_path": context.proof_report_path.as_posix()} if context.proof_report_path.is_file() else {}),
                    "run_manifest_path": _write_manifest_snapshot().as_posix(),
                },
            )
        elif context.proof_report_path.is_file():
            context.proof_report = json.loads(context.proof_report_path.read_text(encoding="utf-8"))

        if start_index <= STAGE_ORDER.index("product_surface"):
            _run_stage(
                "product_surface",
                inputs={"generate_product_report": context.generate_product_report, "policy": _pipeline_policy(context)},
                required_artifacts={
                    **({"proof_report.json": context.proof_report_path} if context.generate_product_report else {}),
                    "run_manifest.json": context.run_manifest_path,
                },
                compute=lambda: stage_product_surface(context),
                write_outputs=lambda _ctx: {
                    **({"product_summary_path": context.product_summary_path.as_posix()} if context.product_summary_path.is_file() else {}),
                    **({"index_html_path": context.index_html_path.as_posix()} if context.index_html_path.is_file() else {}),
                    "run_manifest_path": _write_manifest_snapshot().as_posix(),
                },
            )

        _write_manifest_snapshot()
        _emit_stage_progress(context, completed=set(_completed_stage_names(context.artifact_dir)), skipped=set(), running=None)

    return {
        "artifact_dir": context.artifact_dir.as_posix(),
        "artifact_npz": context.artifact_npz_path.as_posix() if context.artifact_npz_path is not None else None,
        "run_manifest_path": context.run_manifest_path.as_posix(),
        "summary_metrics": context.summary_metrics,
        "summary_metrics_path": (context.artifact_dir / "summary_metrics.json").as_posix(),
        "criticality_report": context.criticality_report,
        "criticality_report_path": (context.artifact_dir / "criticality_report.json").as_posix(),
        "avalanche_report": context.avalanche_report,
        "avalanche_report_path": (context.artifact_dir / "avalanche_report.json").as_posix(),
        "avalanche_fit_report": context.avalanche_fit_report,
        "avalanche_fit_report_path": (context.artifact_dir / "avalanche_fit_report.json").as_posix(),
        "robustness_report": context.robustness_report,
        "robustness_report_path": (context.artifact_dir / "robustness_report.json").as_posix(),
        "envelope_report": context.envelope_report,
        "envelope_report_path": (context.artifact_dir / "envelope_report.json").as_posix(),
        "phase_space_report": context.phase_space_report,
        "phase_space_report_path": (context.artifact_dir / "phase_space_report.json").as_posix(),
        "population_rate_trace_path": (context.artifact_dir / "population_rate_trace.npy").as_posix(),
        "sigma_trace_path": (context.artifact_dir / "sigma_trace.npy").as_posix(),
        "coherence_trace_path": (context.artifact_dir / "coherence_trace.npy").as_posix(),
        "phase_space_rate_sigma_path": (context.artifact_dir / "phase_space_rate_sigma.png").as_posix(),
        "phase_space_rate_coherence_path": (context.artifact_dir / "phase_space_rate_coherence.png").as_posix(),
        "phase_space_activity_map_path": (context.artifact_dir / "phase_space_activity_map.png").as_posix(),
        "emergence_plot_path": (context.artifact_dir / "emergence_plot.png").as_posix(),
        "raster_plot_path": (context.artifact_dir / "raster_plot.png").as_posix(),
        "population_rate_plot_path": (context.artifact_dir / "population_rate_plot.png").as_posix(),
        "emergence_metrics": context.emergence_metrics,
        "proof_report": context.proof_report,
        "proof_report_path": context.proof_report_path.as_posix() if context.proof_report_path.is_file() else None,
        "product_summary_path": context.product_summary_path.as_posix() if context.product_summary_path.is_file() else None,
        "index_html_path": context.index_html_path.as_posix() if context.index_html_path.is_file() else None,
        "completed_stages": _completed_stage_names(context.artifact_dir),
    }
