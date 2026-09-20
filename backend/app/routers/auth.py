"""Authentication and user discovery endpoints for ResolveIt demo identity."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import ActorContext, get_actor_context
from ..database import get_db
from ..models import User

router = APIRouter(tags=["auth"])


class DepartmentIdentity(BaseModel):
    id: int
    code: str
    name: str


class WhoAmIResponse(BaseModel):
    name: str
    role: str
    contact: Optional[str] = None
    department: Optional[DepartmentIdentity] = None


class DemoUserItem(BaseModel):
    id: int
    name: str
    role: str
    department_id: Optional[int] = None


@router.get("/api/auth/whoami", response_model=WhoAmIResponse)
def whoami(ctx: ActorContext = Depends(get_actor_context)):
    """Return the resolved identity for the caller based on demo headers."""
    dept_info: Optional[DepartmentIdentity] = None
    name = "Citizen"

    if ctx.user:
        name = ctx.user.name
        if ctx.user.department:
            dept_info = DepartmentIdentity(
                id=ctx.user.department.id,
                code=ctx.user.department.code,
                name=ctx.user.department.name,
            )

    return WhoAmIResponse(
        name=name,
        role=ctx.role,
        contact=ctx.contact,
        department=dept_info,
    )


@router.get("/api/users", response_model=List[DemoUserItem])
def list_demo_users(
    role: Optional[str] = Query(None, description="Filter demo users by role (OFFICER or ADMIN)"),
    db: Session = Depends(get_db),
):
    """List seeded demo accounts (no contact details) for role picker selection."""
    query = db.query(User).filter(User.role.in_(["OFFICER", "ADMIN"]))
    if role and role.strip():
        norm_role = role.strip().upper()
        query = query.filter(User.role == norm_role)

    users = query.order_by(User.id.asc()).all()
    return [
        DemoUserItem(
            id=u.id,
            name=u.name,
            role=u.role,
            department_id=u.department_id,
        )
        for u in users
    ]
