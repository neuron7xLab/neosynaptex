"""Tests for the interactive dashboard entrypoint."""

from __future__ import annotations

import sys
from types import ModuleType

import numpy as np
import pytest


class _DummyCtx:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_go = ModuleType("plotly.graph_objects")

    class FakeFigure:
        def __init__(self) -> None:
            self.layout: dict[str, object] = {}

        def add_trace(self, *_: object, **__: object) -> None:
            return None

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


def _install_fake_streamlit(monkeypatch: pytest.MonkeyPatch, run: bool) -> None:
    fake_st = ModuleType("streamlit")
    fake_st.set_page_config = lambda **_: None
    fake_st.title = lambda *_: None
    fake_st.markdown = lambda *_: None
    fake_st.info = lambda *_: None
    fake_st.subheader = lambda *_: None
    fake_st.plotly_chart = lambda *_, **__: None
    fake_st.metric = lambda *_: None
    fake_st.tabs = lambda labels: [_DummyCtx() for _ in labels]
    fake_st.columns = lambda count: [_DummyCtx() for _ in range(count)]

    class _Progress:
        def progress(self, *_: object) -> None:
            return None

        def empty(self) -> None:
            return None

    fake_st.sidebar = ModuleType("streamlit.sidebar")
    fake_st.sidebar.header = lambda *_: None
    fake_st.sidebar.slider = lambda *_, **__: 10
    fake_st.sidebar.select_slider = lambda *_, **__: 0.5
    fake_st.sidebar.number_input = lambda *_, **__: 1
    fake_st.sidebar.button = lambda *_, **__: run
    fake_st.sidebar.progress = lambda *_: _Progress()

    fake_st.spinner = lambda *_: _DummyCtx()

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)


def test_interactive_main_info_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_plotly(monkeypatch)
    _install_fake_streamlit(monkeypatch, run=False)

    import importlib

    module = importlib.reload(__import__("bnsyn.viz.interactive", fromlist=["*"]))
    assert module.HAVE_STREAMLIT
    module.main()


def test_interactive_main_run_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_plotly(monkeypatch)
    _install_fake_streamlit(monkeypatch, run=True)

    import importlib

    module = importlib.reload(__import__("bnsyn.viz.interactive", fromlist=["*"]))
    assert module.HAVE_STREAMLIT

    # Shrink simulation sizes to keep runtime small
    monkeypatch.setattr(module.np, "where", np.where)
    module.main()
