from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Complaint, ComplaintEvent, Department, Evidence
from ..pipeline import PipelineError, SubmissionError, SubmissionPayload, process_submission
from ..schemas import ComplaintDetail, ComplaintEventSchema, ComplaintSummary

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
    except PipelineError as pe:
        raise HTTPException(status_code=500, detail=str(pe))

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
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    citizen_contact: Optional[str] = Query(None, description="Filter by citizen contact"),
    limit: int = Query(50, ge=1, le=200, description="Max complaints to return"),
    db: Session = Depends(get_db),
):
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    if category:
        query = query.filter(Complaint.category == category)
    if department_id:
        query = query.filter(Complaint.department_id == department_id)
    if citizen_contact:
        query = query.filter(Complaint.citizen_contact == citizen_contact)

    return query.order_by(Complaint.created_at.desc()).limit(limit).all()


@router.get("/api/complaints/{id}", response_model=ComplaintDetail)
def get_complaint(id: str, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint with id '{id}' not found",
        )
    return complaint


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
