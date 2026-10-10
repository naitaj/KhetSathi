"""Unit tests for independent Agronomic Safety Layer."""

import unittest
from safety.checker import AgronomicSafetyLayer, SafetyOutcome


class TestAgronomicSafetyLayer(unittest.TestCase):
    def setUp(self):
        self.safety = AgronomicSafetyLayer()

    def test_s01_input_plausibility_failure(self):
        # Negative area should trigger FAIL_CLOSED
        res = self.safety.evaluate(
            proposed_action="IRRIGATE",
            proposed_net_depth_mm=15.0,
            proposed_duration_minutes=45,
            proposed_start_time_ist="06:00",
            depletion_mm=30.0,
            raw_mm=25.0,
            taw_mm=60.0,
            stage_id="mid_season",
            area_ha=-1.0,  # Invalid
            pump_flow_lpm=120.0,
        )
        self.assertEqual(res.outcome, SafetyOutcome.FAIL_CLOSED)
        self.assertEqual(res.action, "SKIP")

    def test_s03_depletion_floor_veto(self):
        # Soil has ample moisture (depletion 5 mm, RAW 30 mm)
        # Even if a model proposes IRRIGATE, safety must veto it to SKIP
        res = self.safety.evaluate(
            proposed_action="IRRIGATE",
            proposed_net_depth_mm=10.0,
            proposed_duration_minutes=30,
            proposed_start_time_ist="06:00",
            depletion_mm=5.0,
            raw_mm=30.0,
            taw_mm=75.0,
            stage_id="mid_season",
            area_ha=1.0,
            pump_flow_lpm=120.0,
        )
        self.assertEqual(res.outcome, SafetyOutcome.VETOED)
        self.assertEqual(res.action, "SKIP")
        self.assertEqual(res.final_duration_minutes, 0)

    def test_s04_rainfall_skip(self):
        # Need is 20 mm, but forecast rain has 25 mm effective
        # Should override IRRIGATE to SKIP
        res = self.safety.evaluate(
            proposed_action="IRRIGATE",
            proposed_net_depth_mm=20.0,
            proposed_duration_minutes=45,
            proposed_start_time_ist="06:00",
            depletion_mm=20.0,
            raw_mm=18.0,
            taw_mm=60.0,
            stage_id="mid_season",
            area_ha=1.0,
            pump_flow_lpm=120.0,
            forecast_rain_48h_effective_mm=25.0,
        )
        self.assertEqual(res.action, "SKIP")
        self.assertIn("Rainfall Skip", [r.rule_name for r in res.rules_evaluated if not r.passed])

    def test_s05_minimum_interval_veto(self):
        # Last irrigation was 12 hours ago (< 24h min interval)
        res = self.safety.evaluate(
            proposed_action="IRRIGATE",
            proposed_net_depth_mm=15.0,
            proposed_duration_minutes=35,
            proposed_start_time_ist="06:00",
            depletion_mm=22.0,
            raw_mm=20.0,
            taw_mm=60.0,
            stage_id="mid_season",
            area_ha=1.0,
            pump_flow_lpm=120.0,
            hours_since_last_irrigation=12.0,
        )
        self.assertEqual(res.outcome, SafetyOutcome.VETOED)
        self.assertEqual(res.action, "SKIP")

    def test_s06_maximum_duration_cap(self):
        # Proposed 90 minutes; cap is 60 minutes
        res = self.safety.evaluate(
            proposed_action="IRRIGATE",
            proposed_net_depth_mm=20.0,
            proposed_duration_minutes=90,
            proposed_start_time_ist="06:00",
            depletion_mm=25.0,
            raw_mm=20.0,
            taw_mm=60.0,
            stage_id="mid_season",
            area_ha=1.0,
            pump_flow_lpm=120.0,
            hours_since_last_irrigation=48.0,
        )
        self.assertEqual(res.outcome, SafetyOutcome.MODIFIED)
        self.assertEqual(res.action, "IRRIGATE")
        self.assertEqual(res.final_duration_minutes, 60)

    def test_s10_severe_depletion_protection(self):
        # Dr = 55 mm, TAW = 60 mm -> Severe stress (Dr > 0.9 * TAW)
        # Even if proposal says SKIP, safety must upgrade to IRRIGATE
        res = self.safety.evaluate(
            proposed_action="SKIP",
            proposed_net_depth_mm=0.0,
            proposed_duration_minutes=0,
            proposed_start_time_ist="06:00",
            depletion_mm=55.0,
            raw_mm=30.0,
            taw_mm=60.0,
            stage_id="mid_season",
            area_ha=1.0,
            pump_flow_lpm=120.0,
        )
        self.assertEqual(res.outcome, SafetyOutcome.MODIFIED)
        self.assertEqual(res.action, "IRRIGATE")
        self.assertGreater(res.final_duration_minutes, 0)


if __name__ == "__main__":
    unittest.main()
