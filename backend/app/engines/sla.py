"""Deterministic SLA timing engine."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

SLA_TABLE: Dict[str, Dict[str, int]] = {
    "NORMAL": {"initial_response": 48, "follow_up": 72, "escalation": 96},
    "STANDARD": {"initial_response": 24, "follow_up": 48, "escalation": 72},
    "HIGH": {"initial_response": 12, "follow_up": 24, "escalation": 48},
    "EMERGENCY": {"initial_response": 2, "follow_up": 6, "escalation": 12},
}


def sla_hours(priority: str, department: Optional[Any] = None) -> Dict[str, int]:
    """Return SLA hours for priority, respecting department override if present."""
    norm_priority = priority.strip().upper()
    default_sla = SLA_TABLE.get(norm_priority, SLA_TABLE["NORMAL"])

    if department:
        dept_sla = getattr(department, "sla_hours", None)
        if isinstance(department, dict):
            dept_sla = department.get("sla_hours")

        if dept_sla and isinstance(dept_sla, dict) and norm_priority in dept_sla:
            override = dept_sla[norm_priority]
            if isinstance(override, dict):
                return {**default_sla, **override}

    return default_sla


def initial_deadline(
    reference_time: datetime,
    priority: str,
    department: Optional[Any] = None,
) -> datetime:
    """Calculate the initial response deadline from a reference timestamp."""
    hours = sla_hours(priority, department)["initial_response"]
    return reference_time + timedelta(hours=hours)
