from __future__ import annotations

from pathlib import Path


def test_demo_surface_docs_stay_aligned() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    canonical_proof = Path("docs/CANONICAL_PROOF.md").read_text(encoding="utf-8")
    demo_doc = Path("docs/DEMO.md").read_text(encoding="utf-8")

    expected_shared = {
        "bnsyn run --profile canonical --plot --export-proof",
        "product_summary.json",
        "index.html",
        "bnsyn validate-bundle",
    }

    for expected in expected_shared:
        assert expected in readme
        assert expected in canonical_proof
        assert expected in demo_doc

    assert "Demo-completion checklist for this PR" in demo_doc
    assert "The primary human interface is `artifacts/canonical_run/index.html`." in canonical_proof
