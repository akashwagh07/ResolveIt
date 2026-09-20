"""Action layer mapping high-level user actions to validated executor commands."""

from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .auth import ActorContext
from .commands import Actor
from .executor import execute_command
from .models import Complaint


ACTIONS: Dict[str, Dict[str, Any]] = {
    "accept": {
        "label": "Accept for Review",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"CLASSIFIED"},
        "requires": [],
    },
    "confirm_classification": {
        "label": "Confirm Classification",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"HUMAN_REVIEW"},
        "requires": [],
    },
    "reject_out_of_scope": {
        "label": "Reject as Out of Scope",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"HUMAN_REVIEW"},
        "requires": ["reason"],
    },
    "assign": {
        "label": "Assign Officer",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"CLASSIFIED", "UNDER_REVIEW"},
        "requires": ["officer_id"],
    },
    "start_work": {
        "label": "Start Work",
        "allowed_roles": {"OFFICER", "ADMIN"},
        "allowed_states": {"ASSIGNED"},
        "requires": [],
    },
    "approve_resolution": {
        "label": "Approve Resolution",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"ADMIN_VERIFICATION"},
        "requires": [],
    },
    "reject_resolution": {
        "label": "Reject Resolution",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"ADMIN_VERIFICATION"},
        "requires": ["reason"],
    },
    "confirm_resolution": {
        "label": "Confirm Resolution",
        "allowed_roles": {"CITIZEN"},
        "allowed_states": {"CITIZEN_CONFIRMATION"},
        "requires": [],
    },
    "dispute_resolution": {
        "label": "Dispute Resolution",
        "allowed_roles": {"CITIZEN"},
        "allowed_states": {"CITIZEN_CONFIRMATION"},
        "requires": ["reason"],
    },
    "resume_work": {
        "label": "Resume Work",
        "allowed_roles": {"OFFICER", "ADMIN"},
        "allowed_states": {"REOPENED"},
        "requires": [],
    },
    "de_escalate": {
        "label": "De-escalate",
        "allowed_roles": {"ADMIN"},
        "allowed_states": {"ESCALATED"},
        "requires": [],
    },
}


def available_actions(
    db: Session, complaint: Complaint, ctx: ActorContext
) -> List[Dict[str, Any]]:
    """
    Return actions the caller can take right now on this complaint.
    Honours role, state, assigned officer, and citizen contact.
    """
    available: List[Dict[str, Any]] = []

    for name, spec in ACTIONS.items():
        # 1. Role check
        if ctx.role not in spec["allowed_roles"]:
            continue

        # 2. State check
        if complaint.status not in spec["allowed_states"]:
            continue

        # 3. Officer assignment check for officer actions
        if ctx.role == "OFFICER":
            if name in {"start_work", "resume_work"}:
                if complaint.assigned_officer_id != ctx.user_id:
                    continue

        # 4. Citizen contact check for citizen actions
        if ctx.role == "CITIZEN":
            if name in {"confirm_resolution", "dispute_resolution"}:
                if complaint.citizen_contact != ctx.contact:
                    continue

        # 5. Escalation return check
        if name == "de_escalate":
            if not complaint.previous_status:
                continue

        available.append({
            "action": name,
            "label": spec["label"],
            "requires": spec["requires"],
        })

    return available


def execute_action(
    db: Session,
    complaint: Complaint,
    action_name: str,
    params: Dict[str, Any],
    ctx: ActorContext,
) -> Dict[str, Any]:
    """
    Validate permissions and state, build command dict, and execute via execute_command.
    Never writes to database directly.
    """
    spec = ACTIONS.get(action_name)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown action '{action_name}'",
        )

    # 1. Role check
    if ctx.role not in spec["allowed_roles"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{ctx.role}' is not authorized to perform action '{action_name}'",
        )

    # 2. Specific identity constraints
    if ctx.role == "OFFICER" and action_name in {"start_work", "resume_work"}:
        if complaint.assigned_officer_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Officer {ctx.user_id} is not assigned to complaint '{complaint.id}'",
            )

    if ctx.role == "CITIZEN" and action_name in {"confirm_resolution", "dispute_resolution"}:
        if complaint.citizen_contact != ctx.contact:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizen contact does not match complaint record",
            )

    # 3. State check
    if complaint.status not in spec["allowed_states"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Action '{action_name}' is not allowed for complaint in status "
                f"'{complaint.status}' (allowed: {sorted(list(spec['allowed_states']))})"
            ),
        )

    # 4. Required parameters check
    for req in spec["requires"]:
        val = params.get(req)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required parameter '{req}' for action '{action_name}'",
            )

    actor_str = Actor.ADMIN if ctx.role == "ADMIN" else (
        Actor.OFFICER if ctx.role == "OFFICER" else Actor.CITIZEN
    )
    actor_ref_val = str(ctx.user_id) if ctx.user_id is not None else ctx.contact

    # 5. Build and execute command
    if action_name == "accept":
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "UNDER_REVIEW",
            "reason": "Admin accepted complaint for department review",
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Complaint accepted for review",
        }

    elif action_name == "confirm_classification":
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "CLASSIFIED",
            "reason": "Admin confirmed manual classification",
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Classification confirmed",
        }

    elif action_name == "reject_out_of_scope":
        reason = str(params["reason"]).strip()
        cmd = {
            "command": "MARK_OUT_OF_SCOPE",
            "complaint_id": complaint.id,
            "reason": reason,
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Complaint marked out of scope",
        }

    elif action_name == "assign":
        try:
            officer_id = int(params["officer_id"])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parameter 'officer_id' must be an integer",
            )
        note = params.get("note")

        # Two-step execution if complaint is CLASSIFIED
        if complaint.status == "CLASSIFIED":
            step1_cmd = {
                "command": "CHANGE_STATUS",
                "complaint_id": complaint.id,
                "new_status": "UNDER_REVIEW",
                "reason": "Admin accepted complaint prior to assignment",
            }
            res1 = execute_command(db, step1_cmd, Actor.ADMIN, actor_ref=actor_ref_val)
            if not res1.ok:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Accept step failed: {res1.error}",
                )

        assign_cmd = {
            "command": "ASSIGN",
            "complaint_id": complaint.id,
            "officer_id": officer_id,
            "note": note,
        }
        res2 = execute_command(db, assign_cmd, Actor.ADMIN, actor_ref=actor_ref_val)
        if not res2.ok:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Accept step succeeded, but assignment failed: {res2.error}"
                    if complaint.status == "UNDER_REVIEW"
                    else res2.error
                ),
            )
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": f"Assigned to officer {officer_id}",
        }

    elif action_name == "start_work":
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "IN_PROGRESS",
            "reason": f"{ctx.role} started work",
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Work started",
        }

    elif action_name == "approve_resolution":
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "CITIZEN_CONFIRMATION",
            "reason": "Admin approved resolution evidence",
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Resolution approved",
        }

    elif action_name == "reject_resolution":
        reason = str(params["reason"]).strip()
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "IN_PROGRESS",
            "reason": reason,
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Resolution rejected, complaint returned to IN_PROGRESS",
        }

    elif action_name == "confirm_resolution":
        cmd = {
            "command": "CLOSE",
            "complaint_id": complaint.id,
            "closure_reason": "CITIZEN_CONFIRMED",
        }
        res = execute_command(db, cmd, Actor.CITIZEN, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Resolution confirmed, complaint resolved",
        }

    elif action_name == "dispute_resolution":
        reason = str(params["reason"]).strip()
        cmd = {
            "command": "REOPEN",
            "complaint_id": complaint.id,
            "reason": reason,
        }
        res = execute_command(db, cmd, Actor.CITIZEN, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Resolution disputed, complaint reopened",
        }

    elif action_name == "resume_work":
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": "IN_PROGRESS",
            "reason": f"{ctx.role} resumed work on reopened complaint",
        }
        res = execute_command(db, cmd, actor_str, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": "Work resumed",
        }

    elif action_name == "de_escalate":
        if not complaint.previous_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complaint has no recorded previous_status to return to",
            )
        cmd = {
            "command": "CHANGE_STATUS",
            "complaint_id": complaint.id,
            "new_status": complaint.previous_status,
            "reason": "Admin de-escalated complaint to previous status",
        }
        res = execute_command(db, cmd, Actor.ADMIN, actor_ref=actor_ref_val)
        if not res.ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.error)
        return {
            "ok": True,
            "complaint_id": complaint.id,
            "status": complaint.status,
            "message": f"De-escalated back to {complaint.previous_status}",
        }

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unhandled action '{action_name}'",
    )
