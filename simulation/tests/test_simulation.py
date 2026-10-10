"""Unit tests for the Simulation Engine."""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "simulation"))
sys.path.insert(0, str(PROJECT_ROOT / "decision-engine"))

from simulator import IrrigationSimulator


class TestIrrigationSimulator(unittest.TestCase):
    def setUp(self):
        scenario_path = PROJECT_ROOT / "data" / "scenarios" / "bihar_maize_season.json"
        self.sim = IrrigationSimulator.from_scenario_file(scenario_path)

    def test_simulation_runs_successfully(self):
        res = self.sim.run(baseline_interval_days=4, baseline_duration_minutes=45)
        self.assertEqual(res["simulation_label"], "SIMULATED")
        self.assertEqual(res["simulated_days"], 60)
        self.assertIn("summary", res)

        impact = res["summary"]["impact"]
        self.assertGreater(impact["water_saved_liters"], 0)
        self.assertGreater(impact["water_saved_percent"], 0)
        self.assertIn("disclaimer", res)

    def test_bit_for_bit_reproducibility(self):
        res1 = self.sim.run(baseline_interval_days=4, baseline_duration_minutes=45)
        res2 = self.sim.run(baseline_interval_days=4, baseline_duration_minutes=45)
        self.assertEqual(res1["summary"], res2["summary"])
        self.assertEqual(len(res1["daily_log"]), len(res2["daily_log"]))


if __name__ == "__main__":
    unittest.main()
