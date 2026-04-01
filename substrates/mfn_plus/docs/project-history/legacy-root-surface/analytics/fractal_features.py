"""Compatibility shim for analytics.fractal_features."""

from warnings import warn

from mycelium_fractal_net.analytics import legacy_features as _impl
from mycelium_fractal_net.analytics.legacy_features import *  # noqa: F401,F403

_box_counting_dimension = _impl._box_counting_dimension
_count_clusters_4conn = _impl._count_clusters_4conn
_count_clusters_8conn = _impl._count_clusters_8conn
validate_feature_ranges = _impl.validate_feature_ranges

warn(
    "Importing analytics.fractal_features is deprecated; "
    "use mycelium_fractal_net.analytics.fractal_features instead.",
    DeprecationWarning,
    stacklevel=2,
)
