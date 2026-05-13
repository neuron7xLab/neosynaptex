import json, pytest, jsonschema
s=json.load(open('schemas/artifact_ledger_entry.schema.json'))
def test_artifact_ledger_entry_schema():
    jsonschema.validate({'ledger_id':'LEDGER-000001','status':'KILLED','artifact_hash':'a'*64},s)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({'ledger_id':'LEDGER-1','status':'BAD','artifact_hash':'no'},s)
