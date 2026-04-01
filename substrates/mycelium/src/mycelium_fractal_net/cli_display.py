"""Terminal display formatting for MFN CLI.

Rich-inspired output without heavy dependencies.
Uses ANSI escape codes for color when terminal supports it.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _supports_color()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def dim(text: str) -> str:
    return _c("2", text)


def bold(text: str) -> str:
    return _c("1", text)


def green(text: str) -> str:
    return _c("32", text)


def yellow(text: str) -> str:
    return _c("33", text)


def red(text: str) -> str:
    return _c("31", text)


def cyan(text: str) -> str:
    return _c("36", text)


def blue(text: str) -> str:
    return _c("34", text)


def magenta(text: str) -> str:
    return _c("35", text)


# ═══════════════════════════════════════════════════════════
# Header / banner
# ═══════════════════════════════════════════════════════════


def banner() -> str:
    return (
        f"\n{bold('MFN')} {dim('v4.1.0')} {dim('|')} Morphology-aware Field Intelligence Engine\n"
    )


def section(title: str) -> str:
    return f"\n{bold(cyan(title))}\n{'─' * min(len(title) + 4, 60)}"


# ═══════════════════════════════════════════════════════════
# Simulation display
# ═══════════════════════════════════════════════════════════


def format_simulation(seq: Any) -> str:
    lines = [section("Simulation")]
    spec = seq.spec
    if spec:
        lines.append(f"  Grid:     {bold(str(spec.grid_size))}x{spec.grid_size}")
        lines.append(f"  Steps:    {bold(str(spec.steps))}")
        lines.append(f"  Seed:     {spec.seed}")
        lines.append(f"  Alpha:    {spec.alpha}")
        if spec.neuromodulation and spec.neuromodulation.enabled:
            lines.append(f"  Neuromod: {magenta(spec.neuromodulation.profile)}")

    lines.append(
        f"  Field:    [{seq.field_min_mV:.1f}, {seq.field_max_mV:.1f}] mV  "
        f"mean={seq.field_mean_mV:.1f} mV"
    )
    lines.append(f"  History:  {'yes' if seq.has_history else 'no'}")
    lines.append(f"  Hash:     {dim(seq.runtime_hash)}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Detection display
# ═══════════════════════════════════════════════════════════


def _label_color(label: str) -> str:
    if label in ("nominal", "stable", "near-identical"):
        return green(label)
    if label in ("watch", "transitional", "similar", "related"):
        return yellow(label)
    return red(label)


def format_detection(event: Any) -> str:
    lines = [section("Detection")]
    lines.append(
        f"  Anomaly:  {_label_color(event.label)}  score={event.score:.3f}  conf={event.confidence:.2f}"
    )
    if event.regime:
        lines.append(
            f"  Regime:   {_label_color(event.regime.label)}  score={event.regime.score:.3f}"
        )
    top = event.contributing_features[:3]
    if top:
        lines.append(f"  Drivers:  {', '.join(top)}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Descriptor display
# ═══════════════════════════════════════════════════════════


def format_descriptor(desc: Any) -> str:
    lines = [section("Morphology Descriptor")]
    lines.append(f"  Version:      {desc.version}")
    lines.append(f"  Embedding:    {len(desc.embedding)} dims")

    d_box = desc.features.get("D_box", 0)
    f_active = desc.features.get("f_active", 0)
    lines.append(f"  D_box:        {bold(f'{d_box:.3f}')}")
    lines.append(f"  f_active:     {f_active:.3f}")

    ii = desc.stability.get("instability_index", 0)
    lines.append(f"  Instability:  {ii:.4f}")

    conn = desc.connectivity.get("connectivity_divergence", 0)
    lines.append(f"  Connectivity: {conn:.4f}")

    plast = desc.neuromodulation.get("plasticity_index", 0)
    if plast > 0:
        lines.append(f"  Plasticity:   {magenta(f'{plast:.4f}')}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Forecast display
# ═══════════════════════════════════════════════════════════


def format_forecast(fcast: Any) -> str:
    fd = fcast.to_dict()
    lines = [section("Forecast")]
    lines.append(f"  Horizon:  {bold(str(fd['horizon']))} steps")
    lines.append(f"  Method:   {fd['method']}")
    se = fd.get("benchmark_metrics", {}).get("forecast_structural_error", 0)
    damping = fd.get("benchmark_metrics", {}).get("adaptive_damping", 0)
    lines.append(f"  Error:    {se:.4f}")
    lines.append(f"  Damping:  {damping:.3f}")
    unc = fd.get("uncertainty_envelope", {}).get("ensemble_std_mV", 0)
    if unc > 0:
        lines.append(f"  Uncert:   {unc:.2f} mV")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Comparison display
# ═══════════════════════════════════════════════════════════


def format_comparison(comp: Any) -> str:
    lines = [section("Comparison")]
    lines.append(f"  Label:    {_label_color(comp.label)}")
    lines.append(f"  Distance: {comp.distance:.6f}")
    lines.append(f"  Cosine:   {comp.cosine_similarity:.4f}")
    lines.append(f"  Topology: {comp.topology_label}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Report display
# ═══════════════════════════════════════════════════════════


def format_report(report: Any) -> str:
    lines = [section("Report Generated")]
    lines.append(f"  Run ID:   {bold(report.run_id)}")
    lines.append(f"  Anomaly:  {_label_color(report.detection.label)}")
    if report.detection.regime:
        lines.append(f"  Regime:   {_label_color(report.detection.regime.label)}")
    if report.forecast:
        fd = report.forecast.to_dict()
        lines.append(f"  Forecast: h={fd['horizon']}")
    if report.comparison:
        lines.append(f"  Compare:  {_label_color(report.comparison.label)}")
    artifacts = report.artifacts
    if artifacts:
        lines.append(f"  Artifacts: {len(artifacts)} files")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Causal validation display
# ═══════════════════════════════════════════════════════════


def format_causal(result: Any) -> str:
    lines = [section("Causal Validation")]
    decision = result.decision.value
    if decision == "pass":
        lines.append(f"  Decision: {green('PASS')}")
    elif decision == "degraded":
        lines.append(f"  Decision: {yellow('DEGRADED')}")
    else:
        lines.append(f"  Decision: {red('FAIL')}")

    total = len(result.rule_results)
    passed = sum(1 for r in result.rule_results if r.passed)
    lines.append(f"  Rules:    {passed}/{total}")
    if result.error_count:
        lines.append(f"  Errors:   {red(str(result.error_count))}")
    if result.warning_count:
        lines.append(f"  Warnings: {yellow(str(result.warning_count))}")

    for v in result.violations[:5]:
        sev = v.severity.value.upper()
        if sev in ("ERROR", "FATAL"):
            lines.append(f"    {red(sev):8s} [{v.rule_id}] {v.message}")
        elif sev == "WARN":
            lines.append(f"    {yellow(sev):8s} [{v.rule_id}] {v.message}")
        else:
            lines.append(f"    {dim(sev):8s} [{v.rule_id}] {v.message}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Full pipeline display
# ═══════════════════════════════════════════════════════════


def format_pipeline(
    seq: Any,
    desc: Any | None = None,
    event: Any | None = None,
    fcast: Any | None = None,
    comp: Any | None = None,
    causal: Any | None = None,
) -> str:
    parts = [banner(), format_simulation(seq)]
    if desc:
        parts.append(format_descriptor(desc))
    if event:
        parts.append(format_detection(event))
    if fcast:
        parts.append(format_forecast(fcast))
    if comp:
        parts.append(format_comparison(comp))
    if causal:
        parts.append(format_causal(causal))
    parts.append("")
    return "\n".join(parts)
