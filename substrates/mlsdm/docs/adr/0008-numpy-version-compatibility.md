# ADR-0008: NumPy Version Compatibility Decision

**Status**: Accepted
**Date**: 2026-01-19
**Deciders**: @engineering, @safety-team
**Categories**: Architecture | Dependencies
**Resolves**: TD-005 (HIGH priority)

## Context

The `mlsdm` project uses NumPy 2.0+ as a core dependency (`numpy>=2.0.0`). NumPy 2.0 was released in June 2024 as a major version with significant breaking changes from NumPy 1.x, including:

1. **API Changes**: Removal of deprecated functions, type aliases, and module renames
2. **ABI Incompatibility**: Binaries compiled against NumPy 1.x may not work with 2.x
3. **Ecosystem Compatibility**: Some libraries (especially older ones) may not yet support NumPy 2.x

TD-005 was raised to evaluate whether `numpy>=2.0.0` constraint limits compatibility with other libraries, and whether to consider `numpy>=1.26.0,<3.0.0` as a broader compatibility range.

### Forces at Play

1. **Safety-Critical Operations**: The codebase uses NumPy for memory operations, phase calculations, and cognitive computations that are safety-critical
2. **Type System**: NumPy 2.0 provides improved type annotations critical for mypy strict mode
3. **Performance**: NumPy 2.0 includes performance improvements
4. **CI Matrix**: Current CI tests Python 3.10, 3.11, 3.12 with NumPy 2.0
5. **Dependency Compatibility**: Major dependencies (FastAPI, Pydantic, etc.) support NumPy 2.0

## Decision

**We will maintain `numpy>=2.0.0` as the minimum version requirement.**

Rationale:
1. NumPy 2.0 has been stable for over a year (since June 2024)
2. All major ecosystem libraries now support NumPy 2.0
3. Rolling back to NumPy 1.x would require significant API changes
4. NumPy 2.0's improved type stubs are essential for our strict mypy configuration
5. No production issues have been reported due to NumPy 2.0 usage

## Consequences

### Positive

- **Type Safety**: Full benefit of NumPy 2.0's improved type annotations
- **Future-Proof**: Ready for NumPy 2.1+ improvements
- **Performance**: Access to NumPy 2.0 performance optimizations
- **Maintenance**: Single version target simplifies testing

### Negative

- **Legacy System Compatibility**: Systems locked to NumPy 1.x cannot use mlsdm
- **Transitive Dependencies**: Any library requiring NumPy <2.0 is incompatible

### Neutral

- **Documentation**: No changes needed to existing documentation
- **CI Matrix**: No changes needed to CI configuration

## Alternatives Considered

### Alternative 1: numpy>=1.26.0,<3.0.0

- **Description**: Support both NumPy 1.x and 2.x
- **Pros**: Broader compatibility with older systems and libraries
- **Cons**: 
  - Requires maintaining compatibility with both APIs
  - NumPy 1.x has different type stubs (breaks mypy strict)
  - Testing burden doubles (need CI matrix for 1.x and 2.x)
  - Performance penalty from not using 2.x optimizations
- **Reason for rejection**: Maintenance burden exceeds compatibility benefit

### Alternative 2: numpy>=1.26.0

- **Description**: Support NumPy 1.x only
- **Pros**: Maximum compatibility with legacy systems
- **Cons**:
  - Lose NumPy 2.0 type improvements
  - Lose NumPy 2.0 performance improvements
  - Counter to Python ecosystem direction
- **Reason for rejection**: Technical regression with no justification

## Implementation

No code changes required. This ADR documents the rationale for the existing `numpy>=2.0.0` constraint.

### Affected Components

- `pyproject.toml` (line 40): `"numpy>=2.0.0"`
- `requirements.txt`: `numpy>=2.0.0`

### Verification

```bash
# Verify NumPy 2.x is installed
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"

# Run tests with NumPy 2.x
pytest tests/unit/ -v -m "not slow"
```

### Related Documents

- [TECHNICAL_DEBT_REGISTER.md](../TECHNICAL_DEBT_REGISTER.md) - TD-005 entry
- [pyproject.toml](../../pyproject.toml) - Dependency specification

## References

- [NumPy 2.0 Release Notes](https://numpy.org/doc/stable/release/2.0.0-notes.html)
- [NumPy 2.0 Migration Guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html)
- [NumPy NEP 50: Promotion Rules](https://numpy.org/neps/nep-0050-scalar-promotion.html)

---

*Closes: TD-005 (numpy>=2.0.0 compatibility decision documented)*
