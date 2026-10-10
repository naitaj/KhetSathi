"""Pure Python FAO-56 Root-Zone Water Balance Model for KhetSathi.

Contains zero external cloud/AWS dependencies.
Implements:
- Crop stage derivation and Kc interpolation
- Soil water parameters (TAW, RAW)
- Daily soil moisture depletion tracking
- Pump duration and gross extraction calculation
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    from config.loader import get_crops_config, get_soils_config, get_safety_config
except (ImportError, ValueError):
    from ..config.loader import get_crops_config, get_soils_config, get_safety_config


@dataclass(frozen=True)
class CropStageInfo:
    crop_id: str
    stage_id: str
    stage_name: str
    days_after_sowing: int
    kc: float
    root_depth_m: float
    allowable_depletion_p: float
    preferred_start_time_ist: str


@dataclass(frozen=True)
class WaterBalanceState:
    taw_mm: float
    raw_mm: float
    depletion_mm: float
    depletion_ratio: float  # Dr / TAW
    is_water_stressed: bool  # Dr >= RAW
    available_water_mm: float  # TAW - Dr


def derive_crop_stage(
    crop_id: str,
    days_after_sowing: int,
    crops_cfg: Optional[Dict[str, Any]] = None,
) -> CropStageInfo:
    """Derive current crop stage, Kc, and effective rooting depth from sowing date."""
    if crops_cfg is None:
        crops_cfg = get_crops_config()

    crops = crops_cfg.get("crops", {})
    crop = crops.get(crop_id.lower())
    if not crop:
        raise ValueError(f"Unsupported crop '{crop_id}'. Supported crops: {list(crops.keys())}")

    p = float(crop.get("allowable_depletion_p", 0.55))
    start_time = crop.get("preferred_start_time_ist", "06:00")
    stages = crop.get("stages", [])

    das = max(0, int(days_after_sowing))
    elapsed_days = 0

    for stage in stages:
        stage_days = stage["days"]
        stage_end = elapsed_days + stage_days

        if das <= stage_end or stage == stages[-1]:
            stage_id = stage["stage_id"]
            stage_name = stage["name"]

            # Linear interpolation for Kc and root depth within the stage
            progress = (das - elapsed_days) / max(1, stage_days)
            progress = min(max(progress, 0.0), 1.0)

            kc_start = stage.get("kc_start", stage.get("kc", 0.3))
            kc_end = stage.get("kc_end", kc_start)
            kc = round(kc_start + progress * (kc_end - kc_start), 3)

            rd_start = stage.get("root_depth_start_m", stage.get("root_depth_m", 0.3))
            rd_end = stage.get("root_depth_end_m", rd_start)
            root_depth = round(rd_start + progress * (rd_end - rd_start), 3)

            return CropStageInfo(
                crop_id=crop_id,
                stage_id=stage_id,
                stage_name=stage_name,
                days_after_sowing=das,
                kc=kc,
                root_depth_m=root_depth,
                allowable_depletion_p=p,
                preferred_start_time_ist=start_time,
            )

        elapsed_days += stage_days

    # Fallback to last stage
    last = stages[-1]
    return CropStageInfo(
        crop_id=crop_id,
        stage_id=last["stage_id"],
        stage_name=last["name"],
        days_after_sowing=das,
        kc=float(last.get("kc_end", 0.5)),
        root_depth_m=float(last.get("root_depth_end_m", 1.0)),
        allowable_depletion_p=p,
        preferred_start_time_ist=start_time,
    )


def calculate_effective_rainfall(
    rain_mm: float,
    effective_fraction: float = 0.80,
    min_threshold_mm: float = 2.0,
) -> float:
    """Calculate effective rainfall according to FAO guidelines.

    Precipitation below the threshold largely evaporates from the canopy/surface.
    """
    if rain_mm <= min_threshold_mm:
        return 0.0
    return round((rain_mm - min_threshold_mm) * effective_fraction, 2)


def calculate_water_capacity(
    soil_type: str,
    root_depth_m: float,
    p: float,
    soils_cfg: Optional[Dict[str, Any]] = None,
) -> Tuple[float, float]:
    """Compute Total Available Water (TAW) and Readily Available Water (RAW).

    TAW = 1000 * (FC - WP) * Zr (mm)
    RAW = p * TAW (mm)
    """
    if soils_cfg is None:
        soils_cfg = get_soils_config()

    soils = soils_cfg.get("soils", {})
    soil = soils.get(soil_type.lower())
    if not soil:
        # Default to loam if unspecified
        soil = soils.get("loam", {"field_capacity_fc": 0.27, "wilting_point_wp": 0.12})

    fc = float(soil["field_capacity_fc"])
    wp = float(soil["wilting_point_wp"])

    taw = round(1000.0 * (fc - wp) * max(0.1, root_depth_m), 2)
    raw = round(p * taw, 2)
    return taw, raw


def update_root_zone_depletion(
    dr_previous_mm: float,
    etc_mm: float,
    effective_rain_mm: float,
    net_irrigation_mm: float,
    taw_mm: float,
) -> float:
    """Update root-zone depletion (Dr) for the day.

    Dr,t = Dr,t-1 + ETc - Peff - Inet
    0 <= Dr <= TAW
    """
    dr = dr_previous_mm + etc_mm - effective_rain_mm - net_irrigation_mm
    dr_clamped = min(max(dr, 0.0), taw_mm)
    return round(dr_clamped, 2)


def calculate_irrigation_duration(
    net_depth_mm: float,
    area_ha: float,
    pump_flow_lpm: float,
    application_efficiency: float = 0.75,
    rounding_increment: int = 5,
) -> Tuple[float, int]:
    """Calculate gross volume in Litres and pump duration in minutes.

    1 mm depth over 1 m² = 1 Litre.
    Area m² = area_ha * 10,000.
    Gross volume = (net_depth_mm * Area m²) / application_efficiency.
    Duration (min) = gross_volume / pump_flow_lpm.
    """
    if net_depth_mm <= 0 or area_ha <= 0 or pump_flow_lpm <= 0:
        return 0.0, 0

    eff = max(0.1, min(application_efficiency, 1.0))
    area_m2 = area_ha * 10000.0
    net_volume_l = net_depth_mm * area_m2
    gross_volume_l = round(net_volume_l / eff, 1)

    raw_minutes = gross_volume_l / pump_flow_lpm
    # Round to nearest increment
    rounded_minutes = int(math.ceil(raw_minutes / rounding_increment) * rounding_increment)
    return gross_volume_l, rounded_minutes
