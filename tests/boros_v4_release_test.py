from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "samples" / "boros-backtest-modes" / "release_baseline.json"


class BorosReleaseBaselineTest(unittest.TestCase):
    def test_release_baseline_covers_expected_scenarios(self):
        payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        scenarios = payload["scenarios"]
        self.assertEqual(
            set(scenarios.keys()),
            {
                "two_leg_baseline",
                "four_leg_synthetic_funding",
                "full_execution_compare",
                "full_execution_diagnostics",
            },
        )

    def test_release_baseline_metrics_have_matching_tolerances(self):
        payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        for scenario_name, scenario in payload["scenarios"].items():
            self.assertEqual(
                set(scenario["expected"].keys()),
                set(scenario["tolerance"].keys()),
                msg=scenario_name,
            )


if __name__ == "__main__":
    unittest.main()
