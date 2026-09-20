"""Citizen intake pipeline orchestrating Agent 1, Agent 2, command execution, and audit logging."""

from dataclasses import asdict
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .agents.agent1 import Agent1Input, Agent1Result, run_agent1
from .agents.agent2 import Agent2Decision, Agent2Input, decide
from .commands import Actor
from .config import get_settings
from .events import log_event
from .executor import execute_command
from .llm import MEDIA_WHITELIST, LLMConfigError, LLMError, LLMUnavailableError, MediaError, load_media

logger = logging.getLogger("resolveit.pipeline")


class SubmissionError(Exception):
    """Raised when citizen intake submission is invalid (mapped to HTTP 422)."""
    pass


class PipelineError(Exception):
    """Raised when backend pipeline processing fails (mapped to HTTP 500)."""
    pass


class SubmissionPayload(BaseModel):
    citizen_name: str
    citizen_contact: str
    text: Optional[str] = None
    language: str = "en"
    latitude: float
    longitude: float
    address_text: Optional[str] = None


class PipelineResult(BaseModel):
    complaint_id: str
    status: str
    needs_review: bool
    decision_trace: List[str]
    agent1_summary: Optional[Dict[str, Any]] = None
    execution_result: Dict[str, Any]
    decision: Agent2Decision


def process_submission(
    db: Session,
    submission: SubmissionPayload,
    uploads: Optional[List[tuple[str, UploadFile]]] = None,
) -> PipelineResult:
    """
    Process citizen complaint submission through Agent 1 and Agent 2 pipeline.

    1. Validates and saves uploaded media into UPLOAD_DIR/incoming/<batch_id>/ with whitelisted extensions.
    2. Runs Agent 1 classification (or falls back to ai_unavailable on LLM errors).
    3. Runs Agent 2 deterministic decision engine to produce CreateComplaintCommand.
    4. Executes command through execute_command(db, cmd, Actor.AGENT2).
    5. Appends audit events for AGENT1 (CLASSIFY) and AGENT2 (DECIDE), then commits.
    """
    settings = get_settings()
    upload_root = Path(settings.UPLOAD_DIR)
    batch_id = str(uuid.uuid4())
    incoming_dir = upload_root / "incoming" / batch_id

    saved_paths: List[str] = []
    evidence_items: List[Dict[str, Any]] = []

    # 1. Process and save uploaded files
    if uploads:
        incoming_dir.mkdir(parents=True, exist_ok=True)
        for expected_kind, upload_file in uploads:
            if not upload_file or not upload_file.filename:
                continue

            orig_ext = Path(upload_file.filename).suffix.lower()
            if orig_ext not in MEDIA_WHITELIST:
                # Cleanup and abort
                for sp in saved_paths:
                    Path(sp).unlink(missing_ok=True)
                supported = ", ".join(MEDIA_WHITELIST.keys())
                raise SubmissionError(
                    f"Unsupported media extension '{orig_ext}'. Allowed extensions: {supported}"
                )

            # Generate random destination filename (never use client's filename)
            random_filename = f"{uuid.uuid4().hex}{orig_ext}"
            dest_path = incoming_dir / random_filename

            try:
                content = upload_file.file.read()
                dest_path.write_bytes(content)
                saved_paths.append(str(dest_path.resolve()))

                # Validate with load_media immediately
                part = load_media(dest_path, expected_kind=expected_kind)
                evidence_items.append({
                    "type": part.kind,
                    "file_path": str(dest_path.resolve()),
                })
            except MediaError as me:
                # Delete any saved files and raise 422
                for sp in saved_paths:
                    Path(sp).unlink(missing_ok=True)
                raise SubmissionError(f"Media validation error: {me}")
            except Exception as exc:
                for sp in saved_paths:
                    Path(sp).unlink(missing_ok=True)
                raise SubmissionError(f"Failed to save uploaded file: {exc}")

    # Validate that either text or at least one file was provided
    has_text = bool(submission.text and submission.text.strip())
    has_files = len(evidence_items) > 0
    if not has_text and not has_files:
        for sp in saved_paths:
            Path(sp).unlink(missing_ok=True)
        raise SubmissionError("Submission must contain either text or at least one attached media file.")

    try:
        # 2. Run Agent 1
        a1_result: Optional[Agent1Result] = None
        in_cooldown = False
        start_a1 = time.monotonic()
        try:
            a1_input = Agent1Input(
                text=submission.text,
                language_hint=submission.language,
                latitude=submission.latitude,
                longitude=submission.longitude,
                address_text=submission.address_text,
                media_paths=saved_paths,
            )
            a1_result = run_agent1(a1_input, use_cache=True)
            elapsed_ms = (time.monotonic() - start_a1) * 1000.0
            logger.info("Agent 1 classification finished in %.1f ms", elapsed_ms)
        except LLMUnavailableError as unavail_err:
            in_cooldown = True
            elapsed_ms = (time.monotonic() - start_a1) * 1000.0
            logger.warning(
                "Agent 1 skipped due to quota cooldown after %.1f ms (%s); proceeding with ai_unavailable=True",
                elapsed_ms,
                unavail_err,
            )
            a1_result = None
        except (LLMError, LLMConfigError) as llm_err:
            elapsed_ms = (time.monotonic() - start_a1) * 1000.0
            logger.warning(
                "Agent 1 failed after %.1f ms (%s); proceeding with ai_unavailable=True",
                elapsed_ms,
                llm_err,
            )
            a1_result = None

        # 3. Call Agent 2
        a2_input = Agent2Input(
            agent1=a1_result,
            citizen_name=submission.citizen_name,
            citizen_contact=submission.citizen_contact,
            raw_text=submission.text or "[Media upload only]",
            language=submission.language,
            latitude=submission.latitude,
            longitude=submission.longitude,
            address_text=submission.address_text,
            evidence=evidence_items,
            ai_unavailable=(a1_result is None),
            ai_unavailable_reason="quota cooldown" if in_cooldown else None,
        )
        decision = decide(db, a2_input)

        # 4. Execute CreateComplaintCommand
        exec_res = execute_command(db, decision.command, Actor.AGENT2)
        if not exec_res.ok:
            logger.error("Pipeline command execution rejected: %s", exec_res.error)
            raise PipelineError(f"Command execution rejected: {exec_res.error}")

        complaint_id = exec_res.complaint_id or ""

        # 5. Write audit events for AGENT1 and AGENT2
        a1_summary_dict: Optional[Dict[str, Any]] = None
        if a1_result:
            a1_summary_dict = {
                "category": a1_result.output.category,
                "issue": a1_result.output.issue,
                "confidence": a1_result.output.confidence,
                "description": a1_result.output.description,
                "civic_relevance": a1_result.output.civic_relevance,
            }
            log_event(
                db,
                complaint_id=complaint_id,
                actor="AGENT1",
                action="CLASSIFY",
                detail=a1_summary_dict,
                confidence=a1_result.output.confidence,
            )
        else:
            audit_reason = "AI unavailable (quota cooldown)" if in_cooldown else "AI unavailable"
            log_event(
                db,
                complaint_id=complaint_id,
                actor="AGENT1",
                action="CLASSIFY",
                detail={"error": audit_reason},
                reasoning=audit_reason,
                confidence=0.0,
            )

        a2_summary_dict = {
            "severity_score": decision.severity.score,
            "severity_level": decision.severity.level,
            "priority": decision.priority.priority,
            "department_code": decision.department_code,
            "outcome": decision.outcome,
            "trace": decision.trace,
        }
        log_event(
            db,
            complaint_id=complaint_id,
            actor="AGENT2",
            action="DECIDE",
            detail=a2_summary_dict,
        )

        db.commit()
    except Exception as exc:
        for sp in saved_paths:
            Path(sp).unlink(missing_ok=True)
        if isinstance(exc, (SubmissionError, PipelineError)):
            raise
        logger.exception("Pipeline execution failed unexpectedly")
        raise PipelineError("Internal error while processing the complaint") from exc

    return PipelineResult(
        complaint_id=complaint_id,
        status=exec_res.new_status or decision.outcome,
        needs_review=decision.needs_review,
        decision_trace=decision.trace,
        agent1_summary=a1_summary_dict,
        execution_result=asdict(exec_res),
        decision=decision,
    )
