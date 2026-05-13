from core.eai.intelligence_cycle import BoundaryCard, ClaimCard, ClaimStatus, ClaimType, EvidenceArtifact, FalsificationReport, IntelligenceClosureUnit, KillArtifact, QuarantinedClaim, ReproducibilityManifest

def test_killed_artifact_retention():
    c=ClaimCard('CLM-000001','bad',ClaimType.THEORETICAL)
    k=KillArtifact('KILL-000001',c,'reason','falsifier','guard')
    assert k.retained and not k.can_be_integrated() and k.is_high_quality_kill()
