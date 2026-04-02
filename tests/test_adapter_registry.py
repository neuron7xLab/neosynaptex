"""10 tests for AdapterRegistry — runtime DomainAdapter contract validation."""

import pytest

from core.adapter_registry import AdapterRegistry
from neosynaptex import MockBnSynAdapter, MockMarketAdapter, MockMfnAdapter, MockPsycheCoreAdapter


class _BrokenNoTopo:
    @property
    def domain(self) -> str:
        return "broken"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def thermo_cost(self) -> float:
        return 1.0


class _BrokenBadState:
    @property
    def domain(self) -> str:
        return "badstate"

    @property
    def state_keys(self) -> list[str]:
        return ["a", "b"]

    def state(self) -> dict[str, float]:
        return {"a": "not_a_float", "b": 1.0}  # type: ignore[dict-item]

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


class _TooManyKeys:
    @property
    def domain(self) -> str:
        return "toomany"

    @property
    def state_keys(self) -> list[str]:
        return ["a", "b", "c", "d", "e"]

    def state(self) -> dict[str, float]:
        return {k: 1.0 for k in self.state_keys}

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


class _NegativeTopo:
    @property
    def domain(self) -> str:
        return "negtopo"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def topo(self) -> float:
        return -5.0

    def thermo_cost(self) -> float:
        return 1.0


class _CrashingAdapter:
    @property
    def domain(self) -> str:
        return "crasher"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        raise RuntimeError("adapter crashed")

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


def test_register_valid_adapter():
    reg = AdapterRegistry()
    reg.register(MockBnSynAdapter())
    assert len(reg) == 1
    assert "spike" in reg.domains


def test_register_multiple_adapters():
    reg = AdapterRegistry()
    reg.register(MockBnSynAdapter())
    reg.register(MockMfnAdapter())
    reg.register(MockPsycheCoreAdapter())
    reg.register(MockMarketAdapter())
    assert len(reg) == 4


def test_register_duplicate_raises():
    reg = AdapterRegistry()
    reg.register(MockBnSynAdapter())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(MockBnSynAdapter())


def test_register_broken_protocol_raises():
    reg = AdapterRegistry()
    with pytest.raises(TypeError, match="DomainAdapter Protocol"):
        reg.register(_BrokenNoTopo())


def test_validate_valid_adapter():
    reg = AdapterRegistry()
    result = reg.validate(MockBnSynAdapter())
    assert result.valid
    assert len(result.errors) == 0


def test_validate_bad_state_type():
    reg = AdapterRegistry()
    result = reg.validate(_BrokenBadState())
    assert not result.valid
    assert any("not_a_float" in e or "str" in e for e in result.errors)


def test_validate_too_many_keys():
    reg = AdapterRegistry()
    result = reg.validate(_TooManyKeys())
    assert not result.valid
    assert any("5 keys" in e for e in result.errors)


def test_validate_negative_topo():
    reg = AdapterRegistry()
    result = reg.validate(_NegativeTopo())
    assert not result.valid
    assert any("must be > 0" in e for e in result.errors)


def test_health_alive():
    reg = AdapterRegistry()
    reg.register(MockBnSynAdapter())
    h = reg.health()
    assert h["spike"].alive
    assert h["spike"].domain == "spike"


def test_health_crashing_adapter():
    reg = AdapterRegistry()
    # Force-register crashing adapter bypassing protocol check
    reg._adapters["crasher"] = _CrashingAdapter()
    h = reg.health()
    assert not h["crasher"].alive
    assert h["crasher"].last_error is not None
