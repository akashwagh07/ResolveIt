"""Canonical civic ontology mapping categories to issues."""

from typing import Dict, List

CATEGORIES: Dict[str, List[str]] = {
    "ROADS": [
        "POTHOLE",
        "ROAD_DAMAGE",
        "ROAD_CRACKS",
        "ROAD_DEBRIS",
        "DAMAGED_SPEED_BREAKER",
        "FOOTPATH_DAMAGE",
        "BLOCKED_FOOTPATH",
        "MISSING_ROAD_SIGN",
    ],
    "STREET_LIGHTING": [
        "LIGHT_NOT_WORKING",
        "FLICKERING_LIGHT",
        "DAMAGED_POLE",
        "FALLEN_POLE",
        "EXPOSED_WIRING",
        "INSUFFICIENT_LIGHTING",
    ],
    "WASTE": [
        "GARBAGE_NOT_COLLECTED",
        "OVERFLOWING_BIN",
        "ILLEGAL_DUMPING",
        "GARBAGE_ON_ROAD",
        "CONSTRUCTION_WASTE",
        "MISSED_COLLECTION",
        "DEAD_ANIMAL",
        "ANIMAL_CARCASS",  # alias for DEAD_ANIMAL
    ],
    "WATER": [
        "NO_WATER_SUPPLY",
        "LOW_WATER_PRESSURE",
        "WATER_LEAKAGE",
        "PIPELINE_BURST",
        "CONTAMINATED_WATER",
        "WATER_OVERFLOW",
        "BROKEN_PUBLIC_TAP",
    ],
    "DRAINAGE": [
        "BLOCKED_DRAIN",
        "DRAIN_OVERFLOW",
        "SEWAGE_LEAKAGE",
        "SEWAGE_OVERFLOW",
        "BLOCKED_MANHOLE",
        "MISSING_MANHOLE_COVER",
        "WATERLOGGING",
        "STAGNANT_WATER",
    ],
    "PARKS_ENVIRONMENT": [
        "FALLEN_TREE",
        "DANGEROUS_BRANCH",
        "TREE_MAINTENANCE",
        "DAMAGED_PLAYGROUND",
        "DAMAGED_PARK",
        "UNCLEAN_PARK",
        "ILLEGAL_TREE_CUTTING",
    ],
    "ENCROACHMENT": [
        "ROAD_ENCROACHMENT",
        "FOOTPATH_ENCROACHMENT",
        "ILLEGAL_CONSTRUCTION",
        "UNAUTHORIZED_STRUCTURE",
        "CONSTRUCTION_OBSTRUCTION",
        "UNAUTHORIZED_EXCAVATION",
    ],
    "ANIMALS": [
        "STRAY_DOG",
        "STRAY_CATTLE",
        "AGGRESSIVE_ANIMAL",
        "INJURED_ANIMAL",
        "ANIMAL_TRAFFIC_OBSTRUCTION",
    ],
    "TRAFFIC": [
        "TRAFFIC_SIGNAL_FAILURE",
        "DAMAGED_TRAFFIC_SIGN",
        "MISSING_TRAFFIC_SIGN",
        "UNSAFE_CROSSING",
        "TRAFFIC_OBSTRUCTION",
        "PARKING_OBSTRUCTION",
    ],
    "SANITATION": [
        "PUBLIC_TOILET_ISSUE",
        "FOUL_SMELL",
        "MOSQUITO_BREEDING",
        "PEST_PROBLEM",
        "UNCLEAN_PUBLIC_AREA",
        "UNHYGIENIC_CONDITION",
    ],
    "OTHER": [
        "ANYTHING_ELSE",
        "OTHER",
    ],
}


def normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "_").replace("-", "_")


def is_valid_issue(category: str, issue: str) -> bool:
    """Validate if an issue belongs to a category in the canonical ontology."""
    cat_norm = normalize_code(category)
    if cat_norm not in CATEGORIES:
        return False

    if cat_norm == "OTHER":
        return True

    iss_norm = normalize_code(issue)
    return iss_norm in CATEGORIES[cat_norm]
