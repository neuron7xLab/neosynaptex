# Defect Registry

This registry tracks identified defects and their remediation status.

| ID | Location | Description | Root Cause | Impact | Severity | Priority | Reproduction | Resolution | Closed Criteria | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MFN-DEF-001 | `src/mycelium_fractal_net/integration/api_config.py` (`RateLimitConfig.from_env`) | Invalid rate-limit environment values caused unhandled `ValueError` on `int()` conversion, leading to crashes during config load. | Missing validation and error handling for malformed/non-positive environment values. | API startup failure when env values are misconfigured. | High | P1 | Set `MFN_RATE_LIMIT_REQUESTS=not-a-number` or `MFN_RATE_LIMIT_WINDOW=0` and call `APIConfig.from_env()`. | Added `_parse_positive_int` to validate env values and raise clear errors; added tests. | Tests asserting error messages pass and config loads with valid defaults. | `python -m pytest tests/test_api_config.py -q` | Closed |
