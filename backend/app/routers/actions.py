"""Action execution and resolution upload endpoints."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..actions import available_actions, execute_action
from ..auth import ActorContext, get_actor_context
from ..commands import Actor
from ..config import get_settings
from ..database import get_db
from ..executor import execute_command
from ..llm import MEDIA_WHITELIST, MediaError, load_media
from ..models import Complaint, Evidence, Resolution
from ..verification import run_verification_hook

logger = logging.getLogger("resolveit.actions")

router = APIRouter(tags=["actions"])


class ActionInfo(BaseModel):
    action: str
    label: str
    requires: List[str] = []


class ActionResponse(BaseModel):
    ok: bool
    complaint_id: str
    status: str
    message: str


class ResolutionResponse(BaseModel):
    ok: bool
    status: str
    resolution_id: int


@router.get("/api/complaints/{id}/actions", response_model=List[ActionInfo])
def get_complaint_actions(
    id: str,
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db),
):
    """Return available actions for caller based on role, state, and assignment."""
    complaint = db.query(Complaint).filter_by(id=id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id '{id}' not found",
        )
    return available_actions(db, complaint, ctx)


@router.post("/api/complaints/{id}/actions/{action}", response_model=ActionResponse)
def execute_complaint_action(
    id: str,
    action: str,
    params: Dict[str, Any] = Body(default_factory=dict),
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db),
):
    """Execute permitted action on the complaint through the command gate."""
    complaint = db.query(Complaint).filter_by(id=id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id '{id}' not found",
        )
    return execute_action(db, complaint, action, params, ctx)


@router.post("/api/complaints/{id}/resolution", response_model=ResolutionResponse)
def submit_resolution(
    id: str,
    description: str = Form(...),
    after_images: List[UploadFile] = File(...),
    ctx: ActorContext = Depends(get_actor_context),
    db: Session = Depends(get_db),
):
    """
    Upload resolution description and after-evidence images (assigned OFFICER only).
    Executes SUBMIT_RESOLUTION and triggers automated verification hook.
    """
    # 1. Identity & role check
    if ctx.role != "OFFICER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned officers can upload resolution evidence",
        )

    complaint = db.query(Complaint).filter_by(id=id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id '{id}' not found",
        )

    if complaint.assigned_officer_id != ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Officer {ctx.user_id} is not assigned to complaint '{id}'",
        )

    if complaint.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit resolution for complaint in status '{complaint.status}' (expected IN_PROGRESS)",
        )

    # 2. Input validation
    desc_clean = description.strip()
    if len(desc_clean) < 10 or len(desc_clean) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resolution description must be between 10 and 1000 characters",
        )

    if not after_images or len(after_images) < 1 or len(after_images) > 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resolution must include between 1 and 4 evidence images",
        )

    settings = get_settings()
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target_dir = upload_root / "resolutions" / complaint.id
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []

    def _cleanup_files():
        for sp in saved_paths:
            try:
                sp.unlink(missing_ok=True)
            except Exception:
                pass

    try:
        evidence_rows: List[Evidence] = []
        for file in after_images:
            if not file.filename:
                _cleanup_files()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Uploaded image is missing a filename",
                )

            orig_ext = Path(file.filename).suffix.lower()
            if orig_ext not in MEDIA_WHITELIST or MEDIA_WHITELIST[orig_ext][0] != "IMAGE":
                _cleanup_files()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"File '{file.filename}' is not a supported image format",
                )

            # Random destination filename (never use client's filename)
            random_filename = f"{uuid.uuid4().hex}{orig_ext}"
            dest_path = target_dir / random_filename
            content = file.file.read()
            dest_path.write_bytes(content)
            saved_paths.append(dest_path)

            # Validate with load_media
            try:
                load_media(dest_path, expected_kind="IMAGE")
            except MediaError as me:
                _cleanup_files()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid image upload: {me}",
                )

            # Build relative path from UPLOAD_DIR
            rel_file_path = dest_path.relative_to(upload_root.parent).as_posix()
            ev = Evidence(
                complaint_id=complaint.id,
                type="IMAGE",
                role="RESOLUTION_AFTER",
                file_path=rel_file_path,
                uploaded_by=f"OFFICER:{ctx.user_id}",
            )
            db.add(ev)
            evidence_rows.append(ev)

        db.flush()
        after_evidence_ids = [ev.id for ev in evidence_rows]

        # 3. Execute SUBMIT_RESOLUTION command
        cmd = {
            "command": "SUBMIT_RESOLUTION",
            "complaint_id": complaint.id,
            "officer_id": ctx.user_id,
            "description": desc_clean,
            "after_evidence_ids": after_evidence_ids,
        }
        res = execute_command(db, cmd, Actor.OFFICER, actor_ref=str(ctx.user_id))
        if not res.ok:
            _cleanup_files()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Resolution submission failed: {res.error}",
            )

        # 4. Fetch the created resolution
        latest_res = (
            db.query(Resolution)
            .filter_by(complaint_id=complaint.id)
            .order_by(Resolution.created_at.desc())
            .first()
        )
        if not latest_res:
            _cleanup_files()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Resolution record was not created",
            )

        # 5. Run automated verification hook
        run_verification_hook(db, complaint, latest_res)

        return ResolutionResponse(
            ok=True,
            status=complaint.status,
            resolution_id=latest_res.id,
        )

    except HTTPException:
        _cleanup_files()
        raise
    except Exception as exc:
        _cleanup_files()
        logger.exception("Unexpected error during resolution submission: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit resolution",
        )
