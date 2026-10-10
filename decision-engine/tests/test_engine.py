"""Unit tests for the integrated Decision Engine."""

import unittest
from engine import DecisionEngine


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_decide_skip_when_moisture_plenty(self):
        dec = self.engine.decide(
            plot_id="plt_test_01",
            decision_date="2026-10-09",
            days_after_sowing=45,
            crop_id="maize",
            soil_type="loam",
            area_ha=1.0,
            pump_flow_lpm=120.0,
            pump_power_kw=0.75,
            application_efficiency=0.75,
            current_depletion_mm=5.0,  # Ample moisture
            et0_mm=4.5,
            forecast_rain_48h_mm=0.0,
        )

        self.assertEqual(dec["action"], "SKIP")
        self.assertEqual(dec["duration_minutes"], 0)
        self.assertIn("speech_script_hi", dec)
        self.assertIn("सिंचाई की आवश्यकता नहीं है", dec["speech_script_hi"])
        self.assertTrue(len(dec["reasons"]) >= 2)

    def test_decide_irrigate_when_depleted(self):
        dec = self.engine.decide(
            plot_id="plt_test_02",
            decision_date="2026-10-09",
            days_after_sowing=60,
            crop_id="maize",
            soil_type="loam",
            area_ha=0.5,
            pump_flow_lpm=120.0,
            pump_power_kw=0.75,
            application_efficiency=0.75,
            current_depletion_mm=70.0,  # Stressed, above RAW (~68.1 mm)
            et0_mm=5.0,
            forecast_rain_48h_mm=0.0,
            hours_since_last_irrigation=72.0,
        )

        self.assertEqual(dec["action"], "IRRIGATE")
        self.assertGreater(dec["duration_minutes"], 0)
        self.assertEqual(dec["start_time_ist"], "06:00")
        self.assertIn("speech_script_hi", dec)
        self.assertIn("सिंचाई अनुशंसित है", dec["speech_script_hi"])


if __name__ == "__main__":
    unittest.main()
