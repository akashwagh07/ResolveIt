import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Complaint, ComplaintEvent, Department, Evidence, Resolution, User
from ..pipeline import PipelineError, SubmissionError, SubmissionPayload, process_submission
from ..schemas import ComplaintDetail, ComplaintEventSchema, ComplaintSummary

logger = logging.getLogger("resolveit.complaints")

router = APIRouter(tags=["complaints"])


class ComplaintCreateResponse(BaseModel):
    complaint_id: str
    status: str
    needs_review: bool
    category: str
    issue: str
    confidence: float
    summary: str
    severity: Dict[str, Any]
    priority: Dict[str, Any]
    department: Dict[str, Any]
    trace: List[str]


@router.post("/api/complaints", status_code=201, response_model=ComplaintCreateResponse)
def create_complaint(
    citizen_name: str = Form(...),
    citizen_contact: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    text: Optional[str] = Form(None),
    language: str = Form("en"),
    address_text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Intake citizen complaint with optional media attachments.
    Processes submission through Agent 1 and Agent 2, executes CreateComplaintCommand,
    and returns 201 with full classification, routing, and decision breakdown.
    """
    has_text = bool(text and text.strip())
    uploads: List[tuple[str, UploadFile]] = []
    if image and image.filename:
        uploads.append(("IMAGE", image))
    if audio and audio.filename:
        uploads.append(("AUDIO", audio))
    if video and video.filename:
        uploads.append(("VIDEO", video))

    if not has_text and not uploads:
        raise HTTPException(
            status_code=422,
            detail="Complaint submission must contain either text or at least one media file.",
        )

    payload = SubmissionPayload(
        citizen_name=citizen_name,
        citizen_contact=citizen_contact,
        text=text,
        language=language,
        latitude=latitude,
        longitude=longitude,
        address_text=address_text,
    )

    try:
        res = process_submission(db, payload, uploads)
    except SubmissionError as se:
        raise HTTPException(status_code=422, detail=str(se))
    except (PipelineError, Exception):
        logger.exception("Unexpected error occurred in complaint intake")
        raise HTTPException(
            status_code=500,
            detail="Internal error while processing the complaint",
        )

    dept = db.query(Department).filter_by(code=res.decision.department_code).first()
    dept_info = {
        "id": dept.id if dept else None,
        "code": res.decision.department_code,
        "name": dept.name if dept else res.decision.department_code,
    }

    return ComplaintCreateResponse(
        complaint_id=res.complaint_id,
        status=res.status,
        needs_review=res.needs_review,
        category=res.decision.command.category,
        issue=res.decision.command.issue,
        confidence=res.decision.command.category_confidence,
        summary=res.decision.command.structured_summary,
        severity={
            "score": res.decision.severity.score,
            "level": res.decision.severity.level,
            "factors": res.decision.severity.factors,
        },
        priority={
            "value": res.decision.priority.priority,
            "factors": res.decision.priority.factors,
        },
        department=dept_info,
        trace=res.decision_trace,
    )


@router.get("/api/evidence/{id}/file")
def get_evidence_file(id: int, db: Session = Depends(get_db)):
    """Serve uploaded complaint evidence file securely without path traversal."""
    ev = db.query(Evidence).filter_by(id=id).first()
    if not ev or not ev.file_path:
        raise HTTPException(status_code=404, detail="Evidence not found")

    settings = get_settings()
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    file_path = Path(ev.file_path).resolve()

    # Prevent directory traversal outside UPLOAD_DIR
    try:
        file_path.relative_to(upload_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="File outside allowed directory")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    return FileResponse(file_path)


@router.get("/api/complaints", response_model=List[ComplaintSummary])
def list_complaints(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    assigned_officer_id: Optional[str] = Query(None, description="Filter by assigned officer ID"),
    needs_review: Optional[str] = Query(None, description="Filter by needs_review (bool)"),
    citizen_contact: Optional[str] = Query(None, description="Filter by citizen contact"),
    limit: int = Query(50, ge=1, le=200, description="Max complaints to return"),
    db: Session = Depends(get_db),
):
    query = db.query(Complaint)
    if status and status.strip():
        query = query.filter(Complaint.status == status.strip())
    if category and category.strip():
        query = query.filter(Complaint.category == category.strip())
    if department_id and department_id.strip():
        try:
            dept_int = int(department_id.strip())
            query = query.filter(Complaint.department_id == dept_int)
        except ValueError:
            pass
    if assigned_officer_id and str(assigned_officer_id).strip():
        try:
            off_int = int(str(assigned_officer_id).strip())
            query = query.filter(Complaint.assigned_officer_id == off_int)
        except ValueError:
            pass
    if needs_review is not None and str(needs_review).strip():
        nr_lower = str(needs_review).strip().lower()
        if nr_lower in ("true", "1"):
            query = query.filter(Complaint.needs_review.is_(True))
        elif nr_lower in ("false", "0"):
            query = query.filter(Complaint.needs_review.is_(False))
    if citizen_contact and citizen_contact.strip():
        query = query.filter(Complaint.citizen_contact == citizen_contact.strip())

    return query.order_by(Complaint.created_at.desc()).limit(limit).all()


@router.get("/api/complaints/{id}", response_model=ComplaintDetail)
def get_complaint(id: str, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint with id '{id}' not found",
        )

    assigned_officer_info = None
    if complaint.assigned_officer:
        assigned_officer_info = {
            "id": complaint.assigned_officer.id,
            "name": complaint.assigned_officer.name,
        }

    dept_info = None
    if complaint.department:
        dept_info = {
            "id": complaint.department.id,
            "code": complaint.department.code,
            "name": complaint.department.name,
        }

    before_ev = [
        {"id": ev.id, "url": f"/api/evidence/{ev.id}/file"}
        for ev in complaint.evidence
        if ev.role == "COMPLAINT" and ev.type == "IMAGE"
    ]

    res_list = (
        db.query(Resolution)
        .filter_by(complaint_id=complaint.id)
        .order_by(Resolution.created_at.asc())
        .all()
    )
    resolutions_data = []
    for r in res_list:
        off_name = None
        if r.officer_id:
            off_u = db.query(User).filter_by(id=r.officer_id).first()
            if off_u:
                off_name = off_u.name
        after_ev = [
            {"id": ev.id, "url": f"/api/evidence/{ev.id}/file"}
            for ev in complaint.evidence
            if ev.role == "RESOLUTION_AFTER"
        ]
        resolutions_data.append({
            "id": r.id,
            "created_at": r.created_at,
            "description": r.description,
            "officer_name": off_name,
            "ai_verdict": r.ai_verdict,
            "ai_confidence": r.ai_confidence,
            "admin_decision": r.admin_decision,
            "citizen_decision": r.citizen_decision,
            "after_evidence": after_ev,
        })

    return {
        "id": complaint.id,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "citizen_name": complaint.citizen_name,
        "citizen_contact": complaint.citizen_contact,
        "raw_text": complaint.raw_text,
        "language": complaint.language,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "address_text": complaint.address_text,
        "category": complaint.category,
        "issue": complaint.issue,
        "category_confidence": complaint.category_confidence,
        "civic_relevance": complaint.civic_relevance,
        "credibility": complaint.credibility,
        "severity_score": complaint.severity_score,
        "severity_level": complaint.severity_level,
        "priority": complaint.priority,
        "department_id": complaint.department_id,
        "assigned_officer_id": complaint.assigned_officer_id,
        "needs_review": complaint.needs_review,
        "review_reason": complaint.review_reason,
        "status": complaint.status,
        "previous_status": complaint.previous_status,
        "escalation_level": complaint.escalation_level,
        "sla_deadline": complaint.sla_deadline,
        "resolved_at": complaint.resolved_at,
        "severity_factors": complaint.severity_factors or [],
        "priority_factors": complaint.priority_factors or [],
        "structured_summary": complaint.structured_summary,
        "ai_reasoning": complaint.ai_reasoning or {},
        "missing_info": complaint.missing_info or [],
        "cluster_id": complaint.cluster_id,
        "duplicate_of": complaint.duplicate_of,
        "duplicate_count": complaint.duplicate_count,
        "last_followup_at": complaint.last_followup_at,
        "events": complaint.events,
        "evidence": complaint.evidence,
        "assigned_officer": assigned_officer_info,
        "department": dept_info,
        "resolutions": resolutions_data,
        "before_evidence": before_ev,
    }


@router.get("/api/complaints/{id}/events", response_model=List[ComplaintEventSchema])
def get_complaint_events(id: str, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint with id '{id}' not found",
        )
    return (
        db.query(ComplaintEvent)
        .filter(ComplaintEvent.complaint_id == id)
        .order_by(ComplaintEvent.timestamp.asc(), ComplaintEvent.id.asc())
        .all()
    )
