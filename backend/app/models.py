from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .clock import now as clock_now
from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    escalation_chain: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sla_hours: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)

    users: Mapped[List[User]] = relationship("User", back_populates="department")
    complaints: Mapped[List[Complaint]] = relationship("Complaint", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # CITIZEN | OFFICER | ADMIN
    contact: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)

    department: Mapped[Optional[Department]] = relationship("Department", back_populates="users")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # DUPLICATE | ROOT_CAUSE
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, onupdate=clock_now, nullable=False)
    citizen_name: Mapped[str] = mapped_column(String(100), nullable=False)
    citizen_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address_text: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    issue: Mapped[str] = mapped_column(String(100), nullable=False)
    category_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    civic_relevance: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)
    credibility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity_level: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL", nullable=False)
    severity_factors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    priority_factors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SUBMITTED", index=True, nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    structured_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_reasoning: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    missing_info: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=list)
    cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clusters.id"), nullable=True)
    duplicate_of: Mapped[Optional[str]] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    department: Mapped[Department] = relationship("Department", back_populates="complaints")
    evidence: Mapped[List[Evidence]] = relationship("Evidence", back_populates="complaint", cascade="all, delete-orphan")
    events: Mapped[List[ComplaintEvent]] = relationship("ComplaintEvent", back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintEvent.timestamp")
    resolutions: Mapped[List[Resolution]] = relationship("Resolution", back_populates="complaint", cascade="all, delete-orphan")
    escalations: Mapped[List[Escalation]] = relationship("Escalation", back_populates="complaint", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # IMAGE | AUDIO | VIDEO
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # COMPLAINT | RESOLUTION_BEFORE | RESOLUTION_AFTER
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    phash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)

    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="evidence")


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    officer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ai_verdict: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    admin_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    citizen_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)

    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="resolutions")


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    dossier: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)

    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="escalations")


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=clock_now, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[Optional[dict[str, Any] | list[Any]]] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    complaint: Mapped[Complaint] = relationship("Complaint", back_populates="events")
