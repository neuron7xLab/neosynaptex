"""Isolated worker process entry point.

Launched by `runner.py` via multiprocessing.get_context("spawn"), which
gives us a fresh Python interpreter. We enforce BLAS thread pinning via
environment variables set **before** importing numpy/scipy; by the time
this module is imported those envs are already in place because the
runner passes them through `Process(env=...)` equivalent (we re-set them
here as a belt-and-braces safeguard in case the spawned child inherited
something unexpected).

The worker:
  1. Builds a γ(t) array using the requested pair factory.
  2. Appends every sample to an append-only channel (checksum chain).
  3. Exits cleanly — it NEVER reads from the other process. No feedback.
"""

from __future__ import annotations

import os
from pathlib import Path


def _pin_blas(threads: int) -> None:
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[key] = str(threads)


def worker_main(
    side: str,
    pair_name: str,
    seed: int,
    n_ticks: int,
    perturbation_payload: dict[str, object],
    channel_path: str,
    blas_threads: int,
) -> None:
    """Entry point for an isolated γ-emitting subprocess."""
    _pin_blas(blas_threads)

    # Deferred imports: keep them *after* BLAS pinning.
    from formal.dcvp.channel import GammaChannel
    from formal.dcvp.pairs import get_pair
    from formal.dcvp.protocol import PerturbationSpec

    # Best-effort registration of real-substrate pairs. Mock pairs are
    # always registered at import time in formal.dcvp.pairs; real pairs
    # pull in heavier substrate modules that may not be importable in
    # every environment (e.g. minimal CI), so failures are non-fatal.
    try:
        from formal.dcvp.real_pairs import register_real_pairs

        register_real_pairs()
    except Exception:  # pragma: no cover — optional dependency path
        pass

    perturbation = PerturbationSpec(**perturbation_payload)  # type: ignore[arg-type]
    pair = get_pair(pair_name)
    builder = pair.a_builder if side == "A" else pair.b_builder
    gamma = builder(seed, n_ticks, perturbation)

    channel = GammaChannel(Path(channel_path))
    for t, g in enumerate(gamma.tolist()):
        channel.append(t, float(g))
