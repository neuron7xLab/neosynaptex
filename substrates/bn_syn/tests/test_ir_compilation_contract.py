from __future__ import annotations

from scripts.ca_cognitive_ir_compile import compile_ir


def test_ir_compilation_contract() -> None:
    payload = compile_ir()
    assert "Claims" in payload
    assert "Invariants" in payload
