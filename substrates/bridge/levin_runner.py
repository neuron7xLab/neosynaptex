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
import logging
import os
import pathlib
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

__all__ = [
    "SCHEMA_V1_COLUMNS",
    "SCHEMA_V2_COLUMNS",
    "SCHEMA_VERSION",
    "AdapterBase",
    "BNSynAdapter",
    "ControlFamily",
    "KuramotoAdapter",
    "MFNPlusAdapter",
    "PStatus",
    "RunRow",
    "SchemaVersionMismatch",
    "apply_post_output_control",
    "build_plan",
    "git_head_sha",
    "migrate_v1_to_v2",
    "run_plan",
]

logger = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_CSV = _REPO_ROOT / "evidence" / "levin_bridge" / "cross_substrate_horizon_metrics.csv"

# Canonical schema version carried per-row. Bump on every structural change.
SCHEMA_VERSION: str = "v2"

# Legacy v1 — 13 columns, no schema_version, no P_status, P non-nullable.
# Retained ONLY so the writer can refuse it with a precise error and point
# callers at ``migrate_v1_to_v2``. Never writable.
SCHEMA_V1_COLUMNS: tuple[str, ...] = (
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

# Canonical v2 — 15 columns.
#
# Contract split (this PR):
#
# * Required, cross-substrate comparable: ``H_raw``, ``H_rank``, ``C``,
#   ``gamma``, ``gamma_ci_lo``, ``gamma_ci_hi``.
# * Optional, substrate-specific: ``P`` (may be empty).
#
# ``P_status`` is the explicit signal for downstream analysis. A row with
# ``P_status == "not_defined"`` is valid for regime diagnostics (H / C / γ)
# but MUST NOT feed any productivity or capability claim. ``schema_version``
# is stamped on every row so mixed-version ledgers are always detectable.
SCHEMA_V2_COLUMNS: tuple[str, ...] = (
    "schema_version",
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
    "P_status",
    "n_samples",
    "commit_sha",
    "timestamp_utc",
)

# Public alias for the currently-canonical schema. Code that writes rows
# MUST reference this name rather than v1/v2 directly, so the next bump
# lands cleanly.
_CSV_SCHEMA: tuple[str, ...] = SCHEMA_V2_COLUMNS


class SchemaVersionMismatch(ValueError):
    """Raised when an existing CSV header does not match the canonical schema.

    Never silently coerces legacy rows. Callers must either run
    ``migrate_v1_to_v2`` explicitly or write to a fresh file.
    """


class ControlFamily(str, enum.Enum):
    """Five control families the bridge evaluates per (substrate, regime)."""

    PRODUCTIVE = "productive"
    SHUFFLE = "shuffle"
    MATCHED_NOISE = "matched_noise"
    OVERCOUPLED_COLLAPSE = "overcoupled_collapse"
    UNDERCOUPLED_FRAGMENTATION = "undercoupled_fragmentation"


class PStatus(str, enum.Enum):
    """Explicit productivity-contract status per row.

    * ``DEFINED`` — ``P`` is a numeric value produced by a substrate-native,
      preregistered productivity metric. Only rows in this state may feed
      productivity or capability claims.
    * ``NOT_DEFINED`` — no preregistered P contract exists for this
      substrate. ``P`` MUST be empty in the CSV. The row is still valid for
      regime diagnostics (H / C / γ) and for every falsification control.
    * ``PREREGISTERED_PENDING`` — a P contract has been proposed and
      referenced in ``evidence/levin_bridge/hypotheses.yaml`` but the
      adapter that computes it has not yet landed. ``P`` MUST be empty.
    """

    DEFINED = "defined"
    NOT_DEFINED = "not_defined"
    PREREGISTERED_PENDING = "preregistered_pending"


# ---------------------------------------------------------------------------
# Data record
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunRow:
    """One row of ``cross_substrate_horizon_metrics.csv`` (schema v2).

    Required, cross-substrate comparable — MUST be numeric:
    ``H_raw``, ``H_rank``, ``C``, ``gamma``, ``gamma_ci_lo``, ``gamma_ci_hi``.

    Optional, substrate-specific:
    ``P``. ``None`` is a legal value and is written as an empty CSV cell.
    When ``P is None`` the row's ``P_status`` MUST be ``NOT_DEFINED`` or
    ``PREREGISTERED_PENDING``. When ``P`` is a float, ``P_status`` MUST be
    ``DEFINED``. ``__post_init__`` enforces this pair-invariant.

    ``schema_version`` is stamped per-row so mixed-version ledgers are
    always detectable.
    """

    substrate: str
    regime: str
    control_family: ControlFamily
    H_raw: float
    H_rank: float
    C: float
    gamma: float
    gamma_ci_lo: float
    gamma_ci_hi: float
    P: float | None
    P_status: PStatus
    n_samples: int
    commit_sha: str
    timestamp_utc: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.P is None and self.P_status is PStatus.DEFINED:
            raise ValueError(
                "RunRow invariant: P is None but P_status is DEFINED. "
                "A defined productivity value MUST be numeric."
            )
        if self.P is not None and self.P_status is not PStatus.DEFINED:
            raise ValueError(
                "RunRow invariant: P is numeric but P_status is not DEFINED. "
                "A numeric P MUST carry P_status=DEFINED; use None for "
                "NOT_DEFINED / PREREGISTERED_PENDING."
            )

    def as_csv_row(self) -> list[str]:
        """Serialise to a CSV row in canonical v2 schema order."""

        p_cell = "" if self.P is None else f"{self.P:.6g}"
        return [
            self.schema_version,
            self.substrate,
            self.regime,
            self.control_family.value,
            f"{self.H_raw:.6g}",
            f"{self.H_rank:.6g}",
            f"{self.C:.6g}",
            f"{self.gamma:.6g}",
            f"{self.gamma_ci_lo:.6g}",
            f"{self.gamma_ci_hi:.6g}",
            p_cell,
            self.P_status.value,
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
    """Return the current HEAD SHA, or the ``UNSTAMPED:<12hex>`` sentinel.

    Thin re-export of the canonical ``tools.audit.git_sha.git_head_sha``.
    Kept in this module for backward compat with existing imports.
    Any row appended to ``cross_substrate_horizon_metrics.csv`` must
    carry a verifiable SHA; rows stamped with the sentinel MUST be
    rejected at review.
    """

    from tools.audit.git_sha import git_head_sha as _canonical

    return _canonical(repo_root)


# ---------------------------------------------------------------------------
# CSV append-only writer
# ---------------------------------------------------------------------------


def append_rows(rows: Iterable[RunRow], out_path: pathlib.Path = _DEFAULT_CSV) -> int:
    """Append rows to the canonical CSV; return count written.

    Enforces ``SCHEMA_V2_COLUMNS`` on an empty or missing file. Raises
    ``SchemaVersionMismatch`` in two distinct cases so callers know whether
    the remediation is migration or rejection:

    * existing header == ``SCHEMA_V1_COLUMNS`` — legacy ledger; point at
      ``migrate_v1_to_v2``. Never silently coerced.
    * existing header is anything else unknown — reject as corrupt. Manual
      audit required; no guesswork.
    """

    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    needs_header = not out_path.exists() or out_path.stat().st_size == 0
    if not needs_header:
        with out_path.open("r", newline="", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
            existing_header = tuple(first_line.split(","))
            if existing_header == SCHEMA_V2_COLUMNS:
                pass
            elif existing_header == SCHEMA_V1_COLUMNS:
                raise SchemaVersionMismatch(
                    "legacy v1 header detected; run "
                    "`substrates.bridge.levin_runner.migrate_v1_to_v2("
                    f"{str(out_path)!r})` explicitly before appending. "
                    "Silent reinterpretation of v1 rows is forbidden."
                )
            else:
                raise SchemaVersionMismatch(
                    f"unknown header {existing_header!r} at {out_path}; "
                    f"expected canonical {SCHEMA_V2_COLUMNS!r} "
                    "or legacy v1 for migration."
                )

    # Lazy import so this module stays importable in environments
    # without ``tools/telemetry`` on the path. Emission is best-effort:
    # if the telemetry module is unavailable or raises, the CSV write
    # still succeeds per spec §8 (silent degradation).
    try:
        from tools.telemetry.emit import emit_event as _emit_event
    except ImportError:  # pragma: no cover - optional dep path
        _emit_event = None

    count = 0
    with out_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if needs_header:
            writer.writerow(SCHEMA_V2_COLUMNS)
        for row in rows:
            writer.writerow(row.as_csv_row())
            count += 1
            if _emit_event is not None:
                _emit_event(
                    "evidence.cross_substrate_horizon_metrics.append",
                    "bridge",
                    payload={
                        "substrate": row.substrate,
                        "regime": row.regime,
                        "control_family": row.control_family.value,
                        "schema_version": row.schema_version,
                        "P_status": row.P_status.value,
                        "n_samples": row.n_samples,
                    },
                    outcome="ok",
                )
    return count


def migrate_v1_to_v2(path: pathlib.Path, *, allow_data_rows: bool = False) -> int:
    """Migrate a v1 ledger at ``path`` to v2 in place.

    Header-only files are migrated freely: the single header line is
    rewritten to ``SCHEMA_V2_COLUMNS``. No data semantics change.

    Data rows are NOT auto-mapped. Legacy v1 rows carried a mandatory ``P``
    whose substrate-native semantics were never canonical; silently
    re-interpreting those values as v2 ``P`` with ``P_status=DEFINED`` is
    exactly the fabrication this schema bump exists to prevent. If data
    rows are present, raises ``SchemaVersionMismatch`` unless the caller
    opts into ``allow_data_rows=True`` — in which case every legacy row is
    rewritten with ``schema_version="v2"``, ``P=""``, ``P_status="preregistered_pending"``
    so that the productivity semantics are explicitly marked as needing
    substrate-specific audit before they can feed any claim.

    Returns the number of non-header rows migrated (0 for a header-only
    file).
    """

    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            header = tuple(next(reader))
        except StopIteration:
            header = ()
        data = list(reader)

    if header == SCHEMA_V2_COLUMNS:
        return 0  # already v2; no-op.
    if header != SCHEMA_V1_COLUMNS:
        raise SchemaVersionMismatch(f"cannot migrate: header {header!r} is neither v1 nor v2.")
    if data and not allow_data_rows:
        raise SchemaVersionMismatch(
            f"{path} has {len(data)} legacy data row(s); v1 P semantics "
            "are not canonical and cannot be silently re-labelled. "
            "Call migrate_v1_to_v2(..., allow_data_rows=True) only after "
            "review — it will rewrite every row with "
            "P_status=preregistered_pending and P emptied."
        )

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(SCHEMA_V2_COLUMNS)
        migrated = 0
        for legacy in data:
            # Map v1 columns → v2 by field name.
            v1 = dict(zip(SCHEMA_V1_COLUMNS, legacy, strict=False))
            writer.writerow(
                [
                    SCHEMA_VERSION,
                    v1.get("substrate", ""),
                    v1.get("regime", ""),
                    v1.get("control_family", ""),
                    v1.get("H_raw", ""),
                    v1.get("H_rank", ""),
                    v1.get("C", ""),
                    v1.get("gamma", ""),
                    v1.get("gamma_ci_lo", ""),
                    v1.get("gamma_ci_hi", ""),
                    "",  # P emptied — no silent carry-forward
                    PStatus.PREREGISTERED_PENDING.value,
                    v1.get("n_samples", ""),
                    v1.get("commit_sha", ""),
                    v1.get("timestamp_utc", ""),
                ]
            )
            migrated += 1
    return migrated


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
    * ``compute_metrics(output)`` — return
      ``(H, C, γ, γ_ci, P, P_status, n)`` under schema v2.

      ``P`` may be ``None``. When ``None``, ``P_status`` MUST be
      ``NOT_DEFINED`` or ``PREREGISTERED_PENDING``; when a float,
      ``P_status`` MUST be ``DEFINED``. Substrates without a
      preregistered productivity contract return ``(..., None,
      PStatus.NOT_DEFINED, n)``. A row emitted in that state is valid
      for regime diagnostics (H / C / γ) and MUST NOT feed any
      productivity or capability claim downstream.
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
    ) -> tuple[
        float, float, float, tuple[float, float], float | None, PStatus, int
    ]:  # pragma: no cover - abstract
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

    Entrypoint: ``tradepulse_v21.TradePulseV21Pipeline`` in
    ``substrates/kuramoto/analytics/regime/src/core/``.
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
                    P=None,
                    P_status=PStatus.NOT_DEFINED,
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
        H_raw, C, gamma, (ci_lo, ci_hi), P, p_status, n = adapter.compute_metrics(output)
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
                P_status=p_status,
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
        description=(
            "Levin → Neosynaptex bridge runner (see docs/protocols/levin_bridge_protocol.md)."
        ),
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
