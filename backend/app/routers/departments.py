from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Department
from ..schemas import DepartmentSchema

router = APIRouter(tags=["departments"])


@router.get("/api/departments", response_model=List[DepartmentSchema])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).order_by(Department.id.asc()).all()
