"""Interactive Streamlit dashboard for BN-Syn exploration.

Provides real-time parameter exploration with 4 visualization tabs:
- Raster plot
- Voltage traces
- Firing rates
- Population statistics

References
----------
docs/LEGENDARY_QUICKSTART.md
"""

from __future__ import annotations

from typing import Any

import numpy as np

HAVE_STREAMLIT = False
_IMPORT_ERROR: ImportError | None = None

try:
    import plotly.graph_objects as go
    import streamlit as st

    HAVE_STREAMLIT = True
except ImportError as e:
    _IMPORT_ERROR = e


def main() -> None:
    """Launch interactive BN-Syn dashboard.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If optional visualization dependencies are not installed.

    Examples
    --------
    Launch from command line::

        bnsyn demo --interactive

    Or directly::

        streamlit run src/bnsyn/viz/interactive.py
    """
    if (not HAVE_STREAMLIT) or (_IMPORT_ERROR is not None):
        raise RuntimeError(
            f"Cannot run interactive dashboard: optional dependency missing ({_IMPORT_ERROR}). "
            'Install with: pip install -e ".[viz]"'
        )

    st.set_page_config(page_title="BN-Syn Interactive", page_icon="🧠", layout="wide")

    st.title("🧠 BN-Syn Interactive Demo")
    st.markdown("Real-time exploration of bio-inspired spiking neural networks")

    # Sidebar: parameters
    st.sidebar.header("Network Parameters")
    N = st.sidebar.slider("Network size", 10, 500, 100, help="Number of neurons")
    duration_ms = st.sidebar.slider(
        "Duration (ms)", 100, 5000, 1000, step=100, help="Simulation duration"
    )
    dt_ms = st.sidebar.select_slider(
        "Timestep (ms)", options=[0.01, 0.05, 0.1, 0.5], value=0.1, help="Integration timestep"
    )
    seed = st.sidebar.number_input(
        "Random seed", min_value=0, max_value=10000, value=42, help="Reproducibility seed"
    )

    # Run button
    if st.sidebar.button("▶️ Run Simulation", type="primary"):
        with st.spinner("Running simulation..."):
            # Import here to keep startup fast
            from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
            from bnsyn.rng import seed_all
            from bnsyn.sim.network import Network, NetworkParams

            # Run simulation
            pack = seed_all(seed)
            net = Network(
                NetworkParams(N=N),
                AdExParams(),
                SynapseParams(),
                CriticalityParams(),
                dt_ms=dt_ms,
                rng=pack.np_rng,
            )

            steps = int(duration_ms / dt_ms)
            spike_trains = []
            voltage_history = []
            metrics_history = []

            progress_bar = st.sidebar.progress(0)
            for i in range(steps):
                metrics = net.step()

                # Record spikes
                spikes = np.where(metrics.get("spikes", np.zeros(N, dtype=bool)))[0]
                spike_trains.append((i * dt_ms, spikes))

                # Record sample voltages (first 10 neurons)
                voltage_history.append(net.state.V_mV[:10].copy())

                # Record metrics
                metrics_history.append(metrics)

                # Update progress
                if i % max(1, steps // 100) == 0:
                    progress_bar.progress((i + 1) / steps)

            progress_bar.empty()

        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Raster Plot", "⚡ Voltage Traces", "📈 Firing Rates", "🎯 Population Stats"]
        )

        with tab1:
            st.subheader("Spike Raster Plot")
            fig = create_raster_plot(spike_trains, N, duration_ms)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Voltage Traces (First 10 Neurons)")
            fig = create_voltage_plot(voltage_history, dt_ms)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Population Firing Rate")
            fig = create_firing_rate_plot(metrics_history, dt_ms)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("Population Statistics")
            fig = create_stats_plot(metrics_history, dt_ms)
            st.plotly_chart(fig, use_container_width=True)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mean_rate = np.mean([m.get("spike_rate_hz", 0) for m in metrics_history])
                st.metric("Mean Firing Rate", f"{mean_rate:.2f} Hz")
            with col2:
                mean_sigma = np.mean([m.get("sigma", 0) for m in metrics_history])
                st.metric("Mean Sigma", f"{mean_sigma:.3f}")
            with col3:
                mean_V = np.mean([m.get("V_mean_mV", -60) for m in metrics_history])
                st.metric("Mean Voltage", f"{mean_V:.1f} mV")
            with col4:
                total_spikes = sum(
                    np.sum(m.get("spikes", np.zeros(N, dtype=bool))) for m in metrics_history
                )
                st.metric("Total Spikes", f"{int(total_spikes)}")

    else:
        st.info("👈 Configure parameters in the sidebar and click 'Run Simulation'")


def create_raster_plot(
    spike_trains: list[tuple[float, np.ndarray]], N: int, duration_ms: float
) -> go.Figure:
    """Create interactive raster plot of spike times.

    Parameters
    ----------
    spike_trains : list[tuple[float, np.ndarray]]
        List of (time_ms, neuron_ids) tuples
    N : int
        Number of neurons
    duration_ms : float
        Simulation duration

    Returns
    -------
    go.Figure
        Plotly figure

    Raises
    ------
    RuntimeError
        If optional visualization dependencies are not installed.
    """
    if (not HAVE_STREAMLIT) or (_IMPORT_ERROR is not None):
        raise RuntimeError(
            f"Cannot create plot: optional dependency missing ({_IMPORT_ERROR}). "
            'Install with: pip install -e ".[viz]"'
        )

    times = []
    neurons = []
    for t, spikes in spike_trains:
        for neuron_id in spikes:
            times.append(t)
            neurons.append(neuron_id)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=neurons,
            mode="markers",
            marker=dict(size=2, color="black"),
            name="Spikes",
        )
    )
    fig.update_layout(
        xaxis_title="Time (ms)",
        yaxis_title="Neuron ID",
        yaxis=dict(range=[-1, N]),
        height=400,
        showlegend=False,
    )
    return fig


def create_voltage_plot(voltage_history: list[np.ndarray], dt_ms: float) -> go.Figure:
    """Create voltage trace plot for multiple neurons.

    Parameters
    ----------
    voltage_history : list[np.ndarray]
        History of voltage values [steps, neurons]
    dt_ms : float
        Timestep

    Returns
    -------
    go.Figure
        Plotly figure

    Raises
    ------
    RuntimeError
        If optional visualization dependencies are not installed.
    """
    if (not HAVE_STREAMLIT) or (_IMPORT_ERROR is not None):
        raise RuntimeError(
            f"Cannot create plot: optional dependency missing ({_IMPORT_ERROR}). "
            'Install with: pip install -e ".[viz]"'
        )

    voltage_array = np.array(voltage_history)
    times = np.arange(len(voltage_history)) * dt_ms

    fig = go.Figure()
    for i in range(voltage_array.shape[1]):
        fig.add_trace(
            go.Scatter(
                x=times,
                y=voltage_array[:, i],
                mode="lines",
                name=f"Neuron {i}",
                line=dict(width=1),
            )
        )

    fig.update_layout(
        xaxis_title="Time (ms)",
        yaxis_title="Voltage (mV)",
        height=400,
        hovermode="x unified",
    )
    return fig


def create_firing_rate_plot(metrics_history: list[dict[str, Any]], dt_ms: float) -> go.Figure:
    """Create population firing rate plot.

    Parameters
    ----------
    metrics_history : list[dict]
        History of network metrics
    dt_ms : float
        Timestep

    Returns
    -------
    go.Figure
        Plotly figure

    Raises
    ------
    RuntimeError
        If optional visualization dependencies are not installed.
    """
    if (not HAVE_STREAMLIT) or (_IMPORT_ERROR is not None):
        raise RuntimeError(
            f"Cannot create plot: optional dependency missing ({_IMPORT_ERROR}). "
            'Install with: pip install -e ".[viz]"'
        )

    times = np.arange(len(metrics_history)) * dt_ms
    rates = [m.get("spike_rate_hz", 0) for m in metrics_history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=rates, mode="lines", name="Firing Rate", fill="tozeroy"))

    fig.update_layout(
        xaxis_title="Time (ms)",
        yaxis_title="Firing Rate (Hz)",
        height=400,
    )
    return fig


def create_stats_plot(metrics_history: list[dict[str, Any]], dt_ms: float) -> go.Figure:
    """Create multi-panel statistics plot.

    Parameters
    ----------
    metrics_history : list[dict]
        History of network metrics
    dt_ms : float
        Timestep

    Returns
    -------
    go.Figure
        Plotly figure with subplots

    Raises
    ------
    RuntimeError
        If optional visualization dependencies are not installed.
    """
    if (not HAVE_STREAMLIT) or (_IMPORT_ERROR is not None):
        raise RuntimeError(
            f"Cannot create plot: optional dependency missing ({_IMPORT_ERROR}). "
            'Install with: pip install -e ".[viz]"'
        )

    from plotly.subplots import make_subplots

    times = np.arange(len(metrics_history)) * dt_ms
    sigmas = [m.get("sigma", 0) for m in metrics_history]
    voltages = [m.get("V_mean_mV", -60) for m in metrics_history]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Criticality (Sigma)", "Mean Voltage"),
    )

    # Sigma
    fig.add_trace(
        go.Scatter(x=times, y=sigmas, mode="lines", name="Sigma", line=dict(color="blue")),
        row=1,
        col=1,
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)

    # Voltage
    fig.add_trace(
        go.Scatter(x=times, y=voltages, mode="lines", name="V_mean", line=dict(color="orange")),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text="Time (ms)", row=1, col=1)
    fig.update_xaxes(title_text="Time (ms)", row=1, col=2)
    fig.update_yaxes(title_text="Sigma", row=1, col=1)
    fig.update_yaxes(title_text="Voltage (mV)", row=1, col=2)

    fig.update_layout(height=400, showlegend=False)
    return fig


if __name__ == "__main__":
    main()
