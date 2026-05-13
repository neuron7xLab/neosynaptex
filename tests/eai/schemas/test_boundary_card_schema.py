import json, jsonschema
s=json.load(open('schemas/boundary_card.schema.json'))
def test_boundary_card_schema():
    jsonschema.validate({'boundary_id':'BND-000001','valid_for':['a'],'invalid_for':['b'],'tested_conditions':['a'],'untested_conditions':['b']},s)
