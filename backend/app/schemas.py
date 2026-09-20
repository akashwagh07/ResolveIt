from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class DepartmentSchema(BaseModel):
    id: int
    code: str
    name: str
    categories: list[str]
    escalation_chain: list[str]
    sla_hours: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintEventSchema(BaseModel):
    id: int
    complaint_id: str
    timestamp: datetime
    actor: str
    action: str
    detail: Optional[Any] = None
    reasoning: Optional[str] = None
    confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceSchema(BaseModel):
    id: int
    complaint_id: str
    type: str
    role: str
    file_path: str
    phash: Optional[str] = None
    uploaded_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintSummary(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    citizen_name: str
    citizen_contact: str
    raw_text: str
    language: str
    latitude: float
    longitude: float
    address_text: str
    category: str
    issue: str
    category_confidence: float
    civic_relevance: str
    credibility: Optional[float] = None
    severity_score: int
    severity_level: str
    priority: str
    department_id: int
    assigned_officer_id: Optional[int] = None
    needs_review: bool = False
    review_reason: Optional[str] = None
    status: str
    previous_status: Optional[str] = None
    escalation_level: int
    sla_deadline: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintDetail(ComplaintSummary):
    severity_factors: dict[str, Any] = {}
    priority_factors: dict[str, Any] = {}
    structured_summary: Optional[str] = None
    ai_reasoning: Optional[dict[str, Any]] = None
    missing_info: Optional[list[str]] = None
    cluster_id: Optional[int] = None
    duplicate_of: Optional[str] = None
    duplicate_count: int = 0
    last_followup_at: Optional[datetime] = None
    events: list[ComplaintEventSchema] = []
    evidence: list[EvidenceSchema] = []

    model_config = ConfigDict(from_attributes=True)
