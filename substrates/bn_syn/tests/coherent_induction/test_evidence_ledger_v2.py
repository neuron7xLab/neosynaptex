from coherent_induction.evidence_ledger_v2 import make_entry, to_json


def test_ledger_v2_schema() -> None:
    e = make_entry({
        "run_id":"1","role_sequence_hash":"a","hypothesis_hash":"b","artifact_hash":"c","config_hash":"d","model_name":"m","prompt_hash":"p","drift_score":0.1,"quality_score":1.0,"falsifier_verdict":"PASS","safety_verdict":"PASS","final_verdict":"PASS","failure_reason":"","reproducibility_command":"cmd"
    })
    assert e.utc_timestamp.endswith("Z")
    assert "run_id" in to_json(e)
