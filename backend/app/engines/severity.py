"""Deterministic severity scoring and priority mapping."""

from typing import Dict

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
