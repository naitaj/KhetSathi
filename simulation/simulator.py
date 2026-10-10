"""Simulation Harness comparing Baseline fixed-schedule vs KhetSathi adaptive irrigation.

Strictly adheres to:
1. Identical inputs, soil, weather, crop, pump specs for both arms.
2. Reporting both water conservation and crop stress days.
3. Explicitly tagging all results with 'SIMULATED'.
4. Bit-for-bit reproducibility from fixed scenario and seed.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure decision-engine is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECISION_ENGINE_DIR = PROJECT_ROOT / "decision-engine"
if str(DECISION_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(DECISION_ENGINE_DIR))

from engine import DecisionEngine
from water_balance.model import (
    calculate_effective_rainfall,
    calculate_water_capacity,
    derive_crop_stage,
    update_root_zone_depletion,
)


class IrrigationSimulator:
    """Runs counterfactual simulations comparing fixed-schedule vs KhetSathi."""

    def __init__(self, scenario_data: Dict[str, Any]):
        self.scenario = scenario_data
        self.engine = DecisionEngine()

    @classmethod
    def from_scenario_file(cls, scenario_path: Path) -> IrrigationSimulator:
        with open(scenario_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def run(self, baseline_interval_days: int = 4, baseline_duration_minutes: int = 45) -> Dict[str, Any]:
        """Execute day-by-day simulation across both arms."""
        weather_days: List[Dict[str, Any]] = self.scenario.get("daily_weather", [])
        total_days = len(weather_days)
        crop_id = self.scenario.get("crop", "maize")
        soil_type = self.scenario.get("soil_type", "loam")
        area_ha = float(self.scenario.get("area_ha", 1.0))
        area_m2 = area_ha * 10000.0

        pump_cfg = self.scenario.get("pump", {})
        pump_flow_lpm = float(pump_cfg.get("flow_lpm", 120.0))
        pump_power_kw = float(pump_cfg.get("power_kw", 0.75))
        efficiency = float(pump_cfg.get("application_efficiency", 0.75))

        # Initial conditions: start at low initial depletion (e.g. 10 mm after pre-sowing irrigation)
        dr_base = 10.0
        dr_khet = 10.0
        last_irr_day_base: Optional[int] = -baseline_interval_days
        last_irr_day_khet: Optional[int] = None

        # Cumulative Metrics
        events_base = 0
        events_khet = 0
        water_applied_l_base = 0.0
        water_applied_l_khet = 0.0
        minutes_base = 0
        minutes_khet = 0
        stress_days_base = 0
        stress_days_khet = 0

        daily_log: List[Dict[str, Any]] = []

        for idx, w in enumerate(weather_days):
            day_num = w["day"]
            das = day_num
            et0_mm = float(w["et0_mm"])
            rain_mm = float(w["rain_mm"])
            eff_rain_mm = calculate_effective_rainfall(rain_mm)

            # Lookahead forecast rain (sum of next 2 days)
            forecast_rain_mm = 0.0
            if idx + 1 < total_days:
                forecast_rain_mm += float(weather_days[idx + 1]["rain_mm"])
            if idx + 2 < total_days:
                forecast_rain_mm += float(weather_days[idx + 2]["rain_mm"])

            # Current crop & soil parameters for the day
            crop_stage = derive_crop_stage(crop_id, das)
            etc_mm = round(crop_stage.kc * et0_mm, 2)
            taw_mm, raw_mm = calculate_water_capacity(soil_type, crop_stage.root_depth_m, crop_stage.allowable_depletion_p)

            # --- ARM A: Baseline Strategy (Fixed schedule every N days) ---
            base_action = "SKIP"
            base_dur_min = 0
            base_water_l = 0.0
            base_net_depth_mm = 0.0

            days_since_base = (day_num - last_irr_day_base) if last_irr_day_base is not None else 999
            if days_since_base >= baseline_interval_days:
                base_action = "IRRIGATE"
                base_dur_min = baseline_duration_minutes
                base_water_l = base_dur_min * pump_flow_lpm
                base_net_depth_mm = (base_water_l * efficiency) / area_m2
                events_base += 1
                minutes_base += base_dur_min
                water_applied_l_base += base_water_l
                last_irr_day_base = day_num

            # Update Baseline Depletion
            dr_base = update_root_zone_depletion(
                dr_previous_mm=dr_base,
                etc_mm=etc_mm,
                effective_rain_mm=eff_rain_mm,
                net_irrigation_mm=base_net_depth_mm,
                taw_mm=taw_mm,
            )
            is_stressed_base = dr_base > raw_mm
            if is_stressed_base:
                stress_days_base += 1

            # --- ARM B: KhetSathi Strategy (Water-Balance + Agronomic Safety) ---
            hours_since_khet = None
            if last_irr_day_khet is not None:
                hours_since_khet = float((day_num - last_irr_day_khet) * 24.0)

            khet_dec = self.engine.decide(
                plot_id="sim_plot_01",
                decision_date=f"2026-06-{day_num:02d}",
                days_after_sowing=das,
                crop_id=crop_id,
                soil_type=soil_type,
                area_ha=area_ha,
                pump_flow_lpm=pump_flow_lpm,
                pump_power_kw=pump_power_kw,
                application_efficiency=efficiency,
                current_depletion_mm=dr_khet,
                et0_mm=et0_mm,
                forecast_rain_48h_mm=forecast_rain_mm,
                observed_rain_24h_mm=rain_mm,
                hours_since_last_irrigation=hours_since_khet,
                is_simulation=True,
            )

            khet_action = khet_dec["action"]
            khet_dur_min = khet_dec["duration_minutes"]
            khet_water_l = khet_dec["estimated_extraction_liters"]
            khet_net_depth_mm = khet_dec["net_depth_mm"]

            if khet_action == "IRRIGATE":
                events_khet += 1
                minutes_khet += khet_dur_min
                water_applied_l_khet += khet_water_l
                last_irr_day_khet = day_num

            # Update KhetSathi Depletion
            dr_khet = update_root_zone_depletion(
                dr_previous_mm=dr_khet,
                etc_mm=etc_mm,
                effective_rain_mm=eff_rain_mm,
                net_irrigation_mm=khet_net_depth_mm,
                taw_mm=taw_mm,
            )
            is_stressed_khet = dr_khet > raw_mm
            if is_stressed_khet:
                stress_days_khet += 1

            daily_log.append({
                "day": day_num,
                "das": das,
                "et0_mm": et0_mm,
                "rain_mm": rain_mm,
                "baseline": {
                    "action": base_action,
                    "duration_min": base_dur_min,
                    "water_l": base_water_l,
                    "depletion_mm": dr_base,
                    "stressed": is_stressed_base,
                },
                "khetsathi": {
                    "action": khet_action,
                    "duration_min": khet_dur_min,
                    "water_l": khet_water_l,
                    "depletion_mm": dr_khet,
                    "stressed": is_stressed_khet,
                    "safety_status": khet_dec["safety_status"],
                },
            })

        # Calculate final savings & impact
        pump_hours_base = round(minutes_base / 60.0, 2)
        pump_hours_khet = round(minutes_khet / 60.0, 2)
        avoided_pump_hours = round(max(0.0, pump_hours_base - pump_hours_khet), 2)

        water_saved_l = round(max(0.0, water_applied_l_base - water_applied_l_khet), 1)
        water_saved_pct = round((water_saved_l / max(1.0, water_applied_l_base)) * 100.0, 1)

        energy_kwh_base = round(pump_hours_base * pump_power_kw, 2)
        energy_kwh_khet = round(pump_hours_khet * pump_power_kw, 2)
        energy_saved_kwh = round(max(0.0, energy_kwh_base - energy_kwh_khet), 2)

        avoided_events = max(0, events_base - events_khet)

        return {
            "simulation_label": "SIMULATED",
            "scenario_id": self.scenario.get("scenario_id"),
            "location": self.scenario.get("location"),
            "crop": crop_id,
            "soil_type": soil_type,
            "area_ha": area_ha,
            "simulated_days": total_days,
            "summary": {
                "baseline": {
                    "strategy": f"Fixed schedule every {baseline_interval_days} days for {baseline_duration_minutes} min",
                    "irrigation_events": events_base,
                    "pump_hours": pump_hours_base,
                    "water_applied_liters": water_applied_l_base,
                    "pump_energy_kwh": energy_kwh_base,
                    "crop_stress_days": stress_days_base,
                },
                "khetsathi": {
                    "strategy": "Adaptive FAO-56 Water Balance + Agronomic Safety Layer",
                    "irrigation_events": events_khet,
                    "pump_hours": pump_hours_khet,
                    "water_applied_liters": water_applied_l_khet,
                    "pump_energy_kwh": energy_kwh_khet,
                    "crop_stress_days": stress_days_khet,
                },
                "impact": {
                    "water_saved_liters": water_saved_l,
                    "water_saved_percent": water_saved_pct,
                    "avoided_irrigation_events": avoided_events,
                    "avoided_pump_hours": avoided_pump_hours,
                    "avoided_energy_kwh": energy_saved_kwh,
                    "crop_stress_days_difference": stress_days_khet - stress_days_base,
                },
            },
            "guardrail_verification": {
                "safe_irrigation_maintained": stress_days_khet <= (stress_days_base + 1),
                "excess_extraction_avoided": water_saved_l > 0,
            },
            "disclaimer": (
                "ALL VALUES ARE SIMULATED USING HISTORICAL WEATHER REPLAYS. "
                "THIS DEMONSTRATES ALGORITHMIC EFFICIENCY RELATIVE TO A FIXED SCHEDULE "
                "AND IS NOT A CLAIM OF MEASURED GROUNDWATER OR FIELD SAVINGS."
            ),
            "daily_log": daily_log,
        }
