from __future__ import annotations

from pathlib import Path


def test_readme_contains_claim_boundaries() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "## Interpretation and claim boundaries" in readme
    assert "Not supported from this proof command alone" in readme
    assert "biological equivalence" in readme
    assert "consciousness" in readme
    assert readme.index("consciousness") > readme.index("Not supported")
    assert "AGI-level capability" in readme


def test_canonical_proof_contains_interpretation_limits() -> None:
    doc = Path("docs/CANONICAL_PROOF.md").read_text(encoding="utf-8")
    assert "## Interpretation layer and limits" in doc
    assert "Directly measured signals" in doc
    assert "Out of scope / unsupported claims" in doc
