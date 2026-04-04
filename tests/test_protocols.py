"""Tests for core.protocols — DomainAdapter runtime_checkable Protocol."""

import pytest

from core.protocols import DomainAdapter


class ValidAdapter:
    @property
    def domain(self) -> str:
        return "test"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


class MissingTopo:
    @property
    def domain(self) -> str:
        return "bad"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def thermo_cost(self) -> float:
        return 1.0


def test_valid_adapter_passes_isinstance():
    assert isinstance(ValidAdapter(), DomainAdapter)


def test_missing_method_fails_isinstance():
    assert not isinstance(MissingTopo(), DomainAdapter)


def test_plain_dict_is_not_adapter():
    assert not isinstance({"domain": "fake"}, DomainAdapter)


def test_protocol_works_with_mock_adapters():
    from neosynaptex import MockBnSynAdapter, MockMfnAdapter

    assert isinstance(MockBnSynAdapter(), DomainAdapter)
    assert isinstance(MockMfnAdapter(), DomainAdapter)
