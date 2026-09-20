"""Deterministic priority calculation engine."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from .severity import PRIORITY_FOR_LEVEL

# Priority elevation order
PRIORITY_STEPS = ["NORMAL", "STANDARD", "HIGH", "EMERGENCY"]


class PriorityResult(BaseModel):
    priority: str
    factors: List[Dict[str, Any]]


def compute_priority(
    level: str,
    context_tags: Optional[List[str]] = None,
) -> PriorityResult:
    """
    Compute dynamic priority from severity level and contextual modifiers.

    Rules:
    - Base priority begins at PRIORITY_FOR_LEVEL[level]
    - If SCHOOL_NEARBY or HOSPITAL_NEARBY is present and level is MEDIUM or HIGH,
      bump the priority up one step (NORMAL -> STANDARD -> HIGH -> EMERGENCY)
    - LOW and CRITICAL never bump.
    - Designed for future pluggable modifiers (rain forecast, duplicate count, SLA age).
    """
    norm_level = (level or "LOW").strip().upper()
    base_priority = PRIORITY_FOR_LEVEL.get(norm_level, "NORMAL")
    factors: List[Dict[str, Any]] = [
        {
            "factor": "base_level",
            "priority": base_priority,
            "reason": f"Baseline priority mapped from {norm_level} severity",
        }
    ]

    current_priority = base_priority
    tags = set(context_tags or [])

    # Modifier: Sensitive locations (school / hospital)
    # Only bumps MEDIUM or HIGH severity
    if norm_level in ("MEDIUM", "HIGH"):
        if "SCHOOL_NEARBY" in tags or "HOSPITAL_NEARBY" in tags:
            try:
                curr_idx = PRIORITY_STEPS.index(current_priority)
                if curr_idx < len(PRIORITY_STEPS) - 1:
                    new_priority = PRIORITY_STEPS[curr_idx + 1]
                    current_priority = new_priority
                    sensitive = []
                    if "SCHOOL_NEARBY" in tags:
                        sensitive.append("school")
                    if "HOSPITAL_NEARBY" in tags:
                        sensitive.append("hospital")
                    factors.append({
                        "factor": "sensitive_facility_bump",
                        "priority": current_priority,
                        "adjustment": "+1 step",
                        "reason": f"Elevated priority due to proximity to {', '.join(sensitive)}",
                    })
            except ValueError:
                pass

    # Pluggable placeholder for future modifiers (e.g. rain_forecast, duplicate_cluster, sla_age)

    return PriorityResult(
        priority=current_priority,
        factors=factors,
    )
