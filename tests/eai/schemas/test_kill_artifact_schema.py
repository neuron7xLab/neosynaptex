import json, pytest, jsonschema
s=json.load(open('schemas/kill_artifact.schema.json'))
def test_kill_artifact_schema():
    good={'artifact_id':'KILL-000001','status':'KILLED','claim_id':'CLM-000001','kill_reason':'r','future_guardrail':'g','artifact_hash':'a'*64,'integration_permission':False}
    jsonschema.validate(good,s)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({**good,'kill_reason':''},s)
