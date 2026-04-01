"""Live demo: python -m mycelium_fractal_net

Shows the full system in action with Rich terminal output.
Falls back to plain text if Rich is not installed.
"""

from __future__ import annotations

import time


def _run_rich() -> None:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    import mycelium_fractal_net as mfn

    console = Console()
    console.print()
    console.print(
        Panel.fit(
            f"[bold white]MyceliumFractalNet[/bold white]  [dim]v{mfn.__version__}[/dim]\n"
            "[dim]Reaction-diffusion analytics · Causal validation · Bio physics[/dim]",
            border_style="green",
        )
    )
    console.print()
    from mycelium_fractal_net.bio import BioExtension

    try:
        from mycelium_fractal_net.bio import MetaOptimizer

        _has_meta = True
    except ImportError:
        _has_meta = False
    from mycelium_fractal_net.types.field import SimulationSpec

    # Step 1: Simulate
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True
    ) as p:
        p.add_task("Simulating Turing morphogenesis (32x32, 60 steps)...", total=1)
        t0 = time.perf_counter()
        spec = SimulationSpec(grid_size=32, steps=60, seed=42)
        seq = mfn.simulate(spec)
        sim_ms = (time.perf_counter() - t0) * 1000

    # Step 2: Bio
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True
    ) as p:
        p.add_task("Running bio layer (Physarum + Anastomosis + FHN)...", total=1)
        t0 = time.perf_counter()
        bio = BioExtension.from_sequence(seq).step(n=5)
        bio_ms = (time.perf_counter() - t0) * 1000
        bio_r = bio.report()

    # Step 3: Diagnose
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True
    ) as p:
        p.add_task("Running full diagnostic pipeline...", total=1)
        t0 = time.perf_counter()
        report = mfn.diagnose(seq, skip_intervention=True)
        diag_ms = (time.perf_counter() - t0) * 1000

    # Results table
    table = Table(
        title="[bold]System State[/bold]",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold dim",
    )
    table.add_column("Layer", style="cyan", no_wrap=True)
    table.add_column("Signal", style="white")
    table.add_column("Value", style="bold yellow", justify="right")
    table.add_column("Time", style="dim", justify="right")

    table.add_row(
        "Turing RD", "Field V_mean", f"{seq.field.mean() * 1000:.1f} mV", f"{sim_ms:.0f}ms"
    )

    ews = report.warning
    ec = "red" if ews.ews_score > 0.7 else "yellow" if ews.ews_score > 0.3 else "green"
    table.add_row(
        "Early Warning",
        f"[{ec}]{ews.transition_type}[/{ec}]",
        f"score={ews.ews_score:.3f}",
        f"{diag_ms:.0f}ms",
    )

    cc = {"pass": "green", "degraded": "yellow", "fail": "red"}.get(
        report.causal.decision.value, "dim"
    )
    n_rules = len(report.causal.rule_results)
    n_err = sum(
        1
        for r in report.causal.rule_results
        if not r.passed and r.severity.value in ("error", "fatal")
    )
    table.add_row(
        "Causal Gate",
        f"[{cc}]{report.causal.decision.value.upper()}[/{cc}]",
        f"{n_rules} rules · {n_err} errors",
        "—",
    )

    table.add_row(
        "Physarum",
        "Conductivity Dmax",
        f"{bio_r.physarum.get('conductivity_max', 0):.3f}",
        f"{bio_ms:.0f}ms",
    )
    table.add_row(
        "Anastomosis",
        "Hyphal density B",
        f"{bio_r.anastomosis.get('hyphal_density_mean', 0):.5f}",
        "—",
    )
    table.add_row(
        "FHN Signaling", "Spiking fraction", f"{bio_r.fhn.get('spiking_fraction', 0):.3f}", "—"
    )

    console.print(table)
    console.print()

    sev = report.severity
    sc = {"stable": "green", "info": "blue", "warning": "yellow", "critical": "red"}.get(
        sev, "white"
    )
    console.print(
        Panel(
            f"[{sc}][bold]{sev.upper()}[/bold][/{sc}]\n\n{report.narrative}",
            title="[bold]Diagnosis[/bold]",
            border_style=sc,
            padding=(1, 2),
        )
    )
    console.print()

    console.print(
        f"  [dim]Causal certificate:[/dim] [{cc}]{report.causal.decision.value}[/{cc}]  "
        f"[dim]·  EWS:[/dim] [{ec}]{ews.causal_certificate}[/{ec}]  "
        f"[dim]·  Rules: {n_rules}/{n_rules} evaluated[/dim]"
    )
    console.print()

    # Quick meta demo (optional — requires scipy + cmaes)
    if _has_meta:
        console.print("[bold dim]MetaOptimizer (2 gen, grid=8, fast)...[/bold dim]")
        try:
            meta = MetaOptimizer(grid_size=8, steps=10, bio_steps=2, seed=42)
            result = meta.run(n_generations=2, population_size=4, verbose=False)
            mt = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            mt.add_column(style="dim")
            mt.add_column(style="bold yellow")
            mt.add_row("Best fitness", f"{result.evolution_result.best_fitness:.4f}")
            mt.add_row("Cache hits", f"{result.cache_hits}/{result.total_queries}")
            mt.add_row("Memory episodes", str(result.memory_size))
            mt.add_row("Time", f"{result.evolution_result.elapsed_seconds:.1f}s")
            console.print(mt)
        except Exception as e:
            console.print(f"  [dim]MetaOptimizer skipped: {e}[/dim]")
    else:
        console.print("  [dim]MetaOptimizer requires: pip install -e '.[bio]'[/dim]")
    console.print()
    console.print("  [dim]github.com/neuron7x/mycelium-fractal-net[/dim]")
    console.print()


def _run_plain() -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio import BioExtension
    from mycelium_fractal_net.types.field import SimulationSpec

    print(f"\nMyceliumFractalNet v{mfn.__version__}\n")
    spec = SimulationSpec(grid_size=32, steps=60, seed=42)
    seq = mfn.simulate(spec)
    bio = BioExtension.from_sequence(seq).step(n=5)
    report = mfn.diagnose(seq, skip_intervention=True)
    print(report.summary())
    print(report.narrative)
    print(f"\nBio: {bio.report().summary()}")
    print()


def main() -> None:
    try:
        from rich.console import Console  # noqa: F401

        _run_rich()
    except ImportError:
        _run_plain()


if __name__ == "__main__":
    main()
