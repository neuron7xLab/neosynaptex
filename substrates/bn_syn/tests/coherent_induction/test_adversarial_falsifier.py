from coherent_induction.adversarial_falsifier import run_falsifier


def test_falsifier_blocks_neuro_overreach() -> None:
    r = run_falsifier("literal fusion", True, True)
    assert r.release_blocked
