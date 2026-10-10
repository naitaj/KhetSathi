"""Unit tests for FAO-56 water balance model."""

import unittest
from water_balance.model import (
    derive_crop_stage,
    calculate_effective_rainfall,
    calculate_water_capacity,
    update_root_zone_depletion,
    calculate_irrigation_duration,
)


class TestWaterBalance(unittest.TestCase):
    def test_crop_stage_derivation_maize(self):
        # Initial stage (0-20 days)
        s_ini = derive_crop_stage("maize", days_after_sowing=10)
        self.assertEqual(s_ini.stage_id, "initial")
        self.assertAlmostEqual(s_ini.kc, 0.30, places=2)
        self.assertAlmostEqual(s_ini.root_depth_m, 0.30, places=2)

        # Mid-season (55-95 days): root depth progresses from 0.80m to 1.00m
        s_mid_early = derive_crop_stage("maize", days_after_sowing=65)
        self.assertEqual(s_mid_early.stage_id, "mid_season")
        self.assertAlmostEqual(s_mid_early.kc, 1.20, places=2)
        self.assertAlmostEqual(s_mid_early.root_depth_m, 0.85, places=2)

        s_mid_full = derive_crop_stage("maize", days_after_sowing=95)
        self.assertEqual(s_mid_full.stage_id, "mid_season")
        self.assertAlmostEqual(s_mid_full.root_depth_m, 1.00, places=2)

    def test_effective_rainfall(self):
        # <= 2.0 mm should be zero effective
        self.assertEqual(calculate_effective_rainfall(1.5), 0.0)
        self.assertEqual(calculate_effective_rainfall(2.0), 0.0)
        # 12.0 mm -> (12 - 2) * 0.8 = 8.0 mm
        self.assertAlmostEqual(calculate_effective_rainfall(12.0), 8.0, places=1)

    def test_water_capacity_loam(self):
        # Loam: FC=0.27, WP=0.12 -> AWC=0.15 m/m = 150 mm/m
        # Root depth = 0.5 m -> TAW = 150 * 0.5 = 75 mm
        # Maize p = 0.55 -> RAW = 75 * 0.55 = 41.25 mm
        taw, raw = calculate_water_capacity(soil_type="loam", root_depth_m=0.5, p=0.55)
        self.assertAlmostEqual(taw, 75.0, places=1)
        self.assertAlmostEqual(raw, 41.25, places=1)

    def test_depletion_update(self):
        dr = update_root_zone_depletion(
            dr_previous_mm=30.0,
            etc_mm=5.0,
            effective_rain_mm=10.0,
            net_irrigation_mm=0.0,
            taw_mm=100.0,
        )
        self.assertEqual(dr, 25.0)

        # Clamping at 0
        dr_dry = update_root_zone_depletion(10.0, 2.0, 50.0, 0.0, 100.0)
        self.assertEqual(dr_dry, 0.0)

        # Clamping at TAW
        dr_max = update_root_zone_depletion(95.0, 15.0, 0.0, 0.0, 100.0)
        self.assertEqual(dr_max, 100.0)

    def test_pump_duration_calculation(self):
        volume, minutes = calculate_irrigation_duration(
            net_depth_mm=2.0,
            area_ha=0.1,  # 1,000 m2
            pump_flow_lpm=100.0,
            application_efficiency=0.8,
            rounding_increment=5,
        )
        # Net vol = 2.0 * 1,000 = 2,000 L
        # Gross vol = 2,000 / 0.8 = 2,500 L
        # Duration = 2,500 / 100 = 25 minutes
        self.assertEqual(volume, 2500.0)
        self.assertEqual(minutes, 25)


if __name__ == "__main__":
    unittest.main()
