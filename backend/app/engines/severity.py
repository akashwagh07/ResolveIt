"""Deterministic severity scoring and priority mapping."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from ..ontology import normalize_code, resolve_alias

PRIORITY_FOR_LEVEL: Dict[str, str] = {
    "LOW": "NORMAL",
    "MEDIUM": "STANDARD",
    "HIGH": "HIGH",
    "CRITICAL": "EMERGENCY",
}


def severity_level_for_score(score: int) -> str:
    """Return severity level band for a given numeric score (0-10)."""
    if score <= 2:
        return "LOW"
    elif score <= 4:
        return "MEDIUM"
    elif score <= 7:
        return "HIGH"
    else:
        return "CRITICAL"


# Base risk values (0-5) keyed by canonical issue code from ontology.py
BASE_RISK: Dict[str, int] = {
    # ROADS
    "POTHOLE": 3,
    "ROAD_DAMAGE": 3,
    "ROAD_CRACKS": 1,
    "ROAD_DEBRIS": 2,
    "DAMAGED_SPEED_BREAKER": 2,
    "FOOTPATH_DAMAGE": 2,
    "BLOCKED_FOOTPATH": 1,
    "MISSING_ROAD_SIGN": 2,
    # STREET_LIGHTING
    "LIGHT_NOT_WORKING": 2,
    "FLICKERING_LIGHT": 1,
    "DAMAGED_POLE": 3,
    "FALLEN_POLE": 5,
    "EXPOSED_WIRING": 5,
    "INSUFFICIENT_LIGHTING": 1,
    # WASTE
    "GARBAGE_NOT_COLLECTED": 2,
    "OVERFLOWING_BIN": 2,
    "ILLEGAL_DUMPING": 2,
    "GARBAGE_ON_ROAD": 2,
    "CONSTRUCTION_WASTE": 2,
    "MISSED_COLLECTION": 1,
    "DEAD_ANIMAL": 3,
    "ANIMAL_CARCASS": 3,
    # WATER
    "NO_WATER_SUPPLY": 3,
    "LOW_WATER_PRESSURE": 1,
    "WATER_LEAKAGE": 2,
    "PIPELINE_BURST": 4,
    "CONTAMINATED_WATER": 4,
    "WATER_OVERFLOW": 2,
    "BROKEN_PUBLIC_TAP": 1,
    # DRAINAGE
    "BLOCKED_DRAIN": 2,
    "DRAIN_OVERFLOW": 3,
    "SEWAGE_LEAKAGE": 3,
    "SEWAGE_OVERFLOW": 4,
    "BLOCKED_MANHOLE": 2,
    "MISSING_MANHOLE_COVER": 5,
    "WATERLOGGING": 3,
    "STAGNANT_WATER": 2,
    # PARKS_ENVIRONMENT
    "FALLEN_TREE": 4,
    "DANGEROUS_BRANCH": 3,
    "TREE_MAINTENANCE": 1,
    "DAMAGED_PLAYGROUND": 2,
    "DAMAGED_PARK": 1,
    "UNCLEAN_PARK": 1,
    "ILLEGAL_TREE_CUTTING": 2,
    # ENCROACHMENT
    "ROAD_ENCROACHMENT": 1,
    "FOOTPATH_ENCROACHMENT": 1,
    "ILLEGAL_CONSTRUCTION": 2,
    "UNAUTHORIZED_STRUCTURE": 1,
    "CONSTRUCTION_OBSTRUCTION": 1,
    "UNAUTHORIZED_EXCAVATION": 3,
    # ANIMALS
    "STRAY_DOG": 2,
    "STRAY_CATTLE": 2,
    "AGGRESSIVE_ANIMAL": 4,
    "INJURED_ANIMAL": 3,
    "ANIMAL_TRAFFIC_OBSTRUCTION": 2,
    # TRAFFIC
    "TRAFFIC_SIGNAL_FAILURE": 4,
    "DAMAGED_TRAFFIC_SIGN": 2,
    "MISSING_TRAFFIC_SIGN": 2,
    "UNSAFE_CROSSING": 3,
    "TRAFFIC_OBSTRUCTION": 2,
    "PARKING_OBSTRUCTION": 1,
    # SANITATION
    "PUBLIC_TOILET_ISSUE": 2,
    "FOUL_SMELL": 1,
    "MOSQUITO_BREEDING": 3,
    "PEST_PROBLEM": 2,
    "UNCLEAN_PUBLIC_AREA": 1,
    "UNHYGIENIC_CONDITION": 2,
    # OTHER
    "ANYTHING_ELSE": 1,
    "OTHER": 1,
}


class SeverityResult(BaseModel):
    score: int
    level: str
    factors: List[Dict[str, Any]]


def compute_severity(
    category: str,
    issue: str,
    size_hint: Optional[str] = None,
    duration_days: Optional[float] = None,
    context_tags: Optional[List[str]] = None,
) -> SeverityResult:
    """
    Deterministically compute severity score (0-10), band level, and factor breakdown.
    
    Components:
     a) base issue risk 0-5 from BASE_RISK (unmapped issues default to 2)
     b) public safety 0-2: SAFETY_HAZARD gives +2, otherwise HEALTH_HAZARD gives +1
     c) affected area 0-2: size_hint LARGE +2, MEDIUM +1
     d) traffic/population 0-2: +1 if any of MAJOR_ROAD, TRANSIT_AREA, TRAFFIC_IMPACT; +1 if HIGH_PEDESTRIAN
     e) duration 0-2: duration_days >= 14 gives +2, >= 7 gives +1
     f) context 0-1: +1 if SCHOOL_NEARBY or HOSPITAL_NEARBY
    """
    factors: List[Dict[str, Any]] = []
    cat_norm, iss_norm = resolve_alias(category, issue)

    # a) Base risk (0-5)
    base_score = BASE_RISK.get(iss_norm, 2)
    factors.append({
        "factor": "base_risk",
        "points": base_score,
        "reason": f"Baseline risk for issue {iss_norm}",
    })

    tags = set(context_tags or [])

    # b) Public safety (0-2)
    if "SAFETY_HAZARD" in tags:
        factors.append({
            "factor": "public_safety",
            "points": 2,
            "reason": "Direct safety hazard flagged",
        })
    elif "HEALTH_HAZARD" in tags:
        factors.append({
            "factor": "public_safety",
            "points": 1,
            "reason": "Public health hazard flagged",
        })

    # c) Affected area (0-2)
    norm_size = (size_hint or "").strip().upper()
    if norm_size == "LARGE":
        factors.append({
            "factor": "affected_area",
            "points": 2,
            "reason": "Large affected area or physical scope",
        })
    elif norm_size == "MEDIUM":
        factors.append({
            "factor": "affected_area",
            "points": 1,
            "reason": "Medium affected area or physical scope",
        })

    # d) Traffic / population (0-2)
    traffic_points = 0
    traffic_reasons = []
    if any(t in tags for t in ("MAJOR_ROAD", "TRANSIT_AREA", "TRAFFIC_IMPACT")):
        traffic_points += 1
        traffic_reasons.append("major road, transit area, or traffic disruption")
    if "HIGH_PEDESTRIAN" in tags:
        traffic_points += 1
        traffic_reasons.append("high pedestrian footfall zone")

    if traffic_points > 0:
        factors.append({
            "factor": "traffic_population",
            "points": traffic_points,
            "reason": "Impacts " + " and ".join(traffic_reasons),
        })

    # e) Duration (0-2)
    if duration_days is not None:
        if duration_days >= 14:
            factors.append({
                "factor": "duration",
                "points": 2,
                "reason": f"Unresolved for prolonged duration ({duration_days:.0f} days >= 14 days)",
            })
        elif duration_days >= 7:
            factors.append({
                "factor": "duration",
                "points": 1,
                "reason": f"Unresolved for extended duration ({duration_days:.0f} days >= 7 days)",
            })

    # f) Context (0-1)
    if "SCHOOL_NEARBY" in tags or "HOSPITAL_NEARBY" in tags:
        sensitive = []
        if "SCHOOL_NEARBY" in tags:
            sensitive.append("school")
        if "HOSPITAL_NEARBY" in tags:
            sensitive.append("hospital")
        factors.append({
            "factor": "sensitive_context",
            "points": 1,
            "reason": f"Located near sensitive facility ({', '.join(sensitive)})",
        })

    total_raw = sum(f["points"] for f in factors)
    final_score = max(0, min(10, total_raw))
    level = severity_level_for_score(final_score)

    return SeverityResult(
        score=final_score,
        level=level,
        factors=factors,
    )
