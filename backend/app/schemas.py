from __future__ import annotations
from datetime import datetime
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    url: Optional[str] = None
    phash: Optional[str] = None
    uploaded_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_url(self) -> "EvidenceSchema":
        if self.id and not self.url:
            self.url = f"/api/evidence/{self.id}/file"
        return self


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


class OfficerSummary(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class DepartmentSummary(BaseModel):
    id: int
    code: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class EvidenceItem(BaseModel):
    id: int
    url: str
    model_config = ConfigDict(from_attributes=True)


class ResolutionDetail(BaseModel):
    id: int
    created_at: datetime
    description: str
    officer_name: Optional[str] = None
    ai_verdict: Optional[dict[str, Any]] = None
    ai_confidence: float = 0.0
    admin_decision: Optional[str] = None
    citizen_decision: Optional[str] = None
    after_evidence: list[EvidenceItem] = []
    model_config = ConfigDict(from_attributes=True)


class ComplaintDetail(ComplaintSummary):
    severity_factors: Union[list[dict[str, Any]], dict[str, Any]] = Field(default_factory=list)
    priority_factors: Union[list[dict[str, Any]], dict[str, Any]] = Field(default_factory=list)
    structured_summary: Optional[str] = None
    ai_reasoning: Optional[dict[str, Any]] = None
    missing_info: Optional[list[str]] = None
    cluster_id: Optional[int] = None
    duplicate_of: Optional[str] = None
    duplicate_count: int = 0
    last_followup_at: Optional[datetime] = None
    events: list[ComplaintEventSchema] = []
    evidence: list[EvidenceSchema] = []
    assigned_officer: Optional[OfficerSummary] = None
    department: Optional[DepartmentSummary] = None
    resolutions: list[ResolutionDetail] = []
    before_evidence: list[EvidenceItem] = []

    model_config = ConfigDict(from_attributes=True)
