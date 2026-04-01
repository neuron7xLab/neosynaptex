"""Compatibility shim for legacy experiments.inspect_features."""

from warnings import warn

import numpy as np


def load_dataset(path: str):
    try:
        import pandas as pd

        return pd.read_parquet(path)
    except Exception:
        data = np.load(path, allow_pickle=True)
        return {"data": data["data"], "columns": data.get("columns")}


def compute_descriptive_stats(dataset):
    try:
        import pandas as pd

        if isinstance(dataset, pd.DataFrame):
            return dataset.describe(include="all")
    except Exception:
        pass
    if isinstance(dataset, dict) and "data" in dataset:
        arr = np.asarray(dataset["data"], dtype=object)
        return {"rows": int(arr.shape[0]), "cols": int(arr.shape[1]) if arr.ndim == 2 else 0}
    raise TypeError("unsupported dataset type for descriptive stats")


warn(
    "Importing root-level 'experiments.inspect_features' is deprecated; use package APIs instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["load_dataset", "compute_descriptive_stats"]
