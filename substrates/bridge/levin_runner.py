"""Levin → Neosynaptex bridge runner.

Canonical protocol: ``docs/protocols/levin_bridge_protocol.md``.
Per-substrate knobs: ``evidence/levin_bridge/horizon_knobs.md``.

What this module provides
-------------------------

* ``AdapterBase`` — abstract interface each substrate must implement.
* Three concrete adapter classes — ``MFNPlusAdapter``, ``KuramotoAdapter``,
  ``BNSynAdapter`` — each declares the regime knob values and the
  overcoupled/undercoupled control configs from ``horizon_knobs.md``.
  The ``execute`` method is ``NotImplementedError`` by design: wiring
  to the real substrate is a separate, substrate-owner PR per
  ``evidence/PREREG.md``.
* Post-output control transforms for ``shuffle`` and ``matched_noise``
  families (deterministic, seeded).
* Append-only CSV writer matching the schema in
  ``evidence/levin_bridge/cross_substrate_horizon_metrics.csv``.
* Plan-matrix builder: 3 substrates × 3 regimes × 5 control families = 45
  rows when the LLM substrate is scoped out (see ``horizon_knobs.md``).
* ``main`` CLI with ``--dry-run``, ``--substrate``, ``--out``.

What this module does NOT do
----------------------------

* It does not execute any substrate. The ``execute`` methods on the
  concrete adapters raise ``NotImplementedError`` until the wiring PRs
  land. ``--dry-run`` is therefore the only mode that can run end-to-end
  at this commit.
* It does not compute γ. γ estimation remains the responsibility of the
  Neosynaptex observer attached to each substrate's output (see
  ``docs/science/MECHANISMS.md §1`` and ``core/gamma.py``).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as _dt
import enum
import hashlib
import logging
import os
import pathlib
import subprocess
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

__all__ = [
    "AdapterBase",
    "BNSynAdapter",
    "ControlFamily",
    "KuramotoAdapter",
    "MFNPlusAdapter",
    "RunRow",
    "apply_post_output_control",
    "build_plan",
    "git_head_sha",
    "run_plan",
]

logger = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_CSV = _REPO_ROOT / "evidence" / "levin_bridge" / "cross_substrate_horizon_metrics.csv"
_CSV_SCHEMA: tuple[str, ...] = (
    "substrate",
    "regime",
    "control_family",
    "H_raw",
    "H_rank",
    "C",
    "gamma",
    "gamma_ci_lo",
    "gamma_ci_hi",
    "P",
    "n_samples",
    "commit_sha",
    "timestamp_utc",
)


class ControlFamily(str, enum.Enum):
    """Five control families the bridge evaluates per (substrate, regime)."""

    PRODUCTIVE = "productive"
    SHUFFLE = "shuffle"
    MATCHED_NOISE = "matched_noise"
    OVERCOUPLED_COLLAPSE = "overcoupled_collapse"
    UNDERCOUPLED_FRAGMENTATION = "undercoupled_fragmentation"


# ---------------------------------------------------------------------------
# Data record
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunRow:
    """One row of ``cross_substrate_horizon_metrics.csv``."""

    substrate: str
    regime: str
    control_family: ControlFamily
    H_raw: float
    H_rank: float
    C: float
    gamma: float
    gamma_ci_lo: float
    gamma_ci_hi: float
    P: float
    n_samples: int
    commit_sha: str
    timestamp_utc: str

    def as_csv_row(self) -> list[str]:
        """Serialise to a CSV row in canonical schema order."""

        return [
            self.substrate,
            self.regime,
            self.control_family.value,
            f"{self.H_raw:.6g}",
            f"{self.H_rank:.6g}",
            f"{self.C:.6g}",
            f"{self.gamma:.6g}",
            f"{self.gamma_ci_lo:.6g}",
            f"{self.gamma_ci_hi:.6g}",
            f"{self.P:.6g}",
            str(self.n_samples),
            self.commit_sha,
            self.timestamp_utc,
        ]


# ---------------------------------------------------------------------------
# Post-output control transforms (shuffle, matched_noise)
# ---------------------------------------------------------------------------


def apply_post_output_control(
    series: np.ndarray,
    family: ControlFamily,
    *,
    seed: int,
) -> np.ndarray:
    """Transform a substrate output time series per a control family.

    Only ``SHUFFLE`` and ``MATCHED_NOISE`` are post-output; the other
    families are applied at the config level by the adapter. Calling
    this function with ``PRODUCTIVE`` returns the input unchanged.
    Calling with ``OVERCOUPLED_COLLAPSE`` or
    ``UNDERCOUPLED_FRAGMENTATION`` raises ``ValueError`` because those
    controls require a different ``execute`` call, not a post-hoc
    transform.
    """

    if family is ControlFamily.PRODUCTIVE:
        return series
    if family in (
        ControlFamily.OVERCOUPLED_COLLAPSE,
        ControlFamily.UNDERCOUPLED_FRAGMENTATION,
    ):
        raise ValueError(
            f"{family.value} is a knob-level control, not post-output; "
            "call the adapter's overcoupled_config / undercoupled_config "
            "and re-execute."
        )
    rng = np.random.default_rng(seed)
    if family is ControlFamily.SHUFFLE:
        if series.ndim == 1:
            return rng.permutation(series)
        idx = rng.permutation(series.shape[0])
        return series[idx]
    if family is ControlFamily.MATCHED_NOISE:
        mean = float(np.mean(series))
        std = float(np.std(series))
        return rng.normal(loc=mean, scale=std, size=series.shape).astype(series.dtype)
    raise ValueError(f"unknown control family: {family}")


# ---------------------------------------------------------------------------
# Git SHA provenance
# ---------------------------------------------------------------------------


def git_head_sha(repo_root: pathlib.Path = _REPO_ROOT) -> str:
    """Return the current HEAD SHA, or ``"UNSTAMPED:<hash>"`` if git unavailable.

    Any row appended to ``cross_substrate_horizon_metrics.csv`` must carry
    a verifiable SHA. When running outside a checkout we still emit a
    pseudo-stamp so the row is not silently un-provenanced; such rows
    MUST be rejected at review.
    """

    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        fake = hashlib.sha1(str(repo_root).encode()).hexdigest()
        return f"UNSTAMPED:{fake[:12]}"


# ---------------------------------------------------------------------------
# CSV append-only writer
# ---------------------------------------------------------------------------


def append_rows(rows: Iterable[RunRow], out_path: pathlib.Path = _DEFAULT_CSV) -> int:
    """Append rows to the canonical CSV; return count written.

    Enforces the schema header on an empty or missing file. Raises
    ``ValueError`` if an existing file's header does not match the
    canonical schema (suggests schema drift — never rewrite, always
    extend via a schema bump per the evidence-directory rules).
    """

    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    needs_header = not out_path.exists() or out_path.stat().st_size == 0
    if not needs_header:
        with out_path.open("r", newline="", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
            existing_header = tuple(first_line.split(","))
            if existing_header != _CSV_SCHEMA:
                raise ValueError(
                    "schema drift: existing header "
                    f"{existing_header!r} != canonical {_CSV_SCHEMA!r}"
                )

    count = 0
    with out_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if needs_header:
            writer.writerow(_CSV_SCHEMA)
        for row in rows:
            writer.writerow(row.as_csv_row())
            count += 1
    return count


# ---------------------------------------------------------------------------
# Adapter base
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RegimeSpec:
    """Per-regime knob values + an operational label."""

    name: str
    knobs: dict[str, float]
    notes: str = ""


class AdapterBase:
    """Abstract adapter each substrate must implement.

    Concrete subclasses fill in:

    * ``name`` — short substrate identifier used in the CSV.
    * ``regimes`` — ordered tuple of three ``RegimeSpec`` (compressed /
      intermediate / expanded).
    * ``overcoupled_knobs`` — dict pushed above expanded for the
      overcoupled-collapse control.
    * ``undercoupled_knobs`` — dict pushed below compressed for the
      undercoupled-fragmentation control.
    * ``execute(knobs, seed)`` — run the real substrate and return the
      output time series or sufficient artefact for γ/C/P extraction.
    * ``compute_metrics(output)`` — return ``(H, C, γ, γ_ci, P, n)``.
    """

    name: str = ""
    regimes: tuple[RegimeSpec, RegimeSpec, RegimeSpec] = ()  # type: ignore[assignment]
    overcoupled_knobs: dict[str, float] = {}
    undercoupled_knobs: dict[str, float] = {}
    horizon_rank: dict[str, float] = {}

    def regime_by_name(self, name: str) -> RegimeSpec:
        for r in self.regimes:
            if r.name == name:
                return r
        raise KeyError(f"{self.name}: unknown regime {name!r}")

    def execute(
        self, knobs: dict[str, float], seed: int
    ) -> np.ndarray:  # pragma: no cover - abstract
        raise NotImplementedError(
            f"{self.name}: execute() not wired. See evidence/levin_bridge/"
            "horizon_knobs.md for the target substrate entrypoint; "
            "open a follow-up PR that pre-registers the adapter per "
            "evidence/PREREG.md before writing any row."
        )

    def compute_metrics(
        self, output: np.ndarray
    ) -> tuple[float, float, float, tuple[float, float], float, int]:  # pragma: no cover - abstract
        raise NotImplementedError(
            f"{self.name}: compute_metrics() not wired. γ estimation "
            "must go through core/gamma.py, not an ad-hoc estimator."
        )


# ---------------------------------------------------------------------------
# Concrete adapter declarations (execute NotImplementedError by design)
# ---------------------------------------------------------------------------


class MFNPlusAdapter(AdapterBase):
    """Mycelium-Fractal-Net (``substrates/mfn/``).

    Entrypoint: ``mycelium_fractal_net.core.engine.run_mycelium_simulation_with_history``.
    Knob: ``SimulationConfig.alpha`` ∈ [0.05, 0.25] (CFL-safe).
    P: ``SimulationResult.growth_events``.
    """

    name = "mfn_plus"
    regimes = (
        RegimeSpec("compressed", {"alpha": 0.08}, "sub-default; above ALPHA_MIN=0.05"),
        RegimeSpec("intermediate", {"alpha": 0.18}, "factory default"),
        RegimeSpec("expanded", {"alpha": 0.24}, "near CFL ceiling 0.25"),
    )
    # Overcoupled pushed just below CFL; undercoupled at ALPHA_MIN.
    overcoupled_knobs = {"alpha": 0.249}
    undercoupled_knobs = {"alpha": 0.05}
    horizon_rank = {"compressed": 1.0, "intermediate": 2.0, "expanded": 3.0}


class KuramotoAdapter(AdapterBase):
    """Kuramoto substrate — **TradePulse Δr proxy** (not a classical oscillator).

    Entrypoint: ``substrates.kuramoto.analytics.regime.src.core.tradepulse_v21.TradePulseV21Pipeline``.
    Knob tuple: ``window`` × ``ema_alpha``.
    P: ``ModelPerformance.auc`` on held-out folds; viability AUC > 0.55.

    Restate the proxy caveat in every manuscript citing this substrate
    (required by ``horizon_knobs.md``).
    """

    name = "kuramoto_tradepulse_proxy"
    regimes = (
        RegimeSpec(
            "compressed",
            {"window": 21.0, "ema_alpha": 0.05},
            "~1 month; fast α, shallow memory",
        ),
        RegimeSpec(
            "intermediate",
            {"window": 63.0, "ema_alpha": 0.15},
            "~1 quarter; balanced",
        ),
        RegimeSpec(
            "expanded",
            {"window": 252.0, "ema_alpha": 0.30},
            "annual default; slow α, deep memory",
        ),
    )
    overcoupled_knobs = {"window": 504.0, "ema_alpha": 0.45}
    undercoupled_knobs = {"window": 5.0, "ema_alpha": 0.02}
    horizon_rank = {"compressed": 1.0, "intermediate": 2.0, "expanded": 3.0}


class BNSynAdapter(AdapterBase):
    """BN-Syn (``substrates/bn_syn/``).

    Entrypoint: ``bnsyn.sim.network.Network``.
    Knob tuple: ``p_conn`` × ``delay_ms`` × ``tau_NMDA_ms``.
    P: criticality σ ∈ [0.85, 1.15] AND non-zero spike rate.
    """

    name = "bn_syn"
    regimes = (
        RegimeSpec(
            "compressed",
            {"p_conn": 0.01, "delay_ms": 0.5, "tau_NMDA_ms": 20.0},
            "sparse, shallow recurrence",
        ),
        RegimeSpec(
            "intermediate",
            {"p_conn": 0.05, "delay_ms": 1.0, "tau_NMDA_ms": 100.0},
            "repository defaults",
        ),
        RegimeSpec(
            "expanded",
            {"p_conn": 0.10, "delay_ms": 2.0, "tau_NMDA_ms": 200.0},
            "dense, extended integration",
        ),
    )
    overcoupled_knobs = {"p_conn": 0.25, "delay_ms": 4.0, "tau_NMDA_ms": 400.0}
    undercoupled_knobs = {"p_conn": 0.002, "delay_ms": 0.1, "tau_NMDA_ms": 5.0}
    horizon_rank = {"compressed": 1.0, "intermediate": 2.0, "expanded": 3.0}


# LLM multi-agent is scoped out at this iteration. See
# evidence/levin_bridge/horizon_knobs.md §4 and
# experiments/lm_substrate/README.md for the existing falsification.


ADAPTERS: tuple[type[AdapterBase], ...] = (
    MFNPlusAdapter,
    KuramotoAdapter,
    BNSynAdapter,
)


# ---------------------------------------------------------------------------
# Plan + orchestrator
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PlannedCell:
    """One intended measurement: (adapter, regime, control_family)."""

    substrate: str
    regime: str
    control_family: ControlFamily
    knobs: dict[str, float]


def build_plan(adapters: Sequence[type[AdapterBase]] = ADAPTERS) -> list[PlannedCell]:
    """Return the flat list of cells the bridge intends to fill.

    Size = len(adapters) × 3 regimes × 5 control families.
    """

    cells: list[PlannedCell] = []
    for adapter_cls in adapters:
        adapter = adapter_cls()
        for regime in adapter.regimes:
            for family in ControlFamily:
                if family is ControlFamily.OVERCOUPLED_COLLAPSE:
                    knobs = dict(adapter.overcoupled_knobs)
                elif family is ControlFamily.UNDERCOUPLED_FRAGMENTATION:
                    knobs = dict(adapter.undercoupled_knobs)
                else:
                    knobs = dict(regime.knobs)
                cells.append(
                    PlannedCell(
                        substrate=adapter.name,
                        regime=regime.name,
                        control_family=family,
                        knobs=knobs,
                    )
                )
    return cells


def run_plan(
    plan: Sequence[PlannedCell],
    *,
    dry_run: bool,
    seed: int = 0,
    commit_sha: str | None = None,
) -> list[RunRow]:
    """Execute the plan.

    In ``dry_run`` mode, emits placeholder rows with NaN metrics so the
    plan can be inspected without any substrate dependency. In
    non-dry-run mode, delegates to each adapter's ``execute`` +
    ``compute_metrics``.
    """

    commit_sha = commit_sha or git_head_sha()
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    adapters_by_name = {cls().name: cls() for cls in ADAPTERS}
    rows: list[RunRow] = []

    for cell in plan:
        adapter = adapters_by_name[cell.substrate]
        rank = adapter.horizon_rank[cell.regime]
        if dry_run:
            rows.append(
                RunRow(
                    substrate=cell.substrate,
                    regime=cell.regime,
                    control_family=cell.control_family,
                    H_raw=float("nan"),
                    H_rank=rank,
                    C=float("nan"),
                    gamma=float("nan"),
                    gamma_ci_lo=float("nan"),
                    gamma_ci_hi=float("nan"),
                    P=float("nan"),
                    n_samples=0,
                    commit_sha=f"DRYRUN:{commit_sha}",
                    timestamp_utc=timestamp,
                )
            )
            continue
        output = adapter.execute(cell.knobs, seed=seed)
        if cell.control_family in (
            ControlFamily.SHUFFLE,
            ControlFamily.MATCHED_NOISE,
        ):
            output = apply_post_output_control(output, cell.control_family, seed=seed)
        H_raw, C, gamma, (ci_lo, ci_hi), P, n = adapter.compute_metrics(output)
        rows.append(
            RunRow(
                substrate=cell.substrate,
                regime=cell.regime,
                control_family=cell.control_family,
                H_raw=H_raw,
                H_rank=rank,
                C=C,
                gamma=gamma,
                gamma_ci_lo=ci_lo,
                gamma_ci_hi=ci_hi,
                P=P,
                n_samples=n,
                commit_sha=commit_sha,
                timestamp_utc=timestamp,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="levin_runner",
        description="Levin → Neosynaptex bridge runner (see docs/protocols/levin_bridge_protocol.md).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit the plan matrix with NaN metrics; do not touch any substrate.",
    )
    p.add_argument(
        "--substrate",
        choices=[cls().name for cls in ADAPTERS],
        action="append",
        help="Restrict to one or more substrates (repeatable).",
    )
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--out",
        type=pathlib.Path,
        default=_DEFAULT_CSV,
        help="Append-only CSV path (canonical evidence).",
    )
    p.add_argument(
        "--no-write",
        action="store_true",
        help="Compute rows but skip CSV append (for inspection only).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("LEVIN_RUNNER_LOG", "INFO"))
    ns = _build_argparser().parse_args(argv)
    selected: tuple[type[AdapterBase], ...] = ADAPTERS
    if ns.substrate:
        wanted = set(ns.substrate)
        selected = tuple(cls for cls in ADAPTERS if cls().name in wanted)
    plan = build_plan(selected)
    logger.info("plan: %d cells across %d substrates", len(plan), len(selected))
    rows = run_plan(plan, dry_run=ns.dry_run, seed=ns.seed)
    if ns.no_write:
        for row in rows:
            print(",".join(row.as_csv_row()))
        return 0
    written = append_rows(rows, ns.out)
    logger.info("wrote %d rows to %s", written, ns.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


def _hash_unused_variable(_value: Any) -> None:
    """Type-checker no-op to keep ``Any`` imported for adapter hooks."""

    return None
