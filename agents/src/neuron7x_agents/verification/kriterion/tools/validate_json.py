#!/usr/bin/env python3
"""Validate a JSON file against a JSON Schema file."""
import argparse
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import json
from pathlib import Path
import jsonschema
from jsonschema import RefResolver


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema_json")
    parser.add_argument("input_json")
    args = parser.parse_args()

    schema_path = Path(args.schema_json)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    store = {}
    for path in schema_path.parent.glob('*.json'):
        s = json.loads(path.read_text(encoding="utf-8"))
        store[path.name] = s
        if isinstance(s, dict) and '$id' in s:
            store[s['$id']] = s
    resolver = RefResolver(base_uri=schema_path.parent.resolve().as_uri() + '/', referrer=schema, store=store)
    jsonschema.validate(instance=data, schema=schema, resolver=resolver)
    print("VALID")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
