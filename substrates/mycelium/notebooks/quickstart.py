import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    mo.md("# MyceliumFractalNet — Quickstart")
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    ## 1. Simulate a Turing pattern
    Run a 32×32 reaction-diffusion simulation with default parameters.
    """)
    return


@app.cell
def _():
    import mycelium_fractal_net as mfn
    import numpy as np

    spec = mfn.SimulationSpec(grid_size=32, steps=60, seed=42)
    seq = mfn.simulate(spec)
    print(f"Field shape: {seq.field.shape}")
    print(f"History: {seq.history.shape}")
    return mfn, np, seq, spec


@app.cell
def _(mfn, seq):
    print(mfn.plot_field(seq))
    return


@app.cell
def _(mfn, seq, mo):
    mo.md("## 2. Diagnose the system")
    det = mfn.detect(seq)
    diag = mfn.diagnose(seq)
    print(f"Label: {det.label} (score={det.score:.3f})")
    print(f"Severity: {diag.severity}")
    return


@app.cell
def _(mfn, seq, mo):
    mo.md("## 3. Explain in natural language")
    print(mfn.explain(seq))
    return


@app.cell
def _(mfn, seq, mo):
    mo.md("## 4. Check invariants")
    print(mfn.invariance_report(seq))
    return


@app.cell
def _(mfn, seq, mo):
    mo.md("## 5. Extract features")
    desc = mfn.extract(seq)
    print(f"Embedding: {len(desc.embedding)} dimensions")
    print(f"D_box = {desc.features['D_box']:.3f}")
    return


@app.cell
def _(mo):
    mo.md("## 6. Auto-heal")
    return


@app.cell
def _(mfn, seq):
    heal = mfn.auto_heal(seq, budget=3)
    print(f"Healed: {heal.healed}")
    print(f"M: {heal.M_before:.4f} → {heal.M_after:.4f}")
    return


if __name__ == "__main__":
    app.run()
