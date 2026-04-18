"""Forensic audit of a Decision Bridge telemetry ledger.

    python -m tools.audit.bridge_ledger_audit runs/bridge.jsonl

Emits a human-readable summary to stdout and a machine-parseable JSON
report to stderr (or ``--json-report <path>``). Exit code is:

    0 — ledger intact and no structural anomalies found
    1 — ledger intact but anomalies found (unknown regime, regime
        oscillation, DEAD verdict, etc.)
    2 — ledger chain is broken (tamper / truncation / reorder)
    3 — ledger path does not exist or cannot be read

This is the read-only side of the ledger contract (L-3 / L-5):
we only consume; we never write back.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.decision_bridge_telemetry import (
    LedgerVerification,
    TelemetryEvent,
    TelemetryLedger,
)

_EXIT_OK = 0
_EXIT_ANOMALY = 1
_EXIT_TAMPER = 2
_EXIT_IO = 3


@dataclass(frozen=True)
class LedgerAudit:
    """Full audit report — serialisable to JSON."""

    path: str
    verification: dict[str, Any]
    n_events: int
    tick_range: tuple[int, int] | None
    health_histogram: dict[str, int]
    regime_histogram: dict[str, int]
    risk_histogram: dict[str, int]
    n_dead_ticks: int
    n_regime_transitions: int
    anomalies: list[str] = field(default_factory=list)


def _build_audit(path: Path, events: list[TelemetryEvent], v: LedgerVerification) -> LedgerAudit:
    healths: Counter[str] = Counter()
    regimes: Counter[str] = Counter()
    risks: Counter[str] = Counter()
    anomalies: list[str] = []

    prev_regime: str | None = None
    transitions = 0
    tick_lo: int | None = None
    tick_hi: int | None = None
    n_dead = 0

    for e in events:
        p = e.payload
        health = str(p.get("system_health", ""))
        regime = str(p.get("operating_regime", ""))
        risk = str(p.get("hallucination_risk", ""))
        healths[health] += 1
        regimes[regime] += 1
        risks[risk] += 1
        if health == "DEAD":
            n_dead += 1
        tick_lo = e.tick if tick_lo is None else min(tick_lo, e.tick)
        tick_hi = e.tick if tick_hi is None else max(tick_hi, e.tick)
        if prev_regime is not None and regime != prev_regime:
            transitions += 1
        prev_regime = regime

    if n_dead:
        anomalies.append(f"{n_dead} tick(s) at system_health=DEAD")
    if "chaotic" in regimes:
        anomalies.append(f"{regimes['chaotic']} tick(s) in chaotic regime")
    if "high" in risks:
        anomalies.append(f"{risks['high']} tick(s) at hallucination_risk=high")
    if transitions > max(4, len(events) // 10):
        anomalies.append(f"regime oscillation: {transitions} transitions over {len(events)} events")

    tick_range: tuple[int, int] | None = (
        None if tick_lo is None or tick_hi is None else (tick_lo, tick_hi)
    )
    return LedgerAudit(
        path=str(path),
        verification=asdict(v),
        n_events=len(events),
        tick_range=tick_range,
        health_histogram=dict(healths),
        regime_histogram=dict(regimes),
        risk_histogram=dict(risks),
        n_dead_ticks=n_dead,
        n_regime_transitions=transitions,
        anomalies=anomalies,
    )


def _print_human(report: LedgerAudit) -> None:
    print(f"Ledger: {report.path}")
    print(f"  events: {report.n_events}")
    if report.tick_range is not None:
        print(f"  tick range: [{report.tick_range[0]} .. {report.tick_range[1]}]")
    v = report.verification
    if v["ok"]:
        print(f"  chain integrity: OK ({v['n_events']} links)")
    else:
        print(
            f"  chain integrity: BROKEN at index {v['first_broken_index']} — "
            f"{len(v['defects'])} defect(s)"
        )
    print(f"  health:  {report.health_histogram}")
    print(f"  regime:  {report.regime_histogram}")
    print(f"  risk:    {report.risk_histogram}")
    print(f"  regime transitions: {report.n_regime_transitions}")
    if report.anomalies:
        print("  anomalies:")
        for a in report.anomalies:
            print(f"    - {a}")
    else:
        print("  anomalies: none")


def audit(path: Path) -> tuple[int, LedgerAudit | None]:
    if not path.exists():
        return _EXIT_IO, None
    verification = TelemetryLedger.verify(path)
    events = list(TelemetryLedger.iter_events(path))
    report = _build_audit(path, events, verification)
    if not verification.ok:
        return _EXIT_TAMPER, report
    if report.anomalies:
        return _EXIT_ANOMALY, report
    return _EXIT_OK, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit a DecisionBridge telemetry ledger (read-only).")
    ap.add_argument("ledger", type=Path)
    ap.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write the machine-readable report to this path.",
    )
    ns = ap.parse_args(argv)

    exit_code, report = audit(ns.ledger)
    if report is None:
        print(f"error: ledger not found: {ns.ledger}", file=sys.stderr)
        return exit_code

    _print_human(report)
    if ns.json_report is not None:
        ns.json_report.parent.mkdir(parents=True, exist_ok=True)
        ns.json_report.write_text(
            json.dumps(asdict(report), sort_keys=True, indent=2),
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
