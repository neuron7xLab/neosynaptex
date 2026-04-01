"""CLM-0011 Enforcement: Bibliographic Traceability for NORMATIVE Claims.

This test enforces that all NORMATIVE claims in claims.yml have complete
evidence traceability, per CLM-0011 (FAIR principles).

Required fields for normative claims:
- bibkey: Reference key from bibliography
- locator: Specific location in source (page, section, etc.)
- verification_paths: Test files that validate the claim
- status: Current lifecycle status

Marker: @pytest.mark.smoke (BLOCKING - runs on every PR)
Runtime: <1 second
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.smoke
def test_clm_0011_normative_claims_have_complete_evidence() -> None:
    """Enforce CLM-0011: All normative claims must have complete evidence.

    This is a BLOCKING test that ensures bibliographic traceability.
    Failure indicates incomplete claim documentation.
    """
    claims_file = Path("claims/claims.yml")
    assert claims_file.exists(), "claims/claims.yml not found"

    with claims_file.open() as f:
        claims_data = yaml.safe_load(f)

    claims = claims_data.get("claims", [])
    assert claims, "No claims found in claims.yml"

    # Filter to normative claims only
    normative_claims = [c for c in claims if c.get("normative")]

    violations = []
    for claim in normative_claims:
        missing_fields = []

        # Check required fields
        if not claim.get("bibkey"):
            missing_fields.append("bibkey")
        if not claim.get("locator"):
            missing_fields.append("locator")
        if not claim.get("verification_paths") or not claim["verification_paths"]:
            missing_fields.append("verification_paths")
        if not claim.get("status"):
            missing_fields.append("status")

        if missing_fields:
            violations.append(
                {
                    "claim_id": claim.get("id", "UNKNOWN"),
                    "missing_fields": missing_fields,
                }
            )

    # Assert no violations
    assert not violations, (
        f"CLM-0011 violations detected: {len(violations)} normative claim(s) "
        f"missing required evidence fields.\n"
        f"Violations: {violations}\n\n"
        f"Required fields for normative claims:\n"
        f"  - bibkey (reference key)\n"
        f"  - locator (page/section in source)\n"
        f"  - verification_paths (test files)\n"
        f"  - status (claim lifecycle state)\n"
    )


@pytest.mark.smoke
def test_claims_file_structure() -> None:
    """Validate basic structure of claims.yml file.

    Ensures the file exists, is valid YAML, and has expected top-level keys.
    """
    claims_file = Path("claims/claims.yml")
    assert claims_file.exists(), "claims/claims.yml not found"

    with claims_file.open() as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "claims.yml must be a dictionary"
    assert "claims" in data, "claims.yml must have 'claims' key"
    assert isinstance(data["claims"], list), "'claims' must be a list"
    assert len(data["claims"]) > 0, "claims list must not be empty"


@pytest.mark.smoke
def test_all_claims_have_required_basic_fields() -> None:
    """Ensure all claims (normative or not) have basic required fields.

    Required fields for all claims:
    - id: Unique claim identifier
    - statement: The claim text
    - status: Lifecycle status
    """
    claims_file = Path("claims/claims.yml")
    with claims_file.open() as f:
        claims_data = yaml.safe_load(f)

    claims = claims_data.get("claims", [])

    for claim in claims:
        claim_id = claim.get("id", "UNKNOWN")

        # Every claim must have these basics
        assert claim.get("id"), f"Claim missing 'id' field: {claim}"
        assert claim.get("statement"), f"Claim {claim_id} missing 'statement' field"
        assert claim.get("status"), f"Claim {claim_id} missing 'status' field"
        assert claim.get("tier"), f"Claim {claim_id} missing 'tier' field"
        assert "normative" in claim, f"Claim {claim_id} missing 'normative' field"
