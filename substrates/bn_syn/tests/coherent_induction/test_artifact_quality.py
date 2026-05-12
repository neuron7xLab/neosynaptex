from coherent_induction.artifact_quality import ArtifactQualityScore


def test_artifact_quality_requires_core_scores() -> None:
    s = ArtifactQualityScore(80, 70, 90, 85, 75, 0)
    assert s.final_score > 0
