"""Tests for the mycelium pre-admission adapter.

Numbered tests:
1.  Adapter has no instance state (``__slots__ == ()``).
2.  ``verdict()`` returns the locked Gate 0 verdict.
3.  ``state()`` exposes ``claim_status`` / ``gate_status`` / ``reasons`` /
    ``non_claims`` as a read-only dict.
4.  ``reasons()`` returns the six canonical reason codes.
5.  Every observable method (``topo``, ``thermo_cost``, ``kappa``,
    ``phase_coherence``, ``order_parameter``, ``metastability``) raises
    ``NotImplementedError`` with the ``BLOCKED_BY_METHOD_DEFINITION``
    refusal reason.
6.  ``compute_verdict`` (mirror of BN-Syn API) is also refused.
7.  Adapter accepts no constructor arguments — there is no admit-data
    path even at instantiation.
8.  Multiple adapter instances return equal verdicts (constant).
9.  Public surface of the adapter module is exactly
    ``MyceliumPreAdmissionAdapter``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from substrates.mycelium_pre_admission_adapter import (  # noqa: E402
    MyceliumPreAdmissionAdapter,
)


# 1
def test_adapter_has_no_instance_state() -> None:
    a = MyceliumPreAdmissionAdapter()
    assert MyceliumPreAdmissionAdapter.__slots__ == ()
    with pytest.raises((AttributeError, TypeError)):
        a.fungal_kappa = 1.0  # type: ignore[attr-defined]


# 2
def test_verdict_is_locked_gate_zero() -> None:
    a = MyceliumPreAdmissionAdapter()
    v = a.verdict()
    assert v.claim_status == "NO_ADMISSIBLE_CLAIM"
    assert v.gate_status == "BLOCKED_BY_METHOD_DEFINITION"


# 3
def test_state_dict_view() -> None:
    a = MyceliumPreAdmissionAdapter()
    s = a.state()
    assert s["claim_status"] == "NO_ADMISSIBLE_CLAIM"
    assert s["gate_status"] == "BLOCKED_BY_METHOD_DEFINITION"
    assert isinstance(s["reasons"], tuple)
    assert isinstance(s["non_claims"], tuple)
    assert len(s["reasons"]) == 6


# 4
def test_reasons_match_canonical_six() -> None:
    a = MyceliumPreAdmissionAdapter()
    expected = (
        "OBSERVABLE_NOT_DEFINED",
        "COUPLING_TOPOLOGY_UNDEFINED",
        "ORDER_PARAMETER_NOT_DERIVABLE",
        "METASTABILITY_SCALAR_NOT_PUBLISHED",
        "REPLAY_DETERMINISM_ABSENT",
        "NULL_DISTRIBUTION_ABSENT",
    )
    assert expected == a.reasons()


# 5
@pytest.mark.parametrize(
    "method_name",
    [
        "topo",
        "thermo_cost",
        "kappa",
        "phase_coherence",
        "order_parameter",
        "metastability",
    ],
)
def test_every_observable_is_refused(method_name: str) -> None:
    a = MyceliumPreAdmissionAdapter()
    method = getattr(a, method_name)
    with pytest.raises(NotImplementedError) as excinfo:
        method()
    assert "BLOCKED_BY_METHOD_DEFINITION" in str(excinfo.value)
    assert "MYCELIUM_GAMMA_GATE_0.md" in str(excinfo.value)


# 6
def test_compute_verdict_is_refused() -> None:
    a = MyceliumPreAdmissionAdapter()
    with pytest.raises(NotImplementedError):
        a.compute_verdict()
    with pytest.raises(NotImplementedError):
        a.compute_verdict({}, provenance_ok=True, determinism_ok=True, gamma_pass=True)


# 7
def test_adapter_takes_no_constructor_arguments() -> None:
    # No accidental admit-data path through __init__
    with pytest.raises(TypeError):
        MyceliumPreAdmissionAdapter("fungal_data")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        MyceliumPreAdmissionAdapter(metrics={"kappa": 1.0})  # type: ignore[call-arg]


# 8
def test_multiple_instances_constant_verdict() -> None:
    a1 = MyceliumPreAdmissionAdapter()
    a2 = MyceliumPreAdmissionAdapter()
    assert a1.verdict() == a2.verdict()


# 9
def test_adapter_module_public_surface() -> None:
    import substrates.mycelium_pre_admission_adapter as mod

    assert set(mod.__all__) == {"MyceliumPreAdmissionAdapter"}


def test_no_gamma_pass_anywhere() -> None:
    """The adapter MUST NOT carry a `gamma_pass` parameter on any path."""
    import substrates.mycelium_pre_admission_adapter as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    # `gamma_pass` may legitimately appear ONLY in the docstring of
    # compute_verdict (which explains why it is absent), so we count
    # occurrences and ensure they are all inside docstrings, not in
    # function signatures.
    import ast

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args + node.args.kwonlyargs:
                assert arg.arg != "gamma_pass", (
                    f"forbidden gamma_pass parameter found in {node.name}"
                )
