"""Deterministic department routing engine."""

from typing import Optional
from sqlalchemy.orm import Session
from ..models import Department
from ..ontology import normalize_code

TRIAGE_DEPARTMENT_CODE = "SANITATION"


def department_for_category(db: Session, category: str) -> Department:
    """
    Return the municipal Department responsible for the given civic category.

    Rules:
    - Looks up the Department whose `categories` JSON list contains the canonical category.
    - Category "OTHER" routes to TRIAGE_DEPARTMENT_CODE ("SANITATION").
    - If no department matches, falls back to TRIAGE_DEPARTMENT_CODE.
    - OUT_OF_SCOPE complaints route to TRIAGE_DEPARTMENT_CODE.
    """
    cat_norm = normalize_code(category)

    if cat_norm == "OTHER":
        triage_dept = db.query(Department).filter_by(code=TRIAGE_DEPARTMENT_CODE).first()
        if triage_dept:
            return triage_dept

    # Search departments whose categories list contains cat_norm
    # Because categories is stored as JSON in SQLite, fetch and check in python or via query
    all_depts = db.query(Department).all()
    for dept in all_depts:
        cats = dept.categories or []
        if cat_norm in cats:
            return dept

    # Fallback to triage department
    triage = db.query(Department).filter_by(code=TRIAGE_DEPARTMENT_CODE).first()
    if triage:
        return triage

    # Fallback to first department in database if triage not found
    first_dept = db.query(Department).first()
    if first_dept:
        return first_dept

    raise RuntimeError(
        f"No department found for category '{category}' and no triage department seeded"
    )
