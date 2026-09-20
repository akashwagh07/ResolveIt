from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Complaint, ComplaintEvent
from ..schemas import ComplaintDetail, ComplaintEventSchema, ComplaintSummary

router = APIRouter(tags=["complaints"])


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
