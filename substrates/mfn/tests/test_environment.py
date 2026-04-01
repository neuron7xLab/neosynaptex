"""Environment validation tests."""


def test_must_have_pandas() -> None:
    import pandas  # noqa: F401


def test_must_have_numpy() -> None:
    import numpy  # noqa: F401


def test_torch_is_optional_ml_dependency() -> None:
    try:
        import torch  # noqa: F401
    except ModuleNotFoundError:
        # Core install is valid without ML extras.
        return


def test_pandas_version_compatibility() -> None:
    import pandas as pd
    from packaging import version

    min_version = "1.5.3"
    max_version = "4.0.0"

    current = version.parse(pd.__version__)
    min_v = version.parse(min_version)
    max_v = version.parse(max_version)

    assert current >= min_v, f"pandas version {pd.__version__} is too old (minimum: {min_version})"
    assert current < max_v, f"pandas version {pd.__version__} is too new (maximum: <{max_version})"


def test_numpy_typing_available() -> None:
    from numpy.typing import NDArray  # noqa: F401
