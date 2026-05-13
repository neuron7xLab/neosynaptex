from core.eai.intelligence_cycle import BoundaryCard, ClaimCard, ClaimStatus, ClaimType, EvidenceArtifact, FalsificationReport, IntelligenceClosureUnit, KillArtifact, QuarantinedClaim, ReproducibilityManifest

def test_quarantined_claim_cannot_update_memory():
    q=QuarantinedClaim(ClaimCard('CLM-000001','?',ClaimType.PREDICTIVE),'untestable')
    assert not q.can_update_integration_memory()
