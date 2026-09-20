"""Command gate executor: validates and executes commands for complaints."""

from dataclasses import dataclass, field
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session

from .clock import now as clock_now
from .commands import (
    Actor,
    COMMAND_RULES,
    Command,
    CreateComplaintCommand,
    LinkClusterCommand,
    SetPriorityCommand,
    FlagHumanReviewCommand,
    MarkOutOfScopeCommand,
    AssignCommand,
    ChangeStatusCommand,
    SubmitResolutionCommand,
    RecordVerificationCommand,
    SendFollowupCommand,
    EscalateCommand,
    CloseCommand,
    ReopenCommand,
    parse_command,
)
from .confidence import gate
from .engines.sla import initial_deadline
from .events import log_event
from .models import (
    Cluster,
    CommandRejection,
    Complaint,
    Department,
    Escalation,
    Evidence,
    Resolution,
    User,
)
from .state_machine import ACTIVE_STATES, Status, transition


@dataclass
class ExecutionResult:
    ok: bool
    command: str
    complaint_id: Optional[str] = None
    new_status: Optional[str] = None
    error: Optional[str] = None
    event_ids: List[int] = field(default_factory=list)


# Section 4: Allowed moves for CHANGE_STATUS
CHANGE_STATUS_MOVES: Dict[tuple[Status, Status], set[Actor]] = {
    (Status.SUBMITTED, Status.AI_ANALYZING): {Actor.SYSTEM},
    (Status.CLASSIFIED, Status.UNDER_REVIEW): {Actor.ADMIN},
    (Status.HUMAN_REVIEW, Status.CLASSIFIED): {Actor.ADMIN},
    (Status.HUMAN_REVIEW, Status.OUT_OF_SCOPE): {Actor.ADMIN},
    (Status.ASSIGNED, Status.IN_PROGRESS): {Actor.OFFICER, Actor.ADMIN},
    (Status.RESOLUTION_SUBMITTED, Status.AI_VERIFICATION): {Actor.AGENT3, Actor.SYSTEM},
    (Status.ADMIN_VERIFICATION, Status.CITIZEN_CONFIRMATION): {Actor.ADMIN},
    (Status.ADMIN_VERIFICATION, Status.IN_PROGRESS): {Actor.ADMIN},
    (Status.REOPENED, Status.IN_PROGRESS): {Actor.ADMIN, Actor.OFFICER},
    (Status.ERROR, Status.AI_ANALYZING): {Actor.ADMIN, Actor.SYSTEM},
}


def _reject(
    db: Session,
    command_type: str,
    actor_str: str,
    payload: Dict[str, Any],
    reason: str,
    complaint_id: Optional[str] = None,
    current_status: Optional[str] = None,
) -> ExecutionResult:
    """Roll back uncommitted state, persist CommandRejection row, and return failure."""
    db.rollback()
    rejection = CommandRejection(
        complaint_id=complaint_id,
        command_type=command_type,
        actor=actor_str,
        payload=payload,
        reason=reason,
        created_at=clock_now(),
    )
    db.add(rejection)
    db.commit()
    return ExecutionResult(
        ok=False,
        command=command_type,
        complaint_id=complaint_id,
        new_status=current_status,
        error=reason,
        event_ids=[],
    )


def execute_command(
    db: Session,
    command: Union[Command, Dict[str, Any]],
    actor: Union[Actor, str],
    actor_ref: Optional[Any] = None,
) -> ExecutionResult:
    """Execute a single validated command against the database."""
    # 1. Parse payload if dictionary
    payload: Dict[str, Any]
    if isinstance(command, dict):
        payload = command
        try:
            cmd = parse_command(payload)
        except Exception as exc:
            cmd_type = str(payload.get("command", "UNKNOWN"))
            actor_name = actor.value if isinstance(actor, Actor) else str(actor)
            return _reject(
                db,
                command_type=cmd_type,
                actor_str=actor_name,
                payload=payload,
                reason=f"Failed to parse command: {exc}",
                complaint_id=payload.get("complaint_id"),
            )
    else:
        cmd = command
        payload = cmd.model_dump()

    # 2. Normalize actor
    try:
        act = Actor(actor) if isinstance(actor, str) else actor
    except ValueError:
        return _reject(
            db,
            command_type=cmd.command,
            actor_str=str(actor),
            payload=payload,
            reason=f"Unknown actor: {actor}",
            complaint_id=getattr(cmd, "complaint_id", None),
        )

    actor_str = act.value
    cmd_type = cmd.command

    # 3. Check actor permission from COMMAND_RULES
    rules = COMMAND_RULES.get(cmd_type)
    if not rules:
        return _reject(
            db,
            command_type=cmd_type,
            actor_str=actor_str,
            payload=payload,
            reason=f"No command rules defined for '{cmd_type}'",
        )

    if act not in rules["allowed_actors"]:
        return _reject(
            db,
            command_type=cmd_type,
            actor_str=actor_str,
            payload=payload,
            reason=f"Actor '{actor_str}' is not permitted to execute '{cmd_type}'",
            complaint_id=getattr(cmd, "complaint_id", None),
        )

    # 4. Lookup complaint (if required)
    complaint: Optional[Complaint] = None
    if rules["requires_existing"]:
        cid = getattr(cmd, "complaint_id", None)
        complaint = db.query(Complaint).filter_by(id=cid).first()
        if not complaint:
            return _reject(
                db,
                command_type=cmd_type,
                actor_str=actor_str,
                payload=payload,
                reason=f"Complaint with id '{cid}' not found",
                complaint_id=cid,
            )

        # 5. Check state requirement from COMMAND_RULES
        current_status = Status(complaint.status)
        allowed_states = rules["allowed_states"]
        if allowed_states and current_status not in allowed_states:
            return _reject(
                db,
                command_type=cmd_type,
                actor_str=actor_str,
                payload=payload,
                reason=f"Command '{cmd_type}' not allowed when status is '{current_status.value}'",
                complaint_id=complaint.id,
                current_status=complaint.status,
            )

        # 6. Actor ref identity checks
        if act == Actor.CITIZEN:
            if actor_ref is not None and str(actor_ref) != complaint.citizen_contact:
                return _reject(
                    db,
                    command_type=cmd_type,
                    actor_str=actor_str,
                    payload=payload,
                    reason=f"Citizen actor_ref does not match complaint contact '{complaint.citizen_contact}'",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

        if act == Actor.OFFICER and cmd_type == "SUBMIT_RESOLUTION":
            if actor_ref is not None and int(actor_ref) != complaint.assigned_officer_id:
                return _reject(
                    db,
                    command_type=cmd_type,
                    actor_str=actor_str,
                    payload=payload,
                    reason=f"Officer '{actor_ref}' is not the assigned officer for this complaint",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

    # 7. Apply specific command logic
    event_ids: List[int] = []

    try:
        if isinstance(cmd, CreateComplaintCommand):
            # Department lookup
            dept = db.query(Department).filter_by(code=cmd.department_code).first()
            if not dept:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Department '{cmd.department_code}' does not exist",
                )

            # Category check
            needs_rev = False
            rev_reason: Optional[str] = None
            if cmd.category == "OTHER":
                needs_rev = True
                rev_reason = "Category OTHER flagged for human review"
            elif cmd.category not in dept.categories:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Department '{dept.code}' does not handle category '{cmd.category}'",
                )

            # Confidence gate on category_confidence
            c_gate = gate(cmd.category_confidence)
            final_outcome = cmd.outcome
            if c_gate == "HUMAN":
                if final_outcome not in ("OUT_OF_SCOPE", "MERGED"):
                    final_outcome = "HUMAN_REVIEW"
                    needs_rev = True
                    rev_reason = f"Low confidence {cmd.category_confidence:.2f} routed to HUMAN_REVIEW"
            elif c_gate == "REVIEW":
                needs_rev = True
                rev_reason = f"Confidence {cmd.category_confidence:.2f} flagged for review"

            # Merge target verification
            parent_complaint: Optional[Complaint] = None
            if final_outcome == "MERGED":
                if not cmd.merge_into_id:
                    return _reject(db, cmd_type, actor_str, payload, "merge_into_id required for MERGED outcome")
                parent_complaint = db.query(Complaint).filter_by(id=cmd.merge_into_id).first()
                if not parent_complaint:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Target complaint '{cmd.merge_into_id}' for merge not found",
                    )
                if parent_complaint.status in (Status.MERGED.value, Status.OUT_OF_SCOPE.value):
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Cannot merge into complaint '{parent_complaint.id}' in terminal status '{parent_complaint.status}'",
                    )

            # Create complaint row in SUBMITTED
            complaint_id = str(uuid.uuid4())
            complaint = Complaint(
                id=complaint_id,
                created_at=clock_now(),
                updated_at=clock_now(),
                citizen_name=cmd.citizen_name,
                citizen_contact=cmd.citizen_contact,
                raw_text=cmd.raw_text,
                language=cmd.language,
                latitude=cmd.latitude,
                longitude=cmd.longitude,
                address_text=cmd.address_text,
                category=cmd.category,
                issue=cmd.issue,
                category_confidence=cmd.category_confidence,
                civic_relevance=cmd.civic_relevance,
                credibility=cmd.credibility,
                severity_score=cmd.severity_score,
                severity_level=cmd.severity_level,
                priority=cmd.priority,
                severity_factors=cmd.severity_factors,
                priority_factors=cmd.priority_factors or {},
                department_id=dept.id,
                needs_review=needs_rev,
                review_reason=rev_reason,
                status=Status.SUBMITTED.value,
                structured_summary=cmd.structured_summary,
                ai_reasoning=cmd.ai_reasoning,
                missing_info=cmd.missing_info,
            )
            db.add(complaint)
            db.flush()

            # Create initial audit log
            init_evt = log_event(
                db,
                complaint_id=complaint.id,
                actor=actor_str,
                action="CREATE_COMPLAINT",
                detail=payload,
            )
            event_ids.append(init_evt.id)

            # State transitions: SUBMITTED -> AI_ANALYZING -> outcome
            transition(db, complaint, Status.AI_ANALYZING, actor="SYSTEM")
            transition(db, complaint, Status(final_outcome), actor="SYSTEM")

            # Create evidence rows (role COMPLAINT)
            for ev_item in cmd.evidence:
                ev_obj = Evidence(
                    complaint_id=complaint.id,
                    type=ev_item.get("type", "IMAGE"),
                    role="COMPLAINT",
                    file_path=ev_item.get("file_path", ""),
                    phash=ev_item.get("phash"),
                    uploaded_by=cmd.citizen_name,
                    created_at=clock_now(),
                )
                db.add(ev_obj)

            # Set initial SLA deadline for classified and review outcomes
            if final_outcome in ("CLASSIFIED", "HUMAN_REVIEW"):
                complaint.sla_deadline = initial_deadline(
                    complaint.created_at,
                    complaint.priority,
                    dept,
                )

            # If MERGED, link and audit both parent and child
            if final_outcome == "MERGED" and parent_complaint:
                complaint.duplicate_of = parent_complaint.id
                parent_complaint.duplicate_count += 1
                parent_evt = log_event(
                    db,
                    complaint_id=parent_complaint.id,
                    actor=actor_str,
                    action="DUPLICATE_MERGED",
                    detail={"merged_complaint_id": complaint.id},
                )
                child_evt = log_event(
                    db,
                    complaint_id=complaint.id,
                    actor=actor_str,
                    action="MERGED_INTO",
                    detail={"parent_complaint_id": parent_complaint.id},
                )
                event_ids.extend([parent_evt.id, child_evt.id])

        elif isinstance(cmd, LinkClusterCommand):
            assert complaint is not None
            cluster_id: int
            if cmd.cluster_id:
                cluster = db.query(Cluster).filter_by(id=cmd.cluster_id).first()
                if not cluster:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Cluster '{cmd.cluster_id}' not found",
                        complaint_id=complaint.id,
                    )
                cluster_id = cluster.id
            else:
                assert cmd.new_cluster is not None
                new_c = Cluster(
                    kind=cmd.kind,
                    lat=cmd.new_cluster["lat"],
                    lng=cmd.new_cluster["lng"],
                    hypothesis=cmd.new_cluster["hypothesis"],
                    confidence=cmd.new_cluster["confidence"],
                    created_at=clock_now(),
                )
                db.add(new_c)
                db.flush()
                cluster_id = new_c.id

            complaint.cluster_id = cluster_id
            evt = log_event(
                db,
                complaint_id=complaint.id,
                actor=actor_str,
                action="LINK_CLUSTER",
                detail={"cluster_id": cluster_id, "kind": cmd.kind},
                reasoning=cmd.reasoning,
                confidence=cmd.confidence,
            )
            event_ids.append(evt.id)

        elif isinstance(cmd, SetPriorityCommand):
            assert complaint is not None
            complaint.priority = cmd.priority
            complaint.priority_factors = cmd.priority_factors
            complaint.sla_deadline = initial_deadline(
                complaint.created_at,
                complaint.priority,
                complaint.department,
            )
            evt = log_event(
                db,
                complaint_id=complaint.id,
                actor=actor_str,
                action="SET_PRIORITY",
                detail={"priority": cmd.priority, "factors": cmd.priority_factors},
                reasoning=cmd.reasoning,
            )
            event_ids.append(evt.id)

        elif isinstance(cmd, FlagHumanReviewCommand):
            assert complaint is not None
            complaint.needs_review = True
            complaint.review_reason = cmd.reason
            evt = log_event(
                db,
                complaint_id=complaint.id,
                actor=actor_str,
                action="FLAG_HUMAN_REVIEW",
                detail={"reason": cmd.reason},
                confidence=cmd.confidence,
            )
            event_ids.append(evt.id)

        elif isinstance(cmd, MarkOutOfScopeCommand):
            assert complaint is not None
            transition(db, complaint, Status.OUT_OF_SCOPE, actor=actor_str, reasoning=cmd.reason)

        elif isinstance(cmd, AssignCommand):
            assert complaint is not None
            officer = db.query(User).filter_by(id=cmd.officer_id).first()
            if not officer or officer.role != "OFFICER":
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"User '{cmd.officer_id}' is not an officer",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )
            if officer.department_id != complaint.department_id:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Officer '{cmd.officer_id}' belongs to department {officer.department_id}, "
                    f"not complaint department {complaint.department_id}",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            complaint.assigned_officer_id = officer.id
            complaint.needs_review = False
            complaint.review_reason = None
            transition(
                db,
                complaint,
                Status.ASSIGNED,
                actor=actor_str,
                detail={"officer_id": officer.id, "note": cmd.note},
            )

        elif isinstance(cmd, ChangeStatusCommand):
            assert complaint is not None
            current_s = Status(complaint.status)
            try:
                target_s = Status(cmd.new_status)
            except ValueError:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Unknown target status: {cmd.new_status}",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            # Check special case: ESCALATED returning to previous_status
            if current_s == Status.ESCALATED:
                if act != Actor.ADMIN:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        "Only ADMIN can return complaint from ESCALATED status",
                        complaint_id=complaint.id,
                        current_status=complaint.status,
                    )
                if not complaint.previous_status or target_s.value != complaint.previous_status:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"ESCALATED complaint may only return to previous_status '{complaint.previous_status}'",
                        complaint_id=complaint.id,
                        current_status=complaint.status,
                    )
            else:
                allowed_actors = CHANGE_STATUS_MOVES.get((current_s, target_s))
                if not allowed_actors or act not in allowed_actors:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Transition from {current_s.value} to {target_s.value} not allowed for actor '{actor_str}'",
                        complaint_id=complaint.id,
                        current_status=complaint.status,
                    )

                if (current_s, target_s) == (Status.ASSIGNED, Status.IN_PROGRESS) and act == Actor.OFFICER:
                    if actor_ref is not None and int(actor_ref) != complaint.assigned_officer_id:
                        return _reject(
                            db,
                            cmd_type,
                            actor_str,
                            payload,
                            f"Officer '{actor_ref}' is not the assigned officer for this complaint",
                            complaint_id=complaint.id,
                            current_status=complaint.status,
                        )

            # Specific side effects
            if current_s == Status.HUMAN_REVIEW and target_s == Status.CLASSIFIED:
                complaint.needs_review = False
                complaint.review_reason = None
            elif current_s == Status.ADMIN_VERIFICATION:
                latest_res = (
                    db.query(Resolution)
                    .filter_by(complaint_id=complaint.id)
                    .order_by(Resolution.created_at.desc())
                    .first()
                )
                if latest_res:
                    if target_s == Status.CITIZEN_CONFIRMATION:
                        latest_res.admin_decision = "APPROVED"
                    elif target_s == Status.IN_PROGRESS:
                        latest_res.admin_decision = "REJECTED"

            transition(db, complaint, target_s, actor=actor_str, reasoning=cmd.reason)

        elif isinstance(cmd, SubmitResolutionCommand):
            assert complaint is not None
            if cmd.officer_id != complaint.assigned_officer_id:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Officer '{cmd.officer_id}' is not the assigned officer '{complaint.assigned_officer_id}'",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            # Validate after evidence items
            for ev_id in cmd.after_evidence_ids:
                ev_row = db.query(Evidence).filter_by(id=ev_id, complaint_id=complaint.id).first()
                if not ev_row:
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Evidence id '{ev_id}' not found on this complaint",
                        complaint_id=complaint.id,
                        current_status=complaint.status,
                    )
                if ev_row.role != "RESOLUTION_AFTER":
                    return _reject(
                        db,
                        cmd_type,
                        actor_str,
                        payload,
                        f"Evidence id '{ev_id}' does not have role 'RESOLUTION_AFTER'",
                        complaint_id=complaint.id,
                        current_status=complaint.status,
                    )

            res_obj = Resolution(
                complaint_id=complaint.id,
                officer_id=cmd.officer_id,
                description=cmd.description,
                created_at=clock_now(),
            )
            db.add(res_obj)
            db.flush()

            transition(db, complaint, Status.RESOLUTION_SUBMITTED, actor=actor_str)

        elif isinstance(cmd, RecordVerificationCommand):
            assert complaint is not None
            latest_res = (
                db.query(Resolution)
                .filter_by(complaint_id=complaint.id)
                .order_by(Resolution.created_at.desc())
                .first()
            )
            if not latest_res:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    "No resolution record found to attach verification to",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            latest_res.ai_verdict = {
                "evidence_relevant": cmd.evidence_relevant,
                "location_consistent": cmd.location_consistent,
                "visual_change_detected": cmd.visual_change_detected,
                "recommendation": cmd.recommendation,
                "reasoning": cmd.reasoning,
            }
            latest_res.ai_confidence = cmd.confidence

            # Route by recommendation and confidence
            if cmd.recommendation == "ADMIN_REVIEW":
                target_status = Status.ADMIN_VERIFICATION
            elif cmd.recommendation == "REJECT":
                if gate(cmd.confidence) == "AUTO":
                    target_status = Status.IN_PROGRESS
                else:
                    target_status = Status.ADMIN_VERIFICATION
                    complaint.needs_review = True
                    complaint.review_reason = (
                        f"AI rejected resolution with confidence {cmd.confidence:.2f} "
                        f"(requires manual review)"
                    )
            elif cmd.recommendation == "NEEDS_MORE_EVIDENCE":
                target_status = Status.IN_PROGRESS
            else:
                target_status = Status.ADMIN_VERIFICATION

            transition(db, complaint, target_status, actor=actor_str, reasoning=cmd.reasoning)

        elif isinstance(cmd, SendFollowupCommand):
            assert complaint is not None
            complaint.last_followup_at = clock_now()
            evt = log_event(
                db,
                complaint_id=complaint.id,
                actor=actor_str,
                action="SEND_FOLLOWUP",
                detail={"message": cmd.message, "level": cmd.level},
            )
            event_ids.append(evt.id)

        elif isinstance(cmd, EscalateCommand):
            assert complaint is not None
            if complaint.status == Status.ESCALATED.value:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    "Complaint is already in ESCALATED status",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            max_chain = len(complaint.department.escalation_chain)
            next_level = (complaint.escalation_level or 0) + 1
            if next_level > max_chain:
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    f"Escalation level {next_level} exceeds department maximum chain ({max_chain})",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            esc_record = Escalation(
                complaint_id=complaint.id,
                level=next_level,
                dossier=cmd.dossier,
                created_at=clock_now(),
            )
            db.add(esc_record)
            transition(db, complaint, Status.ESCALATED, actor=actor_str, reasoning=cmd.reason)

        elif isinstance(cmd, CloseCommand):
            assert complaint is not None
            if act == Actor.SYSTEM and cmd.closure_reason != "AUTO_TIMEOUT":
                return _reject(
                    db,
                    cmd_type,
                    actor_str,
                    payload,
                    "SYSTEM actor may only close complaints with reason AUTO_TIMEOUT",
                    complaint_id=complaint.id,
                    current_status=complaint.status,
                )

            latest_res = (
                db.query(Resolution)
                .filter_by(complaint_id=complaint.id)
                .order_by(Resolution.created_at.desc())
                .first()
            )
            if latest_res:
                latest_res.citizen_decision = (
                    "CONFIRMED" if cmd.closure_reason == "CITIZEN_CONFIRMED" else "AUTO_TIMEOUT"
                )

            complaint.resolved_at = clock_now()
            transition(
                db,
                complaint,
                Status.RESOLVED,
                actor=actor_str,
                detail={"closure_reason": cmd.closure_reason},
            )

        elif isinstance(cmd, ReopenCommand):
            assert complaint is not None
            latest_res = (
                db.query(Resolution)
                .filter_by(complaint_id=complaint.id)
                .order_by(Resolution.created_at.desc())
                .first()
            )
            if latest_res:
                latest_res.citizen_decision = "DISPUTED"

            transition(db, complaint, Status.REOPENED, actor=actor_str, reasoning=cmd.reason)

    except Exception as exc:
        return _reject(
            db,
            cmd_type,
            actor_str,
            payload,
            f"Execution failed: {exc}",
            complaint_id=getattr(complaint, "id", None),
            current_status=getattr(complaint, "status", None),
        )

    db.commit()
    return ExecutionResult(
        ok=True,
        command=cmd_type,
        complaint_id=complaint.id if complaint else None,
        new_status=complaint.status if complaint else None,
        error=None,
        event_ids=event_ids,
    )
