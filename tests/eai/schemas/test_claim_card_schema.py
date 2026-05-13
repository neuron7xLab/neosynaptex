import json, jsonschema
s=json.load(open('schemas/claim_card.schema.json'))
def test_claim_card_schema():
    jsonschema.validate({'claim_id':'CLM-000001','claim_text':'x','claim_type':'factual'},s)
