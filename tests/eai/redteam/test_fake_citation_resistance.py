from core.eai.intelligence_cycle import BoundaryCard, ClaimCard, ClaimStatus, ClaimType, EvidenceArtifact, FalsificationReport, IntelligenceClosureUnit, KillArtifact, QuarantinedClaim, ReproducibilityManifest

def test_fake_citation_resistance():
    c=ClaimCard('CLM-000001','fake citation',ClaimType.FACTUAL)
    q=QuarantinedClaim(c,'no independent source')
    assert q.integration_permission is False
