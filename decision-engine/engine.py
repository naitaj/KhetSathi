"""Unified Pure Python Decision Engine for KhetSathi.

Orchestrates:
1. Crop stage derivation & soil moisture parameter evaluation.
2. Root-zone water balance (FAO-56 single-bucket depletion).
3. Baseline counterfactual generation (fixed-schedule comparison).
4. Proposal generation (deterministic water-balance rule).
5. Agronomic safety layer evaluation (S01 to S12).
6. Deterministic fact-based explanations (English and Hindi).
"""

from __future__ import annotations
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from config.loader import get_crops_config, get_safety_config, get_soils_config
    from rules.explanation import format_speech_script_hi, generate_explanation
    from safety.checker import AgronomicSafetyLayer, SafetyOutcome
    from water_balance.model import (
        calculate_effective_rainfall,
        calculate_irrigation_duration,
        calculate_water_capacity,
        derive_crop_stage,
        update_root_zone_depletion,
    )
except (ImportError, ValueError):
    from .config.loader import get_crops_config, get_safety_config, get_soils_config
    from .rules.explanation import format_speech_script_hi, generate_explanation
    from .safety.checker import AgronomicSafetyLayer, SafetyOutcome
    from .water_balance.model import (
        calculate_effective_rainfall,
        calculate_irrigation_duration,
        calculate_water_capacity,
        derive_crop_stage,
        update_root_zone_depletion,
    )

ENGINE_VERSION = "1.0.0"


def generate_ulid(prefix: str = "dec_") -> str:
    """Generate prefixed unique identifier."""
    return f"{prefix}{uuid.uuid4().hex[:16]}"


class DecisionEngine:
    """Core decision engine implementing the SENSE -> DECIDE -> PROTECT -> EXPLAIN flow."""

    def __init__(
        self,
        crops_cfg: Optional[Dict[str, Any]] = None,
        soils_cfg: Optional[Dict[str, Any]] = None,
        safety_cfg: Optional[Dict[str, Any]] = None,
    ):
        self.crops_cfg = crops_cfg or get_crops_config()
        self.soils_cfg = soils_cfg or get_soils_config()
        self.safety_cfg = safety_cfg or get_safety_config()
        self.safety_layer = AgronomicSafetyLayer(self.safety_cfg)

    def decide(
        self,
        plot_id: str,
        decision_date: str,  # YYYY-MM-DD
        days_after_sowing: int,
        crop_id: str,
        soil_type: str,
        area_ha: float,
        pump_flow_lpm: float,
        pump_power_kw: float,
        application_efficiency: float,
        # Moisture & Environmental State
        current_depletion_mm: float,
        et0_mm: float,
        forecast_rain_48h_mm: float,
        observed_rain_24h_mm: float = 0.0,
        hours_since_last_irrigation: Optional[float] = None,
        weather_age_hours: float = 0.0,
        model_proposal: Optional[Dict[str, Any]] = None,
        is_simulation: bool = False,
    ) -> Dict[str, Any]:
        """Produce the canonical daily decision for a plot."""
        # 1. Derive crop stage, Kc, and rooting depth
        crop_stage = derive_crop_stage(crop_id, days_after_sowing, self.crops_cfg)
        etc_mm = round(crop_stage.kc * et0_mm, 2)

        # 2. Derive soil water parameters (TAW, RAW)
        taw_mm, raw_mm = calculate_water_capacity(
            soil_type=soil_type,
            root_depth_m=crop_stage.root_depth_m,
            p=crop_stage.allowable_depletion_p,
            soils_cfg=self.soils_cfg,
        )

        # 3. Calculate effective rainfall
        eff_forecast_rain_mm = calculate_effective_rainfall(forecast_rain_48h_mm)
        eff_observed_rain_mm = calculate_effective_rainfall(observed_rain_24h_mm)

        # 4. Generate Baseline Counterfactual (fixed interval every 4 days)
        baseline_action = "SKIP"
        baseline_duration = 0
        baseline_liters = 0.0
        # If no irrigation in 4 days (or first day), baseline irrigates fixed 45 mins
        if hours_since_last_irrigation is None or hours_since_last_irrigation >= 96.0:
            baseline_action = "IRRIGATE"
            baseline_duration = 45
            baseline_liters = round(baseline_duration * pump_flow_lpm, 1)

        # 5. Deterministic Water-Balance Proposal
        # Water needed to refill root zone up to field capacity
        # Trigger when current depletion >= RAW
        proposed_action = "SKIP"
        proposed_depth_mm = 0.0
        proposed_duration = 0
        proposed_volume_l = 0.0

        if current_depletion_mm >= raw_mm:
            proposed_action = "IRRIGATE"
            proposed_depth_mm = current_depletion_mm
            proposed_volume_l, proposed_duration = calculate_irrigation_duration(
                net_depth_mm=proposed_depth_mm,
                area_ha=area_ha,
                pump_flow_lpm=pump_flow_lpm,
                application_efficiency=application_efficiency,
            )

        # If an optional learned proposal exists, use it as a candidate proposal
        if model_proposal:
            proposed_action = model_proposal.get("action", proposed_action)
            proposed_duration = model_proposal.get("duration_minutes", proposed_duration)
            proposed_depth_mm = model_proposal.get("net_depth_mm", proposed_depth_mm)

        # 6. Agronomic Safety Layer Validation (S01 to S12)
        safety_eval = self.safety_layer.evaluate(
            proposed_action=proposed_action,
            proposed_net_depth_mm=proposed_depth_mm,
            proposed_duration_minutes=proposed_duration,
            proposed_start_time_ist=crop_stage.preferred_start_time_ist,
            depletion_mm=current_depletion_mm,
            raw_mm=raw_mm,
            taw_mm=taw_mm,
            stage_id=crop_stage.stage_id,
            area_ha=area_ha,
            pump_flow_lpm=pump_flow_lpm,
            hours_since_last_irrigation=hours_since_last_irrigation,
            forecast_rain_48h_effective_mm=eff_forecast_rain_mm,
            weather_age_hours=weather_age_hours,
        )

        final_action = safety_eval.action
        final_depth_mm = safety_eval.final_net_depth_mm
        final_duration_min = safety_eval.final_duration_minutes
        final_start_time = safety_eval.final_start_time_ist

        # Recalculate gross extraction volume based on final approved duration & pump flow
        final_extraction_liters = 0.0
        if final_action == "IRRIGATE":
            final_extraction_liters = round(final_duration_min * pump_flow_lpm, 1)

        # 7. Generate Deterministic Reasons
        is_rain_skip = "Rainfall Skip" in [r.rule_name for r in safety_eval.rules_evaluated if not r.passed]
        is_floor_veto = "Depletion Floor" in [r.rule_name for r in safety_eval.rules_evaluated if not r.passed]
        is_interval_veto = "Minimum Interval" in [r.rule_name for r in safety_eval.rules_evaluated if not r.passed]
        is_severe = current_depletion_mm >= (0.90 * taw_mm)

        reasons = generate_explanation(
            action=final_action,
            depletion_mm=current_depletion_mm,
            raw_mm=raw_mm,
            taw_mm=taw_mm,
            forecast_rain_48h_mm=forecast_rain_48h_mm,
            duration_minutes=final_duration_min,
            start_time_ist=final_start_time,
            applied_overrides=safety_eval.applied_overrides,
            is_rain_skip=is_rain_skip,
            is_floor_veto=is_floor_veto,
            is_interval_veto=is_interval_veto,
            is_severe_stressed=is_severe,
            is_degraded=safety_eval.degraded,
        )

        crop_vernacular = self.crops_cfg.get("crops", {}).get(crop_id, {}).get("display_name_hi", "फसल")
        speech_script_hi = format_speech_script_hi(
            action=final_action,
            start_time_ist=final_start_time,
            duration_minutes=final_duration_min,
            reasons=reasons,
            crop_name_hi=crop_vernacular,
        )

        decision_id = generate_ulid("dec_")
        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "decision_id": decision_id,
            "plot_id": plot_id,
            "decision_date": decision_date,
            "action": final_action,
            "start_time_ist": final_start_time if final_action == "IRRIGATE" else None,
            "duration_minutes": final_duration_min if final_action == "IRRIGATE" else 0,
            "estimated_extraction_liters": final_extraction_liters,
            "net_depth_mm": final_depth_mm,
            "crop": crop_id,
            "crop_stage": crop_stage.stage_id,
            "crop_stage_name": crop_stage.stage_name,
            "kc": crop_stage.kc,
            "et0_mm": et0_mm,
            "etc_mm": etc_mm,
            "depletion_mm": current_depletion_mm,
            "raw_mm": raw_mm,
            "taw_mm": taw_mm,
            "forecast_rain_48h_mm": forecast_rain_48h_mm,
            "effective_forecast_rain_mm": eff_forecast_rain_mm,
            "safety_status": safety_eval.outcome.value,
            "safety_message": safety_eval.safety_message,
            "applied_overrides": safety_eval.applied_overrides,
            "reasons": [asdict(r) for r in reasons],
            "speech_script_hi": speech_script_hi,
            "confidence": {
                "level": safety_eval.confidence_level,
                "score": 0.95 if safety_eval.confidence_level == "HIGH" else 0.60,
            },
            "degraded": safety_eval.degraded,
            "simulation_flag": is_simulation,
            "baseline_counterfactual": {
                "action": baseline_action,
                "duration_minutes": baseline_duration,
                "water_liters": baseline_liters,
            },
            "created_at": now_iso,
            "engine_version": ENGINE_VERSION,
            "config_version": self.safety_cfg.get("config_version", "2026-10-08-demo-1"),
        }
