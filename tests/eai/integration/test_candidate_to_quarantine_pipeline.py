from core.eai.intelligence_cycle import BoundaryCard, ClaimCard, ClaimStatus, ClaimType, EvidenceArtifact, FalsificationReport, IntelligenceClosureUnit, KillArtifact, QuarantinedClaim, ReproducibilityManifest

def test_candidate_to_quarantine_pipeline():
    q=QuarantinedClaim(ClaimCard('CLM-000001','untestable',ClaimType.THEORETICAL),'insufficient testability')
    icu=IntelligenceClosureUnit(ClaimStatus.QUARANTINED,q,'a'*64)
    assert (not q.integration_permission) and (not q.can_update_integration_memory()) and icu.is_intelligence_unit()
