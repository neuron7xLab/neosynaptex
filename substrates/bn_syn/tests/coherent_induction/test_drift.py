from coherent_induction.drift import DriftScore


def test_drift_score_computes() -> None:
    d = DriftScore(0.1, 0.2, 0.0, 0.0, 0.3)
    assert 0 <= d.final_score <= 1
