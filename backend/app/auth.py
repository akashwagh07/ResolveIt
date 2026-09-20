"""Demo-grade identity and authentication dependency for ResolveIt."""

from dataclasses import dataclass
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User


@dataclass
class ActorContext:
    role: str  # CITIZEN | OFFICER | ADMIN
    user_id: Optional[int] = None
    contact: Optional[str] = None
    user: Optional[User] = None


def get_actor_context(
    x_demo_role: Optional[str] = Header(None, alias="X-Demo-Role"),
    x_demo_user_id: Optional[int] = Header(None, alias="X-Demo-User-Id"),
    x_demo_passcode: Optional[str] = Header(None, alias="X-Demo-Passcode"),
    x_citizen_contact: Optional[str] = Header(None, alias="X-Citizen-Contact"),
    db: Session = Depends(get_db),
) -> ActorContext:
    """
    Resolve demo caller identity from request headers.

    - CITIZEN requires X-Demo-Role: CITIZEN and X-Citizen-Contact.
    - OFFICER and ADMIN require X-Demo-Role, X-Demo-User-Id, and X-Demo-Passcode.
    - Returns 401 for missing/invalid credentials, 403 for role mismatch.
    - Never logs or exposes passcodes.
    """
    if not x_demo_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required header 'X-Demo-Role'",
        )

    norm_role = x_demo_role.strip().upper()
    if norm_role not in {"CITIZEN", "OFFICER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid X-Demo-Role '{x_demo_role}'. Allowed: CITIZEN, OFFICER, ADMIN",
        )

    settings = get_settings()

    if norm_role == "CITIZEN":
        if not x_citizen_contact or not x_citizen_contact.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing required header 'X-Citizen-Contact' for CITIZEN role",
            )
        return ActorContext(
            role="CITIZEN",
            user_id=None,
            contact=x_citizen_contact.strip(),
            user=None,
        )

    # OFFICER or ADMIN
    if x_demo_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required header 'X-Demo-User-Id' for {norm_role} role",
        )

    if not x_demo_passcode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required header 'X-Demo-Passcode' for {norm_role} role",
        )

    expected_passcode = settings.OFFICER_PASSCODE
    if not secrets.compare_digest(x_demo_passcode, expected_passcode):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passcode",
        )

    user = db.query(User).filter_by(id=x_demo_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Demo user id {x_demo_user_id} not found",
        )

    if user.role != norm_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {x_demo_user_id} has registered role '{user.role}', not '{norm_role}'",
        )

    return ActorContext(
        role=norm_role,
        user_id=user.id,
        contact=user.contact,
        user=user,
    )
