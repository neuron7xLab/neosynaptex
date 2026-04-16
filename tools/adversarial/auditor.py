"""Auditor orchestrator — §IV.B role.

Runs the in-repo set of Auditor tools in priority order (Verifier
first per §IV.B), captures per-tool verdicts + aggregate outcome,
and emits canonical T2 telemetry for the run.

Scope
-----

* The orchestrator is a **runner**, not a new checker. It does not
  re-implement any invariant — it delegates to each tool's own
  ``run_check()``.
* Per-tool failures are **surfaced, not hidden**. The aggregate
  verdict is ``fail`` iff any tool returned a non-zero exit code.
* Telemetry is **best-effort**. If ``tools.telemetry.emit`` is not
  importable (minimal CI image, pre-#84 main), the orchestrator
  still produces its text report; emission is silently skipped.

Tool registry
-------------

``TOOLS`` is a tuple of ``AuditorTool`` descriptors in execution
priority. Adding a new Auditor tool here is the one-line way to
wire it into the orchestrator.

Priority rationale (per §IV.B: Verifier > Auditor > Critic):

1. ``measurement_contract_verifier`` — Verifier. Runs first because
   §IV.B makes a Verifier failure block everything downstream.
2. ``claim_status_applied`` — Auditor (label discipline over git log).
3. ``pr_body_check`` — Auditor (syntactic gate on incoming PRs).
   Only runs when a PR body is supplied; otherwise skipped.

Future Auditor tools (adapter_scope_check, kill_signal_coverage,
replication_index_check, telemetry_adoption, canon_reference_check,
gamma_ledger_integrity) slot in here once their defining PRs land.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import logging
import pathlib
import sys
import time
from collections.abc import Callable

__all__ = [
    "TOOLS",
    "AuditorReport",
    "AuditorTool",
    "ToolVerdict",
    "main",
    "run_all",
]

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class AuditorTool:
    """One tool slot in the orchestrator.

    ``mandatory`` tools cannot be silently skipped: missing modules,
    import failures, and runtime exceptions all convert to a FAIL
    verdict (see ``ToolVerdict.ok``). Optional tools (e.g. the PR-body
    checker, which requires an explicit ``--pr-body``) remain skippable.
    """

    name: str
    module_path: str  # e.g. "tools.adversarial.verifier"
    entry: str = "run_check"  # function that returns (int, ...) where int is exit code
    requires_pr_body: bool = False
    mandatory: bool = False

    def load(self) -> Callable | None:
        try:
            mod = importlib.import_module(self.module_path)
        except ImportError as exc:
            logger.warning("auditor: skipping %s: %s", self.name, exc)
            return None
        return getattr(mod, self.entry, None)


@dataclasses.dataclass(frozen=True)
class ToolVerdict:
    """Verdict from one tool invocation."""

    name: str
    exit_code: int
    duration_ms: float
    message: str
    skipped: bool = False
    mandatory: bool = False

    @property
    def ok(self) -> bool:
        # Mandatory tools cannot pass by being skipped; a missing
        # evidentiary gate is a blocking failure, not a soft skip.
        if self.skipped:
            return not self.mandatory
        return self.exit_code == 0


@dataclasses.dataclass(frozen=True)
class AuditorReport:
    """Aggregate Auditor-orchestrator verdict."""

    verdicts: tuple[ToolVerdict, ...]
    total_duration_ms: float

    @property
    def ok(self) -> bool:
        return all(v.ok for v in self.verdicts)

    @property
    def n_run(self) -> int:
        return sum(1 for v in self.verdicts if not v.skipped)

    @property
    def n_skipped(self) -> int:
        return sum(1 for v in self.verdicts if v.skipped)

    @property
    def n_failed(self) -> int:
        return sum(1 for v in self.verdicts if not v.skipped and not v.ok)


# Canonical execution order. Verifier first per §IV.B.
#
# ``mandatory`` gates MUST produce an explicit pass; a missing module,
# an unimportable entry point, or a runtime exception all count as a
# blocking failure. Optional gates (e.g. ``pr_body_check``, which runs
# only when a PR body is supplied) remain skippable without failing.
TOOLS: tuple[AuditorTool, ...] = (
    AuditorTool(
        name="measurement_contract_verifier",
        module_path="tools.adversarial.verifier",
        mandatory=True,
    ),
    AuditorTool(
        name="null_family_gate",
        module_path="tools.audit.null_family_gate",
        entry="run_check",
        mandatory=True,
    ),
    AuditorTool(
        name="claim_status_applied",
        module_path="tools.audit.claim_status_applied",
        entry="run_audit",
    ),
    AuditorTool(
        name="pr_body_check",
        module_path="tools.audit.pr_body_check",
        entry="validate",
        requires_pr_body=True,
    ),
)


# ---------------------------------------------------------------------------
# Telemetry wrapper — best-effort
# ---------------------------------------------------------------------------


class _NoopSpan:
    """Fallback for when tools.telemetry.emit is not importable."""

    def __enter__(self) -> str:
        return ""

    def __exit__(self, *args: object) -> None:
        return None


def _resolve_telemetry() -> tuple[Callable | None, Callable | None]:
    try:
        from tools.telemetry.emit import emit_event, span  # type: ignore[import-untyped]

        return emit_event, span
    except ImportError:
        return None, None


# ---------------------------------------------------------------------------
# Per-tool invocation
# ---------------------------------------------------------------------------


def _invoke_verifier_style(fn: Callable) -> tuple[int, str]:
    """Tools whose ``run_check`` returns (int, ...) with exit code first."""

    result = fn()
    if isinstance(result, tuple) and result:
        exit_code = int(result[0])
        tail = result[1:]
        message = ""
        if tail:
            last = tail[-1]
            message = last if isinstance(last, str) else repr(last)
        return exit_code, message
    raise TypeError(f"{fn!r}: expected a (exit_code, ...) tuple; got {type(result).__name__}")


def _invoke_claim_status_applied(fn: Callable) -> tuple[int, str]:
    """claim_status_applied.run_audit returns (windows, Verdict)."""

    _, verdict = fn()
    # Canonical mapping: applied→ok, at_risk→2, stopped→2.
    exit_code = 0 if verdict.name == "applied" else 2
    return exit_code, f"verdict={verdict.name}: {verdict.reason[:120]}"


def _invoke_pr_body_check(fn: Callable, *, pr_body: str | None) -> tuple[int, str]:
    """pr_body_check.validate returns (ok: bool, reason: str)."""

    if pr_body is None:
        raise RuntimeError("pr_body_check requires --pr-body; caller should skip")
    ok, reason = fn(pr_body)
    return (0 if ok else 2), reason[:200]


def _invoke(tool: AuditorTool, fn: Callable, *, pr_body: str | None) -> tuple[int, str]:
    if tool.name == "claim_status_applied":
        return _invoke_claim_status_applied(fn)
    if tool.name == "pr_body_check":
        return _invoke_pr_body_check(fn, pr_body=pr_body)
    return _invoke_verifier_style(fn)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_all(
    *,
    tools: tuple[AuditorTool, ...] = TOOLS,
    pr_body: str | None = None,
) -> AuditorReport:
    """Run every tool in priority order; return an AuditorReport."""

    emit_event, span_ctx = _resolve_telemetry()
    verdicts: list[ToolVerdict] = []
    start_total = time.monotonic()

    cm = span_ctx("adversarial.audit.run", "adversarial") if span_ctx else _NoopSpan()
    with cm:
        for tool in tools:
            if tool.requires_pr_body and pr_body is None:
                verdicts.append(
                    ToolVerdict(
                        name=tool.name,
                        exit_code=0,
                        duration_ms=0.0,
                        message="skipped (no --pr-body supplied)",
                        skipped=True,
                        mandatory=tool.mandatory,
                    )
                )
                continue
            fn = tool.load()
            if fn is None:
                # Mandatory tools cannot be silently skipped: emit a
                # non-zero exit code so the aggregate verdict fails.
                if tool.mandatory:
                    verdicts.append(
                        ToolVerdict(
                            name=tool.name,
                            exit_code=2,
                            duration_ms=0.0,
                            message=(f"mandatory tool {tool.module_path} not importable -- FAIL"),
                            skipped=False,
                            mandatory=True,
                        )
                    )
                else:
                    verdicts.append(
                        ToolVerdict(
                            name=tool.name,
                            exit_code=0,
                            duration_ms=0.0,
                            message=f"skipped (module {tool.module_path} not importable)",
                            skipped=True,
                            mandatory=False,
                        )
                    )
                continue
            per_tool_span = (
                span_ctx(f"audit.{tool.name}.run", f"audit.{tool.name}")
                if span_ctx
                else _NoopSpan()
            )
            t0 = time.monotonic()
            with per_tool_span:
                try:
                    exit_code, message = _invoke(tool, fn, pr_body=pr_body)
                except Exception as exc:  # noqa: BLE001 — surface tool errors as failure
                    exit_code, message = 2, f"exception: {exc!r}"
                duration_ms = (time.monotonic() - t0) * 1000.0
                if emit_event is not None:
                    emit_event(
                        f"audit.{tool.name}.verdict",
                        f"audit.{tool.name}",
                        payload={
                            "exit_code": exit_code,
                            "message_head": message[:200],
                        },
                        outcome="ok" if exit_code == 0 else "fail",
                    )
            verdicts.append(
                ToolVerdict(
                    name=tool.name,
                    exit_code=exit_code,
                    duration_ms=duration_ms,
                    message=message,
                    mandatory=tool.mandatory,
                )
            )

    total_duration_ms = (time.monotonic() - start_total) * 1000.0
    report = AuditorReport(verdicts=tuple(verdicts), total_duration_ms=total_duration_ms)
    if emit_event is not None:
        emit_event(
            "adversarial.audit.verdict",
            "adversarial",
            payload={
                "n_run": report.n_run,
                "n_skipped": report.n_skipped,
                "n_failed": report.n_failed,
                "total_duration_ms": round(report.total_duration_ms, 3),
            },
            outcome="ok" if report.ok else "fail",
        )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(report: AuditorReport) -> str:
    lines: list[str] = []
    header = "OK" if report.ok else "FAIL"
    lines.append(
        f"{header}: {report.n_run} tool(s) run, "
        f"{report.n_failed} failed, "
        f"{report.n_skipped} skipped, "
        f"total {report.total_duration_ms:.1f} ms"
    )
    for v in report.verdicts:
        marker = "SKIP" if v.skipped else ("OK" if v.ok else "FAIL")
        lines.append(f"  [{marker}] {v.name} ({v.duration_ms:.1f} ms) — {v.message}")
    return "\n".join(lines)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adversarial.auditor",
        description=(
            "Run the in-repo Auditor stack in §IV.B priority order. "
            "Verifier first, then per-tool checks. Aggregate exit code "
            "is non-zero on any tool failure."
        ),
    )
    p.add_argument(
        "--pr-body",
        type=pathlib.Path,
        default=None,
        help="Optional path to a PR body text file for pr_body_check. "
        "If absent, pr_body_check is skipped.",
    )
    return p


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    logging.basicConfig(level="INFO")
    ns = _build_argparser().parse_args(argv)
    pr_body: str | None = None
    if ns.pr_body is not None:
        pr_body = pathlib.Path(ns.pr_body).read_text(encoding="utf-8")
    report = run_all(pr_body=pr_body)
    stream = sys.stdout if report.ok else sys.stderr
    print(_format_report(report), file=stream)
    return 0 if report.ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
