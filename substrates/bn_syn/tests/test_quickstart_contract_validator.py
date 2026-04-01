"""Unit tests for quickstart contract validator helper functions."""

from __future__ import annotations

import unittest

from scripts.validate_quickstart_contract import count_gate_collected, extract_quickstart_lines


class ExtractQuickstartLinesTests(unittest.TestCase):
    def test_extracts_lines_with_standard_spacing(self) -> None:
        readme = """# Title\n\n## Quickstart\n\n```bash\nmake quickstart-smoke\n```\n\n## Other\n"""
        self.assertEqual(extract_quickstart_lines(readme), ["make quickstart-smoke"])

    def test_extracts_lines_with_extra_blank_lines(self) -> None:
        readme = """# Title\n## Quickstart\n\n\n```\n\nmake quickstart-smoke\n\n```\n"""
        self.assertEqual(extract_quickstart_lines(readme), ["make quickstart-smoke"])


class CountGateCollectedTests(unittest.TestCase):
    def test_counts_nodeid_style_collect_output(self) -> None:
        output = "\n".join(
            [
                "tests/test_alpha.py::test_a",
                "tests/test_beta.py::test_b",
                "= 2 tests collected in 0.10s =",
            ]
        )
        self.assertEqual(count_gate_collected(output), 2)

    def test_counts_summary_collect_output(self) -> None:
        output = "collected 17 items"
        self.assertEqual(count_gate_collected(output), 17)


if __name__ == "__main__":
    unittest.main()
