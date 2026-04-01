"""Deterministic terminal presentation helpers for canonical demo flows."""

from __future__ import annotations

import os
import sys
from typing import Any

_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_DIM = "\033[2m"
_ANSI_CYAN = "\033[96m"
_ANSI_MAGENTA = "\033[95m"
_ANSI_GREEN = "\033[92m"
_ANSI_YELLOW = "\033[93m"
_ANSI_RED = "\033[91m"


def stderr_supports_color() -> bool:
    """Return whether stderr should emit ANSI color sequences."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "").lower() == "dumb":
        return False
    force = os.environ.get("BNSYN_CLI_THEME", "").strip().lower()
    if force in {"on", "force", "color", "neon"}:
        return True
    if force in {"off", "plain", "none"}:
        return False
    return bool(getattr(sys.stderr, "isatty", lambda: False)())


def _stylize(text: str, *codes: str) -> str:
    if not stderr_supports_color() or not codes:
        return text
    return f"{''.join(codes)}{text}{_ANSI_RESET}"


def _rule(label: str, *, glyph: str = "─") -> str:
    line = glyph * 18
    return f"{_stylize(line, _ANSI_DIM)} {_stylize(label, _ANSI_BOLD, _ANSI_CYAN)} {_stylize(line, _ANSI_DIM)}"


def _banner(title: str, subtitle: str) -> None:
    glyph = "✦" if stderr_supports_color() else "*"
    print(file=sys.stderr)
    print(
        _rule("BN-Syn canonical launch", glyph="═" if stderr_supports_color() else "="),
        file=sys.stderr,
    )
    print(_stylize(f"{glyph} {title}", _ANSI_BOLD, _ANSI_MAGENTA), file=sys.stderr)
    print(_stylize(subtitle, _ANSI_DIM), file=sys.stderr)
    print(_rule("emergent dynamics • criticality • reproducibility"), file=sys.stderr)


def _kv(label: str, value: str, *, tone: str = "info") -> None:
    tone_map = {
        "info": (_ANSI_CYAN,),
        "ok": (_ANSI_GREEN,),
        "warn": (_ANSI_YELLOW,),
        "error": (_ANSI_RED,),
    }
    codes = tone_map.get(tone, (_ANSI_CYAN,))
    prefix = _stylize("●", *codes)
    print(f"{prefix} {_stylize(label + ':', _ANSI_BOLD)} {value}", file=sys.stderr)


def emit_canonical_run_prelude(output_dir: str, export_proof: bool) -> None:
    """Emit a terminal prelude for the canonical run path."""
    mode = "canonical-export-proof" if export_proof else "canonical-base"
    _banner(
        "Launching deterministic neural proof bundle",
        "Designed for local first-run clarity, demo presentation, and reviewer trust.",
    )
    _kv("Profile", "canonical")
    _kv("Bundle mode", mode, tone="ok" if export_proof else "info")
    _kv("Output", output_dir)
    _kv(
        "Primary command",
        (
            "bnsyn run --profile canonical --plot --export-proof"
            if export_proof
            else "bnsyn run --profile canonical --plot"
        ),
    )


def emit_canonical_run_epilogue(bundle: dict[str, Any], export_proof: bool) -> None:
    """Emit canonical run completion guidance."""
    artifact_dir = str(bundle["artifact_dir"])
    summary = bundle.get("summary_metrics", {})
    proof_path = bundle.get("proof_report_path")
    product_summary_path = bundle.get("product_summary_path")
    index_html_path = bundle.get("index_html_path")
    print(_rule("canonical bundle ready"), file=sys.stderr)
    _kv("Artifact dir", artifact_dir, tone="ok")
    if isinstance(summary, dict):
        rate = summary.get("rate_mean_hz")
        sigma = summary.get("sigma_mean")
        coherence = summary.get("coherence_mean")
        if rate is not None:
            _kv("Mean rate", f"{float(rate):.3f} Hz")
        if sigma is not None:
            _kv("Sigma mean", f"{float(sigma):.4f}")
        if coherence is not None:
            _kv("Coherence mean", f"{float(coherence):.4f}")
    _kv("Primary visual", f"{artifact_dir}/emergence_plot.png", tone="ok")
    _kv("Manifest", f"{artifact_dir}/run_manifest.json")
    if export_proof and isinstance(proof_path, str):
        _kv("Proof report", proof_path, tone="ok")
        _kv("Proof check", f"bnsyn proof-validate-bundle {artifact_dir}", tone="warn")
    if isinstance(index_html_path, str):
        _kv("Open first", index_html_path, tone="ok")
    if isinstance(product_summary_path, str):
        _kv("Machine summary", product_summary_path, tone="ok")
    _kv("Product check", f"bnsyn validate-bundle {artifact_dir}", tone="warn")


def emit_bundle_validation_success(artifact_dir: str) -> None:
    """Emit success guidance for validate-bundle."""
    _banner(
        "Bundle validation passed",
        "Human-readable product surface, proof gate, and manifest lineage are aligned.",
    )
    _kv("Validated bundle", artifact_dir, tone="ok")


def emit_bundle_validation_failure(artifact_dir: str) -> None:
    """Emit failure guidance for validate-bundle."""
    _banner(
        "Bundle validation failed",
        "Review missing artifacts or contract mismatches before using the demo surface.",
    )
    _kv("Validated bundle", artifact_dir, tone="error")


def emit_demo_product_prelude(output_dir: str, package_version: str) -> None:
    """Emit prelude for the demo-product flow."""
    _banner(
        "Generating canonical demo product surface",
        "This path builds the reviewer-facing HTML report plus the full proof bundle.",
    )
    _kv("Output", output_dir)
    _kv("Package version", package_version)


def emit_demo_product_success(output_dir: str) -> None:
    """Emit completion guidance for demo-product."""
    _kv("Validation", "PASS", tone="ok")
    _kv("Open first", f"{output_dir}/index.html", tone="ok")
    _kv("Machine summary", f"{output_dir}/product_summary.json", tone="ok")
    _kv("Primary visual", f"{output_dir}/emergence_plot.png")
    _kv("Re-check", f"bnsyn validate-bundle {output_dir}", tone="warn")
