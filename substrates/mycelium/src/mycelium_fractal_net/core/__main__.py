"""MFN core module CLI — causal validation manifest.

Usage:
    python -m mycelium_fractal_net.core --manifest   Display causal rules
    python -m mycelium_fractal_net.core --json       JSON format
    python -m mycelium_fractal_net.core --help       This message
"""

import sys

if "--manifest" in sys.argv:
    from mycelium_fractal_net.core.rule_registry import print_manifest

    print_manifest()
elif "--json" in sys.argv:
    import json

    from mycelium_fractal_net.core.rule_registry import manifest_dict

    sys.stdout.write(json.dumps(manifest_dict(), indent=2) + "\n")
elif "--help" in sys.argv or "-h" in sys.argv:
    pass
else:
    sys.exit(1)
