import json, pytest, jsonschema
s=json.load(open('schemas/intelligence_closure_unit.schema.json'))
def test_intelligence_closure_unit_schema():
    jsonschema.validate({'icu_id':'ICU-000001','status':'EVIDENCE','retention_hash':'a'*64},s)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate({'icu_id':'BAD','status':'X','retention_hash':'z'},s)
