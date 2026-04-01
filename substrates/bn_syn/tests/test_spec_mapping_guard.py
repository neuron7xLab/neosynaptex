"""Guard checks that spec references exist for invariant identifiers."""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_tla_spec_contains_invariant_ids() -> None:
    tla_text = _read("specs/tla/BNsyn.tla")
    for token in ("INV-1", "INV-2", "INV-3", "GainClamp", "TemperatureBounds", "GateBounds"):
        assert token in tla_text, f"Missing TLA+ identifier: {token}"


def test_vcg_spec_contains_invariant_ids() -> None:
    vcg_text = _read("docs/VCG.md")
    for token in ("I1", "I2", "I3", "I4", "A1", "A2", "A3", "A4"):
        assert token in vcg_text, f"Missing VCG identifier: {token}"
