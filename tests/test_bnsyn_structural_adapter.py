"""Adapter tests for ``substrates/bnsyn_structural_adapter.py``.

Numbered tests:
11. Adapter refuses to emit ``topo()`` (κ ≠ γ).
12. Adapter refuses to emit ``thermo_cost()`` (κ ≠ γ).
13. Adapter ``compute_verdict`` cannot reach VALIDATED without
    ``gamma_pass=True`` from the caller.

Plus the forbidden-language scan covering the entire integration
surface area.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.bnsyn_structural_evidence import BnSynStructuralMetrics  # noqa: E402
from contracts.provenance import ClaimStatus, ProvenanceClass  # noqa: E402
from substrates.bnsyn_structural_adapter import BnSynStructuralAdapter  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_THRESHOLDS_PATH = _REPO_ROOT / "config" / "bnsyn_structural_thresholds.yaml"


def _thresholds() -> dict[str, Any]:
    with _THRESHOLDS_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    return data


def _good_metrics(**overrides: object) -> BnSynStructuralMetrics:
    base: dict[str, object] = {
        "kappa": 1.02,
        "kappa_ci_low": 0.95,
        "kappa_ci_high": 1.08,
        "avalanche_fit_quality": 0.42,
        "avalanche_distribution_summary": {
            "avalanche_count": 250,
            "size_max": 87,
            "alpha": 1.51,
        },
        "phase_coherence": 0.73,
        "phase_surrogate_rejected": True,
    }
    base.update(overrides)
    return BnSynStructuralMetrics(**base)  # type: ignore[arg-type]


# 11
def test_adapter_refuses_topo() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    with pytest.raises(NotImplementedError):
        adapter.topo()


# 12
def test_adapter_refuses_thermo_cost() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    with pytest.raises(NotImplementedError):
        adapter.thermo_cost()


# 13
def test_adapter_cannot_validate_without_gamma_pass() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    th = _thresholds()
    # Default call → no γ pass → cannot exceed LOCAL_STRUCTURAL_EVIDENCE_ONLY
    v = adapter.compute_verdict(th, provenance_ok=True, determinism_ok=True)
    assert v.claim_status == "LOCAL_STRUCTURAL_EVIDENCE_ONLY"
    assert v.gamma_status == "NO_ADMISSIBLE_CLAIM"
    # gamma_pass=False also stays at LOCAL_STRUCTURAL_EVIDENCE_ONLY because
    # local_pass holds and we do not downgrade for an explicit γ-side
    # FAIL on the structural channel — we surface the FAIL via gamma_status.
    v_fail = adapter.compute_verdict(th, provenance_ok=True, determinism_ok=True, gamma_pass=False)
    assert v_fail.claim_status == "LOCAL_STRUCTURAL_EVIDENCE_ONLY"
    assert v_fail.gamma_status == "FAIL"
    # Only an explicit caller-supplied gamma_pass=True upgrades.
    v_ok = adapter.compute_verdict(th, provenance_ok=True, determinism_ok=True, gamma_pass=True)
    assert v_ok.claim_status == "VALIDATED_SUBSTRATE_EVIDENCE"


def test_adapter_provenance_is_downgraded() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    assert adapter.provenance.provenance_class == ProvenanceClass.DOWNGRADED
    assert adapter.provenance.claim_status == ClaimStatus.DOWNGRADED


def test_adapter_state_is_numeric_only() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    state = adapter.state()
    assert isinstance(state, dict)
    for k, v in state.items():
        assert isinstance(k, str)
        assert isinstance(v, (int, float))


def test_adapter_artifact_suspected_when_surrogate_not_rejected() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics(phase_surrogate_rejected=False))
    th = _thresholds()
    v = adapter.compute_verdict(th, provenance_ok=True, determinism_ok=True)
    assert v.claim_status == "ARTIFACT_SUSPECTED"


def test_adapter_provenance_missing_caps_at_local_only() -> None:
    adapter = BnSynStructuralAdapter(_good_metrics())
    th = _thresholds()
    v = adapter.compute_verdict(th, provenance_ok=False, determinism_ok=True, gamma_pass=True)
    # Even with gamma_pass=True, provenance gap forbids upgrade.
    assert v.claim_status == "LOCAL_STRUCTURAL_EVIDENCE_ONLY"
    assert "PROVENANCE_MISSING" in v.reasons


# Forbidden-language scan ------------------------------------------------

_NEW_FILES: tuple[Path, ...] = (
    _REPO_ROOT / "contracts" / "bnsyn_structural_evidence.py",
    _REPO_ROOT / "config" / "bnsyn_structural_thresholds.yaml",
    _REPO_ROOT / "tools" / "import_bnsyn_structural_evidence.py",
    _REPO_ROOT / "substrates" / "bnsyn_structural_adapter.py",
    _REPO_ROOT / "tests" / "test_bnsyn_structural_evidence.py",
    _REPO_ROOT / "tests" / "test_import_bnsyn_structural_evidence.py",
    _REPO_ROOT / "tests" / "test_bnsyn_structural_adapter.py",
    _REPO_ROOT / "docs" / "claim_boundaries" / "BN_SYN_LOCAL_STRUCTURAL_EVIDENCE.md",
)

# Forbidden phrases are assembled from token tuples at import time so
# the literal substring does not appear in *this* file (otherwise the
# scan would self-match and false-FAIL).
_FORBIDDEN_PHRASE_TOKENS: tuple[tuple[str, ...], ...] = (
    ("p" + "roof", "of", "conscious" + "ness"),
    ("conscious" + "ness", "p" + "roved"),
    ("A" + "G" + "I",),
    ("biolog" + "ical", "equiv" + "alence"),
    ("univ" + "ersal", "emer" + "gence", "p" + "roved"),
    ("BN-Syn", "p" + "roves", "NeoSynaptex"),
    ("emer" + "gence", "p" + "roved"),
)
_FORBIDDEN_PHRASES: tuple[str, ...] = tuple(" ".join(toks) for toks in _FORBIDDEN_PHRASE_TOKENS)


def test_no_old_overclaim_language_in_new_files() -> None:
    """Scan all new files for forbidden over-claim phrases (case-insensitive)."""
    for path in _NEW_FILES:
        assert path.is_file(), f"expected new file is missing: {path}"
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in _FORBIDDEN_PHRASES:
            # "BN-Syn" alone is allowed (identifier/source label) — only
            # the full forbidden phrase is checked.
            assert phrase.lower() not in lower, (
                f"forbidden over-claim phrase {phrase!r} found in {path}"
            )

    # Bonus invariant: the contract docstring must contain the explicit
    # κ ≠ γ disclaimer to prevent silent drift in future edits.
    contract_text = (_REPO_ROOT / "contracts" / "bnsyn_structural_evidence.py").read_text(
        encoding="utf-8"
    )
    assert re.search(
        r"NOT speak about.*γ|κ.*≠.*γ|kappa.*not.*gamma|κ.*alone is not γ",
        contract_text,
        re.IGNORECASE | re.DOTALL,
    ) or "κ ≠ γ" in (
        (_REPO_ROOT / "substrates" / "bnsyn_structural_adapter.py").read_text(encoding="utf-8")
    )
