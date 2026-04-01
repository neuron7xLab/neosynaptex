"""Provenance tracking subpackage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports RunManifest for library-level provenance tracking.

References
----------
docs/SPEC.md#P2-9
docs/REPRODUCIBILITY.md
"""

from .manifest import RunManifest as RunManifest

__all__ = ["RunManifest"]
