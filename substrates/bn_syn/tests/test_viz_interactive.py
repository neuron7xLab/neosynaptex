"""Tests for interactive visualization helpers."""

from __future__ import annotations

import sys
from types import ModuleType

import numpy as np
import pytest


def _install_fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_st = ModuleType("streamlit")
    fake_st.set_page_config = lambda **_: None
    fake_st.title = lambda *_: None
    fake_st.markdown = lambda *_: None
    fake_st.info = lambda *_: None

    fake_st.sidebar = ModuleType("streamlit.sidebar")
    fake_st.sidebar.header = lambda *_: None
    fake_st.sidebar.slider = lambda *_, **__: 10
    fake_st.sidebar.select_slider = lambda *_, **__: 0.1
    fake_st.sidebar.number_input = lambda *_, **__: 1

    class _DummySpinner:
        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_st.spinner = lambda *_: _DummySpinner()
    fake_st.sidebar.button = lambda *_, **__: False

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_go = ModuleType("plotly.graph_objects")

    class FakeFigure:
        def __init__(self) -> None:
            self.traces: list[tuple[str, dict]] = []
            self.layout: dict[str, object] = {}

        def add_trace(self, trace: object, **kwargs: object) -> None:
            self.traces.append(("trace", {"trace": trace, "kwargs": kwargs}))

        def update_layout(self, **kwargs: object) -> None:
            self.layout.update(kwargs)

        def update_xaxes(self, **_: object) -> None:
            return None

        def update_yaxes(self, **_: object) -> None:
            return None

        def add_hline(self, **_: object) -> None:
            return None

    class FakeScatter:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    fake_go.Figure = FakeFigure
    fake_go.Scatter = FakeScatter

    fake_plotly = ModuleType("plotly")
    fake_plotly.graph_objects = fake_go

    fake_subplots = ModuleType("plotly.subplots")

    def make_subplots(*_: object, **__: object) -> FakeFigure:
        return FakeFigure()

    fake_subplots.make_subplots = make_subplots

    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)
    monkeypatch.setitem(sys.modules, "plotly.subplots", fake_subplots)


def test_interactive_helpers_raise_without_streamlit() -> None:
    import bnsyn.viz.interactive as interactive

    if not interactive.HAVE_STREAMLIT:
        with pytest.raises(RuntimeError, match="optional dependency"):
            interactive.create_raster_plot([], 1, 1.0)


def test_interactive_helpers_with_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_plotly(monkeypatch)
    _install_fake_streamlit(monkeypatch)

    import importlib

    module = importlib.reload(
        sys.modules.get(
            "bnsyn.viz.interactive",
            __import__("bnsyn.viz.interactive", fromlist=["*"]),
        )
    )
    assert module.HAVE_STREAMLIT

    spike_trains = [(0.0, np.array([0, 1], dtype=int))]
    raster = module.create_raster_plot(spike_trains, 2, 1.0)
    assert raster.layout["xaxis_title"] == "Time (ms)"
    assert raster.layout["yaxis_title"] == "Neuron ID"

    voltage = module.create_voltage_plot([np.array([0.0, 1.0])], 0.1)
    assert voltage.layout["xaxis_title"] == "Time (ms)"

    metrics = [{"spike_rate_hz": 1.5, "sigma": 1.1, "V_mean_mV": -60.0}]
    firing = module.create_firing_rate_plot(metrics, 0.1)
    assert firing.layout["yaxis_title"] == "Firing Rate (Hz)"

    stats = module.create_stats_plot(metrics, 0.1)
    assert stats.layout["height"] == 400
