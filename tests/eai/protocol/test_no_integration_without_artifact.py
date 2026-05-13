from core.eai.intelligence_cycle import BoundaryCard, ClaimCard, ClaimStatus, ClaimType, EvidenceArtifact, FalsificationReport, IntelligenceClosureUnit, KillArtifact, QuarantinedClaim, ReproducibilityManifest

def test_no_integration_without_artifact():
    icu=IntelligenceClosureUnit(ClaimStatus.EVIDENCE,None,'a'*64,{}, {'next':1})
    assert not icu.is_intelligence_unit()
