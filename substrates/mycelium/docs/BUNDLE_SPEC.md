# Artifact Bundle Specification

## Bundle Layout

```
<run_id>/
├── report.json          # Full pipeline report (manifest)
├── field.npy            # Final field array (numpy)
├── history.npy          # Field history array (numpy)
├── descriptor.json      # MorphologyDescriptor
├── detection.json       # AnomalyEvent
├── forecast.json        # ForecastResult
├── comparison.json      # ComparisonResult
├── causal.json          # CausalValidationResult
├── explanation_trace.json  # Full decision trace
└── signature.json       # Ed25519 signature (optional)
```

## Schema Versions

All schemas follow JSON Schema draft-07 and are stored in `docs/contracts/schemas/`.

| Artifact | Schema | Version |
|----------|--------|---------|
| Manifest | manifest.v1.schema.json | v1 |
| Descriptor | morphologydescriptor.v1.schema.json | v1 |
| Detection | anomalyevent.v1.schema.json | v1 |
| Forecast | forecastresult.v1.schema.json | v1 |
| Comparison | comparisonresult.v1.schema.json | v1 |
| Causal | causalvalidationresult.v1.schema.json | v1 |

## Standalone Verification

```bash
python scripts/verify_bundle.py <bundle_directory>
```

The verifier does NOT import `mycelium_fractal_net`. It validates:
1. Each JSON artifact is valid JSON
2. Each artifact has a version field
3. Schema type-level validation passes
4. Checksums match (if present)

## Backward Compatibility

- Schema versions follow semver
- Minor version bumps add optional fields only
- Major version bumps may remove or rename fields
- Old schemas must still validate new artifacts (additive only)

## Signature Verification

If `signature.json` is present, verify with:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
```
