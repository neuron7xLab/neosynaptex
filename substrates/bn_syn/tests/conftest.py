from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _seed_numpy() -> None:
    np.random.seed(2026)
