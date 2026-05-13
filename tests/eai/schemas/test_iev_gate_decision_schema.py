import json, pytest, jsonschema
s=json.load(open('schemas/iev_gate_decision.schema.json'))
def test_iev_gate_decision_schema():
    jsonschema.validate({'decision_id':'IEV-000001','status':'QUARANTINED','claim_id':'CLM-000001'},s)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({'decision_id':'IEV-1','status':'OK','claim_id':'x'},s)
