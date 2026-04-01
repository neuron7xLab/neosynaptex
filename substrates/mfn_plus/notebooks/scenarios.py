import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    mo.md("# MFN Scenario Explorer")
    return (mo,)


@app.cell
def _(mo):
    alpha_slider = mo.ui.slider(0.08, 0.24, step=0.02, value=0.18, label="α (diffusion)")
    spike_slider = mo.ui.slider(0.05, 0.40, step=0.05, value=0.22, label="spike probability")
    seed_input = mo.ui.number(value=42, start=0, stop=9999, label="seed")
    mo.hstack([alpha_slider, spike_slider, seed_input])
    return alpha_slider, spike_slider, seed_input


@app.cell
def _(alpha_slider, spike_slider, seed_input):
    import mycelium_fractal_net as mfn
    spec = mfn.SimulationSpec(
        grid_size=32, steps=60,
        seed=int(seed_input.value),
        alpha=float(alpha_slider.value),
        spike_probability=float(spike_slider.value),
    )
    seq = mfn.simulate(spec)
    print(mfn.plot_field(seq))
    return mfn, seq


@app.cell
def _(mfn, seq):
    det = mfn.detect(seq)
    ews = mfn.early_warning(seq)
    print(f"Detection: {det.label} (score={det.score:.3f})")
    print(f"EWS: {ews.transition_type} (score={ews.ews_score:.3f})")
    print()
    print(mfn.invariance_report(seq))
    return


@app.cell
def _(mfn, seq):
    from mycelium_fractal_net.analytics.synchronization import kuramoto_order_parameter
    from mycelium_fractal_net.analytics.bifiltration import compute_bifiltration

    k = kuramoto_order_parameter(seq.field)
    bf = compute_bifiltration(seq.field, n_thresholds=8)
    print(f"Kuramoto: {k.summary()}")
    print(f"Bifiltration: {bf.summary()}")
    return


if __name__ == "__main__":
    app.run()
