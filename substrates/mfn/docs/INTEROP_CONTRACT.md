# Domain Interoperability Contract

## Purpose

All MFN pipeline outputs are JSON-serializable with versioned schemas.
External systems can consume MFN output without installing the Python engine.

## Schemas

| Domain Type | Schema | Roundtrip Guarantee |
|-------------|--------|---------------------|
| SimulationSpec | simulation_spec.v1.schema.json | `to_dict()` → JSON → `from_dict()` |
| FieldSequence | field_sequence.v1.schema.json | Summary only; arrays via numpy |
| MorphologyDescriptor | morphology_descriptor.v1.schema.json | Full roundtrip |
| AnomalyEvent | anomaly_event.v1.schema.json | Full roundtrip |
| ForecastResult | forecast_result.v1.schema.json | Full roundtrip |
| ComparisonResult | comparison_result.v1.schema.json | Full roundtrip |
| CausalValidationResult | causal_validation_result.v1.schema.json | Full roundtrip |
| AnalysisReport | analysis_report.v1.schema.json | Full roundtrip |

## Roundtrip Guarantee

For every domain type `T`:
```
obj = T(...)
d = obj.to_dict()
json_str = json.dumps(d)
d2 = json.loads(json_str)
obj2 = T.from_dict(d2)
assert semantic_equal(obj, obj2)
```

## Using MFN Output Without Python

```javascript
// JavaScript example
const report = JSON.parse(fs.readFileSync('report.json'));
const score = report.detection.score;
const label = report.detection.label;
const regime = report.detection.regime.label;
const features = report.descriptor.features;
```

## Schema Evolution Policy

1. **Patch**: No schema changes
2. **Minor**: New optional fields only (backward compatible)
3. **Major**: Breaking changes (field removal/rename)

All schema changes require:
- Version bump in schema file
- Backward compatibility test
- CHANGELOG entry
