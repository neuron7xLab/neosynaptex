"""System health diagnostics and introspection for MFN CLI.

Provides `mfn doctor`, `mfn info`, and `mfn scenarios` commands
for system-level visibility.
"""

from __future__ import annotations

import importlib
import platform
import sys
import time
from pathlib import Path

from mycelium_fractal_net.cli_display import (
    bold,
    cyan,
    dim,
    green,
    red,
    yellow,
)


def run_doctor() -> str:
    """Run system health check. Returns formatted status."""
    lines = [
        f"\n{bold('MFN Doctor')} {dim('— system health check')}\n",
        "─" * 50,
    ]
    all_ok = True

    # 1. Python version
    py = platform.python_version()
    py_ok = sys.version_info >= (3, 10)
    lines.append(
        f"  {'✓' if py_ok else '✗'} Python {py}" + ("" if py_ok else f"  {red('requires ≥3.10')}")
    )
    all_ok = all_ok and py_ok

    # 2. Package import
    try:
        import mycelium_fractal_net as mfn

        lines.append(f"  ✓ mycelium_fractal_net v{mfn.__version__}")
    except Exception as e:
        lines.append(f"  ✗ Import failed: {red(str(e))}")
        all_ok = False

    # 3. Core dependencies
    for dep in ["numpy", "pydantic", "fastapi", "sympy", "cryptography"]:
        try:
            mod = importlib.import_module(dep)
            ver = getattr(mod, "__version__", "?")
            lines.append(f"  ✓ {dep} {dim(ver)}")
        except ImportError:
            lines.append(f"  ✗ {dep} {red('not installed')}")
            all_ok = False

    # 4. Optional dependencies
    for dep, extra in [("torch", "ml"), ("numba", "accel")]:
        try:
            mod = importlib.import_module(dep)
            ver = getattr(mod, "__version__", "?")
            lines.append(f"  ✓ {dep} {dim(ver)} [{extra}]")
        except ImportError:
            lines.append(f"  ○ {dep} {dim('not installed')} [{extra} optional]")

    # 5. Simulation smoke test
    try:
        import mycelium_fractal_net as mfn

        start = time.perf_counter()
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=4, seed=1))  # type: ignore[attr-defined]
        elapsed = (time.perf_counter() - start) * 1000
        lines.append(f"  ✓ Simulation smoke test {dim(f'{elapsed:.0f}ms')}")
    except Exception as e:
        lines.append(f"  ✗ Simulation failed: {red(str(e))}")
        all_ok = False

    # 6. Causal validation
    try:
        from mycelium_fractal_net.core.causal_validation import (
            validate_causal_consistency,
        )

        result = validate_causal_consistency(seq)
        lines.append(
            f"  ✓ Causal validation {dim(f'{result.decision.value}, {len(result.rule_results)} rules')}"
        )
    except Exception as e:
        lines.append(f"  ✗ Causal validation failed: {red(str(e))}")
        all_ok = False

    # 7. Configs present
    config_dir = Path(__file__).resolve().parents[2] / "configs"
    for cfg in [
        "detection_thresholds_v1.json",
        "causal_validation_v1.json",
        "benchmark_baseline.json",
    ]:
        path = config_dir / cfg
        if path.exists():
            lines.append(f"  ✓ {cfg}")
        else:
            lines.append(f"  ✗ {cfg} {red('missing')}")
            all_ok = False

    lines.append("─" * 50)
    if all_ok:
        lines.append(f"  {green(bold('System healthy.'))}")
    else:
        lines.append(f"  {yellow(bold('Issues detected. See above.'))}")

    return "\n".join(lines)


def run_info() -> str:
    """Show system info and metrics."""
    import mycelium_fractal_net as mfn

    src = Path(__file__).resolve().parent
    py_files = list(src.rglob("*.py"))
    total_loc = sum(len(f.read_text().splitlines()) for f in py_files)
    test_dir = src.parents[1] / "tests"
    test_files = list(test_dir.rglob("*.py")) if test_dir.exists() else []
    test_loc = sum(len(f.read_text().splitlines()) for f in test_files)

    lines = [
        f"\n{bold('MFN')} {dim('v' + mfn.__version__)} {dim('— system info')}\n",
        "─" * 50,
        "  Engine:     Morphology-aware Field Intelligence Engine",
        f"  Version:    {bold(mfn.__version__)}",
        f"  Python:     {platform.python_version()}",
        f"  Platform:   {platform.system()} {platform.machine()}",
        f"  Source:      {len(py_files)} files, {total_loc:,} lines",
        f"  Tests:      {len(test_files)} files, {test_loc:,} lines",
        f"  Ratio:      {test_loc / max(total_loc, 1):.2f} test/source",
        "",
        f"  {cyan('Pipeline:')}   simulate → extract → detect → forecast → compare → report",
        f"  {cyan('Causal:')}     42 rules, 7 stages, perturbation stability",
        f"  {cyan('Security:')}   Ed25519, CSP, HSTS, rate limiting, output sanitization",
        "─" * 50,
    ]
    return "\n".join(lines)


def run_scenarios() -> str:
    """List available simulation scenarios with descriptions."""

    scenarios = {
        "synthetic_morphology": "Pure Turing morphogenesis, no neuromodulation",
        "sensor_grid_anomaly": "Gaussian temporal smoothing observation noise overlay",
        "regime_transition": "Serotonergic reorganization candidate",
        "balanced_criticality": "GABA-A + serotonergic at criticality boundary",
        "inhibitory_stabilization": "GABA-A tonic muscimol (high inhibition)",
        "high_inhibition_recovery": "Extrasynaptic delta GABA-A (recovery kinetics)",
    }

    lines = [
        f"\n{bold('Available Scenarios')}\n",
        "─" * 60,
    ]
    for name, desc in scenarios.items():
        lines.append(f"  {cyan(name)}")
        lines.append(f"    {dim(desc)}")
        lines.append("")

    lines.append(f"  {dim('Usage:')} mfn simulate --neuromod-profile <name>")
    lines.append(f"  {dim('Or:')}    mfn.simulate(mfn.SimulationSpec(neuromodulation=...))")
    return "\n".join(lines)
