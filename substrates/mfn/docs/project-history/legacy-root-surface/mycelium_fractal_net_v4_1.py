#!/usr/bin/env python
"""
CLI entrypoint for MyceliumFractalNet v4.1.

Забезпечує сумісність зі специфікацією "один файл-ентрі":
python mycelium_fractal_net_v4_1.py --mode validate
"""

from __future__ import annotations

import sys
from pathlib import Path

# Додати src/ у sys.path для локального запуску скрипта без інсталяції пакету
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mycelium_fractal_net import run_validation_cli

if __name__ == "__main__":
    run_validation_cli()
