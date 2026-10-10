"""Independent Agronomic Safety Layer for KhetSathi.

Strictly decoupled from any AI, ML, or optimization model.
Implements the 12 TRD Safety Rules (S01 to S12) enforcing the core invariant:
'AI proposes; agronomic constraints control what can be deployed.'
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from config.loader import get_safety_config
except (ImportError, ValueError):
    from ..config.loader import get_safety_config


class SafetyOutcome(str, Enum):
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    VETOED = "VETOED"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass
class SafetyRuleCheck:
    rule_id: str
    rule_name: str
    passed: bool
    description: str


@dataclass
class SafetyEvaluationResult:
    action: str  # "IRRIGATE" or "SKIP"
    original_action: str
    outcome: SafetyOutcome
    final_net_depth_mm: float
    final_duration_minutes: int
    final_start_time_ist: str
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    degraded: bool
    applied_overrides: List[str] = field(default_factory=list)
    rules_evaluated: List[SafetyRuleCheck] = field(default_factory=list)
    safety_message: str = ""


class AgronomicSafetyLayer:
    """Evaluates and enforces agronomic safety rules on any proposed irrigation action."""

    def __init__(self, safety_cfg: Optional[Dict[str, Any]] = None):
        if safety_cfg is None:
            safety_cfg = get_safety_config()
        self.rules = safety_cfg.get("rules", {})

        self.max_duration_minutes = int(self.rules.get("max_duration_minutes", 60))
        self.max_daily_depth_mm = float(self.rules.get("max_daily_depth_mm", 25.0))
        self.min_interval_hours = float(self.rules.get("min_interval_hours", 24.0))
        self.rainfall_skip_fraction = float(self.rules.get("rainfall_skip_coverage_fraction", 0.75))
        self.depletion_trigger_fraction = float(self.rules.get("depletion_trigger_fraction", 0.85))
        self.severe_depletion_fraction = float(self.rules.get("severe_depletion_fraction", 0.90))
        self.max_stale_weather_hours = float(self.rules.get("max_stale_weather_hours", 36.0))
        self.min_recommended_duration_minutes = int(self.rules.get("min_recommended_duration_minutes", 15))

    def evaluate(
        self,
        proposed_action: str,  # "IRRIGATE" or "SKIP"
        proposed_net_depth_mm: float,
        proposed_duration_minutes: int,
        proposed_start_time_ist: str,
        # Plot & Agronomic Context
        depletion_mm: float,
        raw_mm: float,
        taw_mm: float,
        stage_id: str,
        area_ha: float,
        pump_flow_lpm: float,
        hours_since_last_irrigation: Optional[float] = None,
        forecast_rain_48h_effective_mm: float = 0.0,
        weather_age_hours: float = 0.0,
        has_critical_error: bool = False,
    ) -> SafetyEvaluationResult:
        """Run all safety checks sequentially and determine the final action."""
        checks: List[SafetyRuleCheck] = []
        overrides: List[str] = []
        outcome = SafetyOutcome.APPROVED
        action = proposed_action.upper()
        net_depth = max(0.0, proposed_net_depth_mm)
        duration = max(0, proposed_duration_minutes)
        start_time = proposed_start_time_ist
        confidence = "HIGH"
        degraded = False

        # --- S01: Critical input plausibility check ---
        if has_critical_error or area_ha <= 0 or area_ha > 50 or pump_flow_lpm <= 0 or taw_mm <= 0:
            checks.append(SafetyRuleCheck("S01", "Input Plausibility", False, "Critical input outside safe bounds"))
            return SafetyEvaluationResult(
                action="SKIP",
                original_action=proposed_action,
                outcome=SafetyOutcome.FAIL_CLOSED,
                final_net_depth_mm=0.0,
                final_duration_minutes=0,
                final_start_time_ist=start_time,
                confidence_level="LOW",
                degraded=True,
                applied_overrides=["Fail-closed: Invalid plot configuration or input plausibility failure."],
                rules_evaluated=checks,
                safety_message="System safely halted irrigation recommendation due to invalid input data.",
            )
        checks.append(SafetyRuleCheck("S01", "Input Plausibility", True, "Inputs within safe agronomic bounds"))

        # --- S02: Data Freshness ---
        if weather_age_hours > self.max_stale_weather_hours:
            confidence = "LOW"
            degraded = True
            checks.append(
                SafetyRuleCheck(
                    "S02",
                    "Data Freshness",
                    False,
                    f"Weather snapshot is {weather_age_hours:.1f}h old (threshold: {self.max_stale_weather_hours}h)",
                )
            )
            overrides.append("Degraded confidence due to stale weather data.")
        else:
            checks.append(SafetyRuleCheck("S02", "Data Freshness", True, "Weather data is current"))

        # --- S10: Severe Depletion Protection (Wilting prevention) ---
        severe_threshold = self.severe_depletion_fraction * taw_mm
        if depletion_mm >= severe_threshold and action == "SKIP":
            action = "IRRIGATE"
            outcome = SafetyOutcome.MODIFIED
            net_depth = min(depletion_mm, self.max_daily_depth_mm)
            duration = max(duration, self.min_recommended_duration_minutes)
            checks.append(
                SafetyRuleCheck(
                    "S10",
                    "Severe Depletion Protection",
                    False,
                    f"Depletion ({depletion_mm:.1f} mm) >= {severe_threshold:.1f} mm (severe stress). Override SKIP to IRRIGATE.",
                )
            )
            overrides.append("Severe water depletion detected; override to protect crop from permanent wilting.")
        else:
            checks.append(SafetyRuleCheck("S10", "Severe Depletion Protection", True, "No severe depletion risk"))

        # If action is IRRIGATE, run irrigation safety constraints
        if action == "IRRIGATE":
            # --- S03: Depletion Floor (Prevent unnecessary pumping) ---
            trigger_level = self.depletion_trigger_fraction * raw_mm
            if depletion_mm < trigger_level:
                action = "SKIP"
                net_depth = 0.0
                duration = 0
                outcome = SafetyOutcome.VETOED
                checks.append(
                    SafetyRuleCheck(
                        "S03",
                        "Depletion Floor",
                        False,
                        f"Depletion ({depletion_mm:.1f} mm) < trigger level ({trigger_level:.1f} mm). Veto unnecessary pumping.",
                    )
                )
                overrides.append("Root zone moisture is ample; irrigation vetoed to conserve groundwater.")
            else:
                checks.append(SafetyRuleCheck("S03", "Depletion Floor", True, "Depletion meets irrigation threshold"))

            # --- S04: Rain-skip condition ---
            if action == "IRRIGATE" and forecast_rain_48h_effective_mm > 0:
                required_need = max(depletion_mm, 5.0)
                rain_coverage = forecast_rain_48h_effective_mm / required_need
                # Only trust rain forecast if data is not severely stale (S11)
                if rain_coverage >= self.rainfall_skip_fraction and not degraded:
                    action = "SKIP"
                    net_depth = 0.0
                    duration = 0
                    outcome = SafetyOutcome.MODIFIED if outcome != SafetyOutcome.VETOED else outcome
                    checks.append(
                        SafetyRuleCheck(
                            "S04",
                            "Rainfall Skip",
                            False,
                            f"Forecast effective rain ({forecast_rain_48h_effective_mm:.1f} mm) covers {rain_coverage * 100:.0f}% of need. Skipping irrigation.",
                        )
                    )
                    overrides.append("Significant rainfall expected; irrigation safely skipped.")
                else:
                    checks.append(
                        SafetyRuleCheck(
                            "S04",
                            "Rainfall Skip",
                            True,
                            f"Forecast rain ({forecast_rain_48h_effective_mm:.1f} mm) insufficient to replace irrigation",
                        )
                    )

            # --- S05: Minimum Interval between events ---
            if action == "IRRIGATE" and hours_since_last_irrigation is not None:
                if hours_since_last_irrigation < self.min_interval_hours:
                    action = "SKIP"
                    net_depth = 0.0
                    duration = 0
                    outcome = SafetyOutcome.VETOED
                    checks.append(
                        SafetyRuleCheck(
                            "S05",
                            "Minimum Interval",
                            False,
                            f"Only {hours_since_last_irrigation:.1f}h since last irrigation (minimum: {self.min_interval_hours}h). Veto back-to-back watering.",
                        )
                    )
                    overrides.append("Recent irrigation event recorded within 24 hours; back-to-back watering vetoed.")
                else:
                    checks.append(SafetyRuleCheck("S05", "Minimum Interval", True, "Interval requirement satisfied"))

            # --- S07: Maximum Daily Irrigation Depth Cap ---
            if action == "IRRIGATE" and net_depth > self.max_daily_depth_mm:
                overrides.append(
                    f"Net depth capped from {net_depth:.1f} mm to daily maximum {self.max_daily_depth_mm:.1f} mm."
                )
                net_depth = self.max_daily_depth_mm
                outcome = SafetyOutcome.MODIFIED
                checks.append(
                    SafetyRuleCheck(
                        "S07", "Max Daily Depth", False, f"Net depth capped at {self.max_daily_depth_mm} mm"
                    )
                )
            elif action == "IRRIGATE":
                checks.append(SafetyRuleCheck("S07", "Max Daily Depth", True, "Net depth within daily cap"))

            # --- S09: Field-Capacity Protection ---
            if action == "IRRIGATE" and net_depth > depletion_mm and depletion_mm > 0:
                overrides.append(
                    f"Net depth adjusted from {net_depth:.1f} mm to current depletion {depletion_mm:.1f} mm to prevent leaching/runoff."
                )
                net_depth = depletion_mm
                outcome = SafetyOutcome.MODIFIED
                checks.append(
                    SafetyRuleCheck("S09", "Field Capacity", False, "Depth capped to current depletion deficit")
                )
            elif action == "IRRIGATE":
                checks.append(SafetyRuleCheck("S09", "Field Capacity", True, "No over-filling beyond field capacity"))

            # --- S06: Maximum Duration Cap ---
            if action == "IRRIGATE" and duration > self.max_duration_minutes:
                overrides.append(
                    f"Pump duration capped from {duration} min to maximum safety limit {self.max_duration_minutes} min."
                )
                duration = self.max_duration_minutes
                outcome = SafetyOutcome.MODIFIED
                checks.append(
                    SafetyRuleCheck(
                        "S06", "Max Duration Cap", False, f"Duration capped at {self.max_duration_minutes} min"
                    )
                )
            elif action == "IRRIGATE":
                checks.append(SafetyRuleCheck("S06", "Max Duration Cap", True, "Duration within event cap"))

            # --- S08: Crop-Stage Restriction (seedling stage protection) ---
            if action == "IRRIGATE" and stage_id == "initial":
                seedling_cap = 30
                if duration > seedling_cap:
                    duration = seedling_cap
                    overrides.append("Initial seedling stage; duration capped at 30 min to prevent root suffocation.")
                    outcome = SafetyOutcome.MODIFIED
                    checks.append(
                        SafetyRuleCheck("S08", "Crop Stage Restriction", False, "Capped for tender seedling roots")
                    )
                else:
                    checks.append(SafetyRuleCheck("S08", "Crop Stage Restriction", True, "Stage restriction checked"))

            # Enforce minimum recommended duration if irrigating
            if action == "IRRIGATE" and duration < self.min_recommended_duration_minutes:
                duration = self.min_recommended_duration_minutes

        # --- S12: Window Sanity Check ---
        # Ensure morning window (06:00 IST) is maintained to prevent high mid-day evaporative loss
        start_time = "06:00"
        checks.append(SafetyRuleCheck("S12", "Window Sanity", True, "Recommended for cool morning window (06:00 IST)"))

        msg = (
            f"Action: {action}. Safety Outcome: {outcome.value}. "
            + (f"Overrides: {'; '.join(overrides)}" if overrides else "All agronomic constraints satisfied.")
        )

        return SafetyEvaluationResult(
            action=action,
            original_action=proposed_action,
            outcome=outcome,
            final_net_depth_mm=round(net_depth, 1),
            final_duration_minutes=duration,
            final_start_time_ist=start_time,
            confidence_level=confidence,
            degraded=degraded,
            applied_overrides=overrides,
            rules_evaluated=checks,
            safety_message=msg,
        )
