"""Presentation helpers for terminal and human-facing demo surfaces."""

from .terminal import (
    emit_bundle_validation_failure,
    emit_bundle_validation_success,
    emit_canonical_run_epilogue,
    emit_canonical_run_prelude,
    emit_demo_product_prelude,
    emit_demo_product_success,
)

__all__ = [
    "emit_bundle_validation_failure",
    "emit_bundle_validation_success",
    "emit_canonical_run_epilogue",
    "emit_canonical_run_prelude",
    "emit_demo_product_prelude",
    "emit_demo_product_success",
]
