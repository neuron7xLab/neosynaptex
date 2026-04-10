"""DCVP top-level orchestrator.

`run_dcvp(cfg)` is the only public entry point. It:

  1. Spawns two isolated processes per (seed, perturbation) — one per
     side — via `multiprocessing.get_context("spawn")`. Both workers
     receive the same perturbation spec but independent RNG seeds and
     pinned BLAS threads.
  2. Each worker writes to its own append-only γ-channel file.
  3. The parent reads both channels, verifies checksums, and runs the
     causality battery + negative controls.
  4. Aggregates verdict + reproducibility hash.

The parent process NEVER sends feedback to workers — spec §I, "No
feedback: B never influences A". Communication is strictly append-only.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import tempfile
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

import numpy as np

from formal.dcvp.alignment import alignment_sensitivity, dtw_align
from formal.dcvp.causality import (
    baseline_drift,
    cascade_lag,
    effect_size,
    granger_robust,
    jitter_survival,
    stationarity,
    te_null,
)
from formal.dcvp.channel import GammaChannel
from formal.dcvp.controls import run_all_controls
from formal.dcvp.protocol import (
    CausalityRow,
    DCVPConfig,
    DCVPReport,
    PerturbationSpec,
)
from formal.dcvp.verdict import (
    aggregate_verdict,
    code_hash,
    data_hash,
    reproducibility_hash,
    score_row,
)
from formal.dcvp.worker import worker_main

__all__ = ["run_dcvp"]


def _spawn_pair(
    ctx: mp.context.BaseContext,
    pair_name: str,
    seed: int,
    n_ticks: int,
    perturbation: PerturbationSpec,
    channel_a: Path,
    channel_b: Path,
    blas_threads: int,
) -> None:
    payload = asdict(perturbation)
    procs = []
    for side, channel in (("A", channel_a), ("B", channel_b)):
        # Each side gets a DIFFERENT seed derived from the nominal seed.
        # Spec §I: "independent RNG + entropy sources".
        side_seed = seed if side == "A" else seed + 1_000_003
        p = ctx.Process(
            target=worker_main,
            args=(
                side,
                pair_name,
                side_seed,
                n_ticks,
                payload,
                str(channel),
                blas_threads,
            ),
            name=f"dcvp-{side}-{seed}",
        )
        procs.append(p)
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        if p.exitcode != 0:
            raise RuntimeError(f"DCVP worker {p.name} exited with {p.exitcode}")


def _read_channel(path: Path) -> np.ndarray:
    ch = GammaChannel(path)
    if not ch.verify():
        raise RuntimeError(f"channel {path} failed checksum verification")
    samples = ch.read()
    return np.array([s.gamma for s in samples], dtype=np.float64)


def _iter_configs(cfg: DCVPConfig) -> Iterator[tuple[int, PerturbationSpec]]:
    for seed in cfg.seeds:
        for p in cfg.perturbations:
            yield seed, p


def run_dcvp(cfg: DCVPConfig, workdir: Path | None = None) -> DCVPReport:
    """Run the full DCVP v2.1 protocol and return a reproducible report."""
    ctx = mp.get_context("spawn")
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="dcvp_"))
    tmp.mkdir(parents=True, exist_ok=True)

    # Pin BLAS threads in the parent process too, so any work we do here
    # is as deterministic as the workers.
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[key] = str(cfg.blas_threads)

    gamma_a: dict[int, tuple[float, ...]] = {}
    gamma_b: dict[int, tuple[float, ...]] = {}
    aligned: dict[int, tuple[tuple[float, ...], tuple[float, ...]]] = {}
    rows: list[CausalityRow] = []
    cascade_profile: list[tuple[int, float]] = []

    rng_parent = np.random.default_rng(0xC0DE_A11)

    # For each seed we first run the CONTROL (unperturbed) to get the
    # reference γ_A / γ_B streams used by negative controls.
    control_streams: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    from formal.dcvp.protocol import PerturbationSpec as _PS

    baseline = _PS(kind="noise", sigma=0.0)
    for seed in cfg.seeds:
        ch_a = tmp / f"ctrl_a_seed{seed}.ndjson"
        ch_b = tmp / f"ctrl_b_seed{seed}.ndjson"
        _spawn_pair(ctx, cfg.pair.name, seed, cfg.n_ticks, baseline, ch_a, ch_b, cfg.blas_threads)
        a = _read_channel(ch_a)
        b = _read_channel(ch_b)
        control_streams[seed] = (a, b)
        gamma_a[seed] = tuple(a.tolist())
        gamma_b[seed] = tuple(b.tolist())

    # Perturbation sweep.
    for seed, perturbation in _iter_configs(cfg):
        ch_a = tmp / f"pert_a_seed{seed}_{perturbation.kind}_{perturbation.sigma:.2f}.ndjson"
        ch_b = tmp / f"pert_b_seed{seed}_{perturbation.kind}_{perturbation.sigma:.2f}.ndjson"
        _spawn_pair(
            ctx,
            cfg.pair.name,
            seed,
            cfg.n_ticks,
            perturbation,
            ch_a,
            ch_b,
            cfg.blas_threads,
        )
        a = _read_channel(ch_a)
        b = _read_channel(ch_b)

        stat_a = stationarity(a)
        stat_b = stationarity(b)
        if stat_a.nan_fraction > 0.05 or stat_b.nan_fraction > 0.05:
            # Reject per spec §IV; still record a failing row so the user
            # can see why.
            rows.append(
                CausalityRow(
                    seed=seed,
                    perturbation=perturbation,
                    granger_p=1.0,
                    granger_lag=0,
                    te_z=0.0,
                    te_value=0.0,
                    cascade_lag=0,
                    cascade_lag_cv=float("inf"),
                    jitter_survival=0.0,
                    alignment_sensitivity=1.0,
                    effect_size=0.0,
                    baseline_drift=float("inf"),
                    passes=False,
                    fail_reasons=("nan_fraction>5%",),
                )
            )
            continue

        a_al, b_al, _ = dtw_align(a, b)
        aligned[seed] = (tuple(a_al.tolist()), tuple(b_al.tolist()))

        granger_p, granger_lag = granger_robust(a_al, b_al, max_lag=cfg.granger_max_lag, seed=seed)
        te_obs, te_mu, te_sigma = te_null(
            a_al, b_al, n_surrogates=cfg.te_null_n, rng=np.random.default_rng(seed)
        )
        mean_lag, lag_cv = cascade_lag(a_al, b_al, max_lag=min(12, cfg.granger_max_lag))
        surv = jitter_survival(
            a_al,
            b_al,
            max_shift=cfg.jitter_max_ticks,
            dropout=cfg.jitter_dropout,
            rng=np.random.default_rng(seed + 1),
            granger_lag=max(1, granger_lag),
        )
        sens = alignment_sensitivity(
            a,
            b,
            max_shift=cfg.jitter_max_ticks,
            dropout=cfg.jitter_dropout,
            rng=np.random.default_rng(seed + 2),
        )
        eff = effect_size(a_al, b_al)
        drift = max(baseline_drift(a_al), baseline_drift(b_al))

        row = score_row(
            seed=seed,
            perturbation=perturbation,
            granger_p=granger_p,
            granger_lag=granger_lag,
            te_obs=te_obs,
            te_null_mean=te_mu,
            te_null_std=te_sigma,
            cascade_mean_lag=mean_lag,
            cascade_cv=lag_cv,
            jitter_surv=surv,
            alignment_sens=sens,
            effect=eff,
            drift=drift,
        )
        rows.append(row)
        cascade_profile.append((mean_lag, eff))

    # Negative controls use the UNPERTURBED streams, paired across runs.
    seeds_sorted = sorted(control_streams)
    if len(seeds_sorted) >= 2:
        a1, b1 = control_streams[seeds_sorted[0]]
        a2, b2 = control_streams[seeds_sorted[1]]
    else:
        a1, b1 = control_streams[seeds_sorted[0]]
        a2, b2 = a1.copy(), b1.copy()
    controls = run_all_controls(
        a1,
        b1,
        a2,
        b2,
        rng=rng_parent,
        n_ticks=cfg.n_ticks,
        granger_max_lag=cfg.granger_max_lag,
        te_null_n=min(cfg.te_null_n, 200),
    )
    controls_flagged = {k: v.signaled_causality for k, v in controls.items()}

    verdict = aggregate_verdict(tuple(rows), controls_flagged)

    dcvp_dir = Path(__file__).parent
    code_hex = code_hash(
        [
            dcvp_dir / "protocol.py",
            dcvp_dir / "channel.py",
            dcvp_dir / "perturbation.py",
            dcvp_dir / "alignment.py",
            dcvp_dir / "causality.py",
            dcvp_dir / "controls.py",
            dcvp_dir / "verdict.py",
            dcvp_dir / "runner.py",
            dcvp_dir / "worker.py",
            dcvp_dir / "pairs.py",
        ]
    )
    data_hex = data_hash(gamma_a, gamma_b)
    repro_hex = reproducibility_hash(cfg, code_hex, data_hex)

    return DCVPReport(
        config=cfg,
        gamma_a=gamma_a,
        gamma_b=gamma_b,
        aligned=aligned,
        causality_matrix=tuple(rows),
        cascade_profile=tuple(cascade_profile),
        controls=controls_flagged,
        verdict=verdict,
        reproducibility_hash=repro_hex,
        code_hash=code_hex,
        data_hash=data_hex,
    )
