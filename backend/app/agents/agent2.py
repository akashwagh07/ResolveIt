"""Agent 2: Deterministic decision and command generation engine."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..commands import CreateComplaintCommand
from ..engines.department import department_for_category
from ..engines.priority import PriorityResult, compute_priority
from ..engines.severity import SeverityResult, compute_severity
from .agent1 import Agent1Result


class Agent2Input(BaseModel):
    """Input parameters provided to Agent 2."""
    agent1: Optional[Agent1Result] = None
    citizen_name: str
    citizen_contact: str
    raw_text: str
    language: str = "en"
    latitude: float
    longitude: float
    address_text: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    ai_unavailable: bool = False


class Agent2Decision(BaseModel):
    """Deterministic output decision and generated executable command from Agent 2."""
    command: CreateComplaintCommand
    outcome: Literal["CLASSIFIED", "HUMAN_REVIEW", "OUT_OF_SCOPE", "MERGED"]
    severity: SeverityResult
    priority: PriorityResult
    department_code: str
    needs_review: bool
    review_reasons: List[str]
    trace: List[str]


CONFIDENCE_THRESHOLDS = {
    "high_confidence": 0.85,
    "review_threshold": 0.60,
}


def decide(db: Session, inp: Agent2Input) -> Agent2Decision:
    """
    Deterministically decide outcome, compute severity and priority, route department,
    and build a validated CreateComplaintCommand without making any LLM calls.
    
    Decision order:
    1. ai_unavailable -> HUMAN_REVIEW (category/issue OTHER, confidence 0.0)
    2. civic_relevance LOW -> OUT_OF_SCOPE (score 0, level LOW, priority NORMAL)
    3. category OTHER (relevance MEDIUM or HIGH) -> HUMAN_REVIEW
    4. confidence < 0.60 -> HUMAN_REVIEW
    5. Otherwise -> CLASSIFIED (needs_review flagged for 0.60 to 0.84)
    """
    trace: List[str] = []
    review_reasons: List[str] = []

    a1 = inp.agent1
    a1_out = a1.output if a1 else None

    # Resolve address text: citizen provided address_text wins, then Agent 1 location address_text
    address_text = (inp.address_text or "").strip()
    if not address_text and a1 and a1.location and a1.location.address_text:
        address_text = a1.location.address_text.strip()
    if not address_text:
        address_text = f"Coordinates: {inp.latitude:.5f}, {inp.longitude:.5f}"

    # Structured summary: Agent 1 description or first 200 chars of raw_text
    structured_summary = ""
    if a1_out and a1_out.description:
        structured_summary = a1_out.description
    elif inp.raw_text:
        structured_summary = inp.raw_text[:200].strip()
    else:
        structured_summary = "Citizen civic complaint."

    # 1. AI Unavailable
    if inp.ai_unavailable or a1 is None or a1_out is None:
        outcome = "HUMAN_REVIEW"
        category = "OTHER"
        issue = "OTHER"
        confidence = 0.0
        civic_relevance = "MEDIUM"
        needs_review = True
        review_reasons.append("AI unavailable")
        trace.append("AI analysis was unavailable; routed to HUMAN_REVIEW with default fallback classification.")

        sev = compute_severity("OTHER", "OTHER")
        prio = compute_priority(sev.level)
        dept = department_for_category(db, "OTHER")
        dept_code = dept.code

    # 2. Civic relevance LOW -> OUT_OF_SCOPE
    elif a1_out.civic_relevance == "LOW":
        outcome = "OUT_OF_SCOPE"
        category = a1_out.category or "OTHER"
        issue = a1_out.issue or "OTHER"
        confidence = float(a1_out.confidence)
        civic_relevance = "LOW"
        needs_review = False
        rel_reason = a1_out.relevance_reason or "Non-civic issue"
        trace.append(f"Civic relevance evaluated as LOW: {rel_reason}. Marked OUT_OF_SCOPE.")

        sev = SeverityResult(
            score=0,
            level="LOW",
            factors=[{"factor": "non_civic", "points": 0, "reason": rel_reason}],
        )
        prio = PriorityResult(
            priority="NORMAL",
            factors=[{"factor": "out_of_scope", "priority": "NORMAL", "reason": "Non-civic issue defaulted to NORMAL priority"}],
        )
        dept = department_for_category(db, "OTHER")
        dept_code = dept.code

    # 3. Category OTHER (with relevance MEDIUM or HIGH) -> HUMAN_REVIEW
    elif a1_out.category == "OTHER":
        outcome = "HUMAN_REVIEW"
        category = "OTHER"
        issue = a1_out.issue or "OTHER"
        confidence = float(a1_out.confidence)
        civic_relevance = a1_out.civic_relevance
        needs_review = True
        review_reasons.append("Category OTHER flagged for human review")
        trace.append("Category classified as OTHER; routed to HUMAN_REVIEW for manual departmental triage.")

        sev = compute_severity(
            category="OTHER",
            issue="OTHER",
            size_hint=a1_out.size_hint,
            duration_days=a1_out.duration_days,
            context_tags=a1_out.context_tags,
        )
        prio = compute_priority(sev.level, context_tags=a1_out.context_tags)
        dept = department_for_category(db, "OTHER")
        dept_code = dept.code

    # 4. Confidence below 0.60 -> HUMAN_REVIEW
    elif a1_out.confidence < CONFIDENCE_THRESHOLDS["review_threshold"]:
        outcome = "HUMAN_REVIEW"
        category = a1_out.category
        issue = a1_out.issue
        confidence = float(a1_out.confidence)
        civic_relevance = a1_out.civic_relevance
        needs_review = True
        reason_msg = f"Confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLDS['review_threshold']}"
        review_reasons.append(reason_msg)
        trace.append(f"Low confidence classification ({confidence:.2f} < 0.60); routed to HUMAN_REVIEW.")

        sev = compute_severity(
            category=category,
            issue=issue,
            size_hint=a1_out.size_hint,
            duration_days=a1_out.duration_days,
            context_tags=a1_out.context_tags,
        )
        prio = compute_priority(sev.level, context_tags=a1_out.context_tags)
        dept = department_for_category(db, category)
        dept_code = dept.code

    # 5. Otherwise -> CLASSIFIED
    else:
        outcome = "CLASSIFIED"
        category = a1_out.category
        issue = a1_out.issue
        confidence = float(a1_out.confidence)
        civic_relevance = a1_out.civic_relevance
        dept = department_for_category(db, category)
        dept_code = dept.code

        sev = compute_severity(
            category=category,
            issue=issue,
            size_hint=a1_out.size_hint,
            duration_days=a1_out.duration_days,
            context_tags=a1_out.context_tags,
        )
        prio = compute_priority(sev.level, context_tags=a1_out.context_tags)

        # Flag review if in review band [0.60, 0.84]
        if confidence < CONFIDENCE_THRESHOLDS["high_confidence"]:
            needs_review = True
            review_reasons.append(f"Confidence {confidence:.2f} flagged for review (band [0.60, 0.84])")
            trace.append(f"Confidence {confidence:.2f} falls into review band [0.60, 0.84]; flagged for review.")
        else:
            needs_review = False
            trace.append(f"High confidence {confidence:.2f} qualifies for automated classification.")

        trace.append(f"Classified into category '{category}', issue '{issue}'.")
        trace.append(f"Computed severity score {sev.score} ({sev.level}) and priority {prio.priority}.")
        trace.append(f"Assigned to department '{dept.name}' ({dept.code}).")

    # Build ai_reasoning metadata
    ai_reasoning: Dict[str, Any] = {
        "thresholds_used": CONFIDENCE_THRESHOLDS,
        "decision_trace": trace,
        "review_reasons": review_reasons,
    }
    if a1_out:
        ai_reasoning.update({
            "category": a1_out.category,
            "issue": a1_out.issue,
            "confidence": a1_out.confidence,
            "confidence_reason": a1_out.confidence_reason,
            "civic_relevance": a1_out.civic_relevance,
            "relevance_reason": a1_out.relevance_reason,
            "size_hint": a1_out.size_hint,
            "context_tags": a1_out.context_tags,
            "alternatives": [alt.model_dump() for alt in a1_out.alternatives],
            "observations": [obs.model_dump() for obs in a1_out.observations],
            "transcript": a1_out.transcript,
            "translation_en": a1_out.translation_en,
        })
    if a1:
        ai_reasoning.update({
            "model_used": a1.model_used,
            "cached": a1.cached,
            "warnings": a1.warnings,
            "latency_ms": a1.latency_ms,
        })

    # Assemble CreateComplaintCommand
    cmd = CreateComplaintCommand(
        citizen_name=inp.citizen_name,
        citizen_contact=inp.citizen_contact,
        raw_text=inp.raw_text,
        language=inp.language,
        latitude=inp.latitude,
        longitude=inp.longitude,
        address_text=address_text,
        category=category,
        issue=issue,
        category_confidence=confidence,
        civic_relevance=civic_relevance,
        credibility=0.90 if a1 else None,
        severity_score=sev.score,
        severity_level=sev.level,
        priority=prio.priority,
        severity_factors=sev.factors,
        priority_factors=prio.factors,
        department_code=dept_code,
        structured_summary=structured_summary,
        ai_reasoning=ai_reasoning,
        missing_info=a1_out.missing_info if a1_out else [],
        evidence=inp.evidence,
        outcome=outcome,
    )

    return Agent2Decision(
        command=cmd,
        outcome=outcome,
        severity=sev,
        priority=prio,
        department_code=dept_code,
        needs_review=needs_review,
        review_reasons=review_reasons,
        trace=trace,
    )
