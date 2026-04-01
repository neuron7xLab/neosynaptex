"""Tests for the optional JAX backend."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from types import ModuleType

import numpy as np
import pytest


def _load_module_with_jnp(fake_jnp: ModuleType) -> ModuleType:
    module_name = "bnsyn.production.jax_backend"
    sys.modules["jax"] = ModuleType("jax")
    sys.modules["jax.numpy"] = fake_jnp
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def _import_module_without_jax(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module_name = "bnsyn.production.jax_backend"
    original_find_spec = importlib.util.find_spec
    original_import = importlib.import_module

    def fake_find_spec(name: str, *args: object, **kwargs: object) -> object | None:
        if name == "jax.numpy":
            return None
        return original_find_spec(name, *args, **kwargs)

    def fake_import(name: str, *args: object, **kwargs: object) -> ModuleType:
        if name == "jax.numpy":
            raise ImportError("no jax")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import)
    sys.modules.pop(module_name, None)
    sys.modules.pop("jax.numpy", None)
    sys.modules.pop("jax", None)
    return importlib.import_module(module_name)


def _import_module_with_find_spec_error(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module_name = "bnsyn.production.jax_backend"
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *args: object, **kwargs: object) -> object | None:
        if name == "jax.numpy":
            raise ValueError("invalid spec")
        return original_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_jax_backend_import_safe_without_jax(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _import_module_without_jax(monkeypatch)
    assert module.JAX_AVAILABLE is False

    V = np.array([-55.0, -40.0], dtype=float)
    w = np.array([0.0, 0.0], dtype=float)
    input_current = np.array([0.0, 500.0], dtype=float)

    with pytest.raises(RuntimeError, match="JAX is required.*pip install jax jaxlib"):
        module.adex_step_jax(
            V,
            w,
            input_current,
            C=200.0,
            gL=10.0,
            EL=-65.0,
            VT=-50.0,
            DeltaT=2.0,
            tau_w=100.0,
            a=2.0,
            b=50.0,
            V_reset=-65.0,
            V_spike=-40.0,
            dt=0.1,
        )


def test_adex_step_jax_with_numpy_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_jnp = ModuleType("jax.numpy")
    fake_jnp.exp = np.exp
    fake_jnp.where = np.where

    module = _load_module_with_jnp(fake_jnp)

    V = np.array([-55.0, -40.0], dtype=float)
    w = np.array([0.0, 0.0], dtype=float)
    input_current = np.array([0.0, 500.0], dtype=float)

    V_new, w_new, spikes = module.adex_step_jax(
        V,
        w,
        input_current,
        C=200.0,
        gL=10.0,
        EL=-65.0,
        VT=-50.0,
        DeltaT=2.0,
        tau_w=100.0,
        a=2.0,
        b=50.0,
        V_reset=-65.0,
        V_spike=-40.0,
        dt=0.1,
    )

    assert V_new.shape == V.shape
    assert w_new.shape == w.shape
    assert spikes.shape == V.shape
    assert spikes.dtype == bool
    assert V_new[1] == -65.0
    assert w_new[1] > w[1]

    sys.modules.pop("bnsyn.production.jax_backend", None)
    sys.modules.pop("jax.numpy", None)
    sys.modules.pop("jax", None)


def test_jax_backend_propagates_non_import_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "bnsyn.production.jax_backend"
    module = importlib.import_module(module_name)
    original_import = importlib.import_module

    def boom(name: str, *args: object, **kwargs: object) -> ModuleType:
        if name == "jax.numpy":
            raise ValueError("unexpected failure")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", boom)

    with pytest.raises(ValueError, match="unexpected failure"):
        module.adex_step_jax(
            np.array([-55.0], dtype=float),
            np.array([0.0], dtype=float),
            np.array([0.0], dtype=float),
            C=200.0,
            gL=10.0,
            EL=-65.0,
            VT=-50.0,
            DeltaT=2.0,
            tau_w=100.0,
            a=2.0,
            b=50.0,
            V_reset=-65.0,
            V_spike=-40.0,
            dt=0.1,
        )

    sys.modules.pop(module_name, None)


def test_jax_backend_handles_find_spec_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _import_module_with_find_spec_error(monkeypatch)
    assert module.JAX_AVAILABLE is False
