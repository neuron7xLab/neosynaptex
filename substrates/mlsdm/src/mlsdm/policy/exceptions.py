"""Policy subsystem exceptions.

This module defines exceptions for policy drift detection.
All policy-related error types should be defined here to maintain semantic cohesion
and comply with architecture manifest dependency rules.

The policy module has `allowed_dependencies=()` (no external dependencies),
so exceptions must be defined within the policy module itself.
"""

from __future__ import annotations


class PolicyDriftError(RuntimeError):
    """Raised when policy drift is detected or policy registry is invalid.

    This exception is raised by:
    - Policy fingerprint guard when detecting unauthorized threshold changes
    - Policy drift checker when registry/catalog validation fails
    - Policy loader when policy integrity is compromised
    """
