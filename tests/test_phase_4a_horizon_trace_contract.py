"""Phase 4a — Horizon Trace Contract validation.

This test file enforces the structural contract that
``substrates/serotonergic_kuramoto/horizon_trace_contract.yaml``
declares. The 10 numbered tests are the binding ratifiers of:

1.  the contract YAML exists,
2.  ``phase == "4a"``,
3.  ``hidden_core_is_evidence`` is False,
4.  ``boundary_trace_required`` is True,
5.  ``ledger_mutation_allowed`` is False,
6.  ``gamma_promotion_allowed`` is False,
7.  ``topo`` and ``thermo_cost`` exist as observable entries,
8.  every observable has the nine required fields,
9.  ``raw_c`` and ``critical_distance`` exist as coordinate entries,
10. forbidden claims do not appear in either the YAML or the
    Phase 4a protocol document.

The contract is canonical. Production source files (under ``core/``,
``contracts/``, ``evidence/``, ``tools/``, ``analysis/``, ``formal/``)
are also covered by ``tools.audit.claim_overclaim_gate``; this file
covers the Phase 4a-specific frozen claims that the global overclaim
gate does not yet track.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml as _yaml  # type: ignore[import-untyped]

    _HAVE_YAML = True
except ImportError:  # pragma: no cover - PyYAML missing
    _HAVE_YAML = False

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONTRACT_PATH = _REPO_ROOT / "substrates" / "serotonergic_kuramoto" / "horizon_trace_contract.yaml"
_PROTOCOL_PATH = _REPO_ROOT / "docs" / "audit" / "PHASE_4A_HORIZON_TRACE_PROTOCOL.md"

_REQUIRED_OBSERVABLE_FIELDS: tuple[str, ...] = (
    "status",
    "source_path",
    "code_symbol",
    "definition",
    "units_or_scale",
    "boundary_meaning",
    "expected_null_behavior",
    "failure_modes",
    "falsifiers",
)

_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "γ≈1 validated",
    "substrate validated",
    "Phase 4 fixed the hypothesis",
    "old γ preserved",
    "Theil-Sen killed the hypothesis",
)


def _load_contract() -> dict[str, object]:
    """Load the YAML contract.

    Uses PyYAML when available. PyYAML is a transitive dependency of
    the project (pinned via the dev environment), so the assertion is
    safe; the explicit ``importorskip`` keeps the failure mode
    informative if the dev environment ever changes.
    """
    if not _HAVE_YAML:
        pytest.importorskip("yaml")
    with _CONTRACT_PATH.open(encoding="utf-8") as fh:
        loaded = _yaml.safe_load(fh)
    assert isinstance(loaded, dict), (
        f"contract YAML must parse to a top-level mapping, got {type(loaded).__name__}"
    )
    return loaded


# 1
def test_contract_yaml_exists() -> None:
    assert _CONTRACT_PATH.is_file(), f"horizon_trace_contract.yaml not found at {_CONTRACT_PATH}"


# 2
def test_phase_is_4a() -> None:
    contract = _load_contract()
    assert contract.get("phase") == "4a", (
        f"contract.phase must be exactly '4a'; got {contract.get('phase')!r}"
    )


# 3
def test_hidden_core_is_not_evidence() -> None:
    contract = _load_contract()
    cb = contract.get("claim_boundary")
    assert isinstance(cb, dict), "claim_boundary must be a mapping"
    assert cb.get("hidden_core_is_evidence") is False, (
        "claim_boundary.hidden_core_is_evidence must be exactly False; "
        f"got {cb.get('hidden_core_is_evidence')!r}"
    )


# 4
def test_boundary_trace_required() -> None:
    contract = _load_contract()
    cb = contract.get("claim_boundary")
    assert isinstance(cb, dict)
    assert cb.get("boundary_trace_required") is True, (
        "claim_boundary.boundary_trace_required must be exactly True; "
        f"got {cb.get('boundary_trace_required')!r}"
    )


# 5
def test_ledger_mutation_not_allowed() -> None:
    contract = _load_contract()
    cb = contract.get("claim_boundary")
    assert isinstance(cb, dict)
    assert cb.get("ledger_mutation_allowed") is False, (
        "claim_boundary.ledger_mutation_allowed must be exactly False; "
        f"got {cb.get('ledger_mutation_allowed')!r}"
    )


# 6
def test_gamma_promotion_not_allowed() -> None:
    contract = _load_contract()
    cb = contract.get("claim_boundary")
    assert isinstance(cb, dict)
    assert cb.get("gamma_promotion_allowed") is False, (
        "claim_boundary.gamma_promotion_allowed must be exactly False; "
        f"got {cb.get('gamma_promotion_allowed')!r}"
    )


# 7
def test_topo_and_thermo_cost_observables_exist() -> None:
    contract = _load_contract()
    obs = contract.get("observables")
    assert isinstance(obs, dict), "contract.observables must be a mapping"
    assert "topo" in obs, "observable 'topo' missing from contract"
    assert "thermo_cost" in obs, "observable 'thermo_cost' missing from contract"


# 8
@pytest.mark.parametrize("observable_name", ["topo", "thermo_cost"])
def test_observables_have_all_required_fields(observable_name: str) -> None:
    contract = _load_contract()
    obs = contract.get("observables")
    assert isinstance(obs, dict)
    entry = obs.get(observable_name)
    assert isinstance(entry, dict), f"observable {observable_name!r} must be a mapping"
    missing = [f for f in _REQUIRED_OBSERVABLE_FIELDS if f not in entry]
    assert not missing, f"observable {observable_name!r} missing required fields: {missing}"


# 9
def test_coordinates_raw_c_and_critical_distance_exist() -> None:
    contract = _load_contract()
    coords = contract.get("coordinates")
    assert isinstance(coords, dict), "contract.coordinates must be a mapping"
    assert "raw_c" in coords, "coordinate 'raw_c' missing"
    assert "critical_distance" in coords, "coordinate 'critical_distance' missing"


# 10
@pytest.mark.parametrize("path", [_CONTRACT_PATH, _PROTOCOL_PATH])
def test_forbidden_claims_do_not_appear_positively(path: Path) -> None:
    """Forbidden claims must not appear as positive assertions in either
    the contract or the protocol document.

    Both files are *required* to enumerate the forbidden phrases in
    ``forbidden_claims`` lists or in disavowal sections — that is the
    whole point of the contract. The check uses a rolling-window
    disavowal context so a forbidden phrase appearing as a YAML list
    item under ``forbidden_claims:`` (or as a markdown bullet under a
    "must not claim" preamble) is admitted, while a positive
    assertion on its own line is rejected.
    """
    text = path.read_text(encoding="utf-8")
    disavowal_tokens = (
        "forbidden",
        "rejected",
        "must not",
        "do not",
        "does not",
        "is not",
        "never",
        "no auto-promotion",
        "anti-",
        "disavow",
        # YAML key whose entire purpose is to enumerate forbidden phrases.
        "forbidden_claims",
        "anti-cartesian",
    )
    # ``window`` lines back from a phrase match: if any of them carries
    # a disavowal token, the listing is structural, not assertive.
    window = 12

    lines = text.splitlines()
    disavowal_at: set[int] = {
        idx
        for idx, line in enumerate(lines)
        if any(tok in line.lower() for tok in disavowal_tokens)
    }

    violations: list[str] = []
    for n, line in enumerate(lines, start=1):
        line_lower = line.lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase.lower() not in line_lower:
                continue
            # Local disavowal: same line carries a disavowal token.
            if any(tok in line_lower for tok in disavowal_tokens):
                continue
            # Rolling-window disavowal: any of the previous `window`
            # lines carries a disavowal token.
            idx0 = n - 1
            if any((idx0 - k) in disavowal_at for k in range(1, window + 1)):
                continue
            violations.append(f"{path.name}:{n}: {phrase!r} → {line.strip()[:160]}")
    assert not violations, "positive forbidden-claim use detected:\n" + "\n".join(violations)
