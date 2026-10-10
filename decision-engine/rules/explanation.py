"""Deterministic, Fact-Based Explanation Generator for KhetSathi.

Generates structured, traceable reasons in English and Hindi directly
from computed decision facts and triggered safety rules.
NO LLM is required or allowed in the core MVP path.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DecisionReason:
    rule_id: str
    code: str
    text_en: str
    text_hi: str


def generate_explanation(
    action: str,  # "IRRIGATE" or "SKIP"
    depletion_mm: float,
    raw_mm: float,
    taw_mm: float,
    forecast_rain_48h_mm: float,
    duration_minutes: int,
    start_time_ist: str,
    applied_overrides: List[str],
    is_rain_skip: bool = False,
    is_floor_veto: bool = False,
    is_interval_veto: bool = False,
    is_severe_stressed: bool = False,
    is_degraded: bool = False,
) -> List[DecisionReason]:
    """Build a deterministic list of reasons matching the actual computed facts."""
    reasons: List[DecisionReason] = []

    if action == "SKIP":
        if is_rain_skip:
            reasons.append(
                DecisionReason(
                    rule_id="R_RAIN_FORECAST",
                    code="ADEQUATE_RAIN_FORECAST",
                    text_en=f"Upcoming forecast rain ({forecast_rain_48h_mm:.1f} mm) is sufficient to fulfill crop water needs.",
                    text_hi=f"आगामी वर्षा का अनुमान ({forecast_rain_48h_mm:.1f} मिमी) फसल की जल आवश्यकता पूरी करने के लिए पर्याप्त है।",
                )
            )
            reasons.append(
                DecisionReason(
                    rule_id="R_MOISTURE_OK",
                    code="ROOT_MOISTURE_ADEQUATE",
                    text_en="Current root-zone moisture level remains adequate.",
                    text_hi="वर्तमान में पौधे के जड़ क्षेत्र में पर्याप्त नमी उपलब्ध है।",
                )
            )
            reasons.append(
                DecisionReason(
                    rule_id="R_AVOID_EXTRACTION",
                    code="UNNECESSARY_EXTRACTION_AVOIDED",
                    text_en="Skipping pumping conserves valuable groundwater and avoids excess waterlogging.",
                    text_hi="पंपिंग न करने से भूजल की बचत होती है और खेत में जलजमाव का जोखिम टलता है।",
                )
            )
        elif is_interval_veto:
            reasons.append(
                DecisionReason(
                    rule_id="R_MIN_INTERVAL",
                    code="RECENT_IRRIGATION_EVENT",
                    text_en="A confirmed irrigation event was completed recently (within 24 hours).",
                    text_hi="खेत में हाल ही में (24 घंटे के भीतर) सिंचाई की गई है।",
                )
            )
            reasons.append(
                DecisionReason(
                    rule_id="R_PREVENT_WATERLOGGING",
                    code="PREVENT_ROOT_SUFFOCATION",
                    text_en="Allowing soil aeration prevents root rot and saves unnecessary pump energy.",
                    text_hi="मिट्टी में हवा का संचार बना रहने से जड़ें स्वस्थ रहती हैं और बिजली की बचत होती है।",
                )
            )
        else:
            # Depletion floor / normal skip
            reasons.append(
                DecisionReason(
                    rule_id="R_DEPLETION_LOW",
                    code="DEPLETION_BELOW_THRESHOLD",
                    text_en=f"Root-zone depletion ({depletion_mm:.1f} mm) is well below the allowable stress threshold ({raw_mm:.1f} mm).",
                    text_hi=f"जड़ क्षेत्र में पानी की कमी ({depletion_mm:.1f} मिमी) सुरक्षित सीमा ({raw_mm:.1f} मिमी) से काफी नीचे है।",
                )
            )
            reasons.append(
                DecisionReason(
                    rule_id="R_SUFFICIENT_MOISTURE",
                    code="SOIL_MOISTURE_SUFFICIENT",
                    text_en="Soil retains ample accessible water for transpiration today.",
                    text_hi="पौधों के सामान्य विकास के लिए मिट्टी में अभी पर्याप्त नमी मौजूद है।",
                )
            )
            reasons.append(
                DecisionReason(
                    rule_id="R_CONSERVE_GROUNDWATER",
                    code="PUMPING_UNNECESSARY",
                    text_en="Additional pumping today is unnecessary and would cause drainage loss.",
                    text_hi="आज सिंचाई की आवश्यकता नहीं है; पंप न चलाकर पानी की बचत करें।",
                )
            )

    else:
        # action == "IRRIGATE"
        if is_severe_stressed:
            reasons.append(
                DecisionReason(
                    rule_id="R_SEVERE_STRESS",
                    code="SEVERE_DEPLETION_ALERT",
                    text_en=f"Root-zone water depletion ({depletion_mm:.1f} mm) has entered severe crop stress zone.",
                    text_hi=f"जड़ क्षेत्र में पानी की कमी ({depletion_mm:.1f} मिमी) गंभीर तनाव की स्थिति में पहुंच गई है।",
                )
            )
        else:
            reasons.append(
                DecisionReason(
                    rule_id="R_DEPLETION_HIGH",
                    code="WATER_NEED_HIGH",
                    text_en=f"Soil moisture depletion ({depletion_mm:.1f} mm) has reached the readily available water limit ({raw_mm:.1f} mm).",
                    text_hi=f"मिट्टी में नमी की कमी ({depletion_mm:.1f} मिमी) सिंचाई की आवश्यकता सीमा ({raw_mm:.1f} मिमी) तक पहुंच गई है।",
                )
            )

        if forecast_rain_48h_mm < 2.0:
            reasons.append(
                DecisionReason(
                    rule_id="R_NO_RAIN",
                    code="INSUFFICIENT_RAIN_FORECAST",
                    text_en="No significant rainfall is expected in the next 48 hours.",
                    text_hi="अगले 48 घंटों में बारिश की कोई संभावना नहीं है।",
                )
            )
        else:
            reasons.append(
                DecisionReason(
                    rule_id="R_PARTIAL_RAIN",
                    code="PARTIAL_RAIN_INSUFFICIENT",
                    text_en=f"Expected light rainfall ({forecast_rain_48h_mm:.1f} mm) is insufficient to meet crop water demand.",
                    text_hi=f"हल्की बारिश का अनुमान ({forecast_rain_48h_mm:.1f} मिमी) फसल की जरूरत को पूरा करने के लिए काफी नहीं है।",
                )
            )

        reasons.append(
            DecisionReason(
                rule_id="R_OPTIMAL_WINDOW",
                code="MORNING_WINDOW_CAP",
                text_en=f"Recommended at {start_time_ist} for {duration_minutes} minutes during cool morning hours to minimize evaporation.",
                text_hi=f"वाष्पीकरण रोकने के लिए सुबह {start_time_ist} बजे {duration_minutes} मिनट की सिंचाई अनुशंसित है।",
            )
        )

        if applied_overrides:
            for override in applied_overrides:
                reasons.append(
                    DecisionReason(
                        rule_id="R_SAFETY_OVERRIDE",
                        code="SAFETY_CONSTRAINT_APPLIED",
                        text_en=f"Agronomic safety constraint applied: {override}",
                        text_hi=f"कृषि सुरक्षा नियम लागू: {override}",
                    )
                )

    if is_degraded:
        reasons.append(
            DecisionReason(
                rule_id="R_DATA_DEGRADED",
                code="DATA_STALE_CONSERVATIVE_MODE",
                text_en="Weather data is older than normal; operating in safe conservative mode.",
                text_hi="मौसम का डेटा सामान्य से पुराना है; प्रणाली सुरक्षित मोड में कार्य कर रही है।",
            )
        )

    return reasons


def format_speech_script_hi(
    action: str,
    start_time_ist: str,
    duration_minutes: int,
    reasons: List[DecisionReason],
    crop_name_hi: str = "फसल",
) -> str:
    """Format an authentic, natural Hindi voice script for Amazon Polly."""
    if action == "SKIP":
        lines = [
            f"नमस्ते किसान साथी। आज आपकी {crop_name_hi} के लिए सिंचाई की आवश्यकता नहीं है। कृपया पंप बंद रखें।",
            "मुख्य कारण:",
        ]
        for r in reasons[:3]:
            lines.append(f"{r.text_hi}")
        lines.append("खेत साथी का उपयोग करने के लिए धन्यवाद।")
        return " ".join(lines)
    else:
        lines = [
            f"नमस्ते किसान साथी। आज आपकी {crop_name_hi} के लिए सिंचाई अनुशंसित है।",
            f"कृपया सुबह {start_time_ist} बजे, {duration_minutes} मिनट के लिए पंप चलाएं।",
            "मुख्य कारण:",
        ]
        for r in reasons[:3]:
            lines.append(f"{r.text_hi}")
        lines.append("सिंचाई पूरी होने के बाद कृपया डन बटन दबाएं।")
        return " ".join(lines)
