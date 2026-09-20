"""Verification interface and stub implementation for ResolveIt resolution verification."""

from dataclasses import dataclass
import logging
from typing import Literal, Optional, Protocol
from sqlalchemy.orm import Session

from .commands import Actor
from .config import get_settings
from .executor import execute_command
from .models import Complaint, Resolution

logger = logging.getLogger("resolveit.verification")


@dataclass
class VerificationVerdict:
    evidence_relevant: Optional[bool]
    location_consistent: Optional[bool]
    visual_change_detected: Optional[bool]
    confidence: float
    recommendation: Literal["ADMIN_REVIEW", "REJECT", "NEEDS_MORE_EVIDENCE"]
    reasoning: str


class Verifier(Protocol):
    def verify(
        self, db: Session, complaint: Complaint, resolution: Resolution
    ) -> VerificationVerdict:
        """Analyze before/after evidence and return a structured verdict."""
        ...


class StubVerifier:
    """Default non-AI verifier recommending human admin review."""

    def verify(
        self, db: Session, complaint: Complaint, resolution: Resolution
    ) -> VerificationVerdict:
        return VerificationVerdict(
            evidence_relevant=None,
            location_consistent=None,
            visual_change_detected=None,
            confidence=0.0,
            recommendation="ADMIN_REVIEW",
            reasoning="Automated visual verification is not enabled; a human must review the evidence",
        )


def get_verifier() -> Verifier:
    """Return configured Verifier instance according to VERIFIER setting."""
    settings = get_settings()
    mode = (settings.VERIFIER or "stub").strip().lower()
    if mode == "stub":
        return StubVerifier()
    # Placeholder for future verifiers
    return StubVerifier()


def run_verification_hook(
    db: Session, complaint: Complaint, resolution: Resolution
) -> None:
    """
    Hook executed after SUBMIT_RESOLUTION succeeds:
    1. Steps status from RESOLUTION_SUBMITTED to AI_VERIFICATION via SYSTEM command.
    2. Runs configured verifier (or catches failure and falls back to ADMIN_REVIEW).
    3. Executes RECORD_VERIFICATION via AGENT3 to route to ADMIN_VERIFICATION.
    """
    # 1. Transition RESOLUTION_SUBMITTED -> AI_VERIFICATION
    step1_cmd = {
        "command": "CHANGE_STATUS",
        "complaint_id": complaint.id,
        "new_status": "AI_VERIFICATION",
        "reason": "Triggering automated resolution verification",
    }
    step1_res = execute_command(db, step1_cmd, Actor.SYSTEM)
    if not step1_res.ok:
        logger.error(
            "Failed to transition complaint %s to AI_VERIFICATION: %s",
            complaint.id,
            step1_res.error,
        )
        return

    # 2. Run verifier
    verifier = get_verifier()
    try:
        verdict = verifier.verify(db, complaint, resolution)
    except Exception as exc:
        logger.exception("Verifier execution failed for complaint %s: %s", complaint.id, exc)
        verdict = VerificationVerdict(
            evidence_relevant=None,
            location_consistent=None,
            visual_change_detected=None,
            confidence=0.0,
            recommendation="ADMIN_REVIEW",
            reasoning="Verification unavailable",
        )

    # 3. Record verification as AGENT3
    record_cmd = {
        "command": "RECORD_VERIFICATION",
        "complaint_id": complaint.id,
        "evidence_relevant": verdict.evidence_relevant,
        "location_consistent": verdict.location_consistent,
        "visual_change_detected": verdict.visual_change_detected,
        "confidence": verdict.confidence,
        "recommendation": verdict.recommendation,
        "reasoning": verdict.reasoning,
    }
    record_res = execute_command(db, record_cmd, Actor.AGENT3)
    if not record_res.ok:
        logger.error(
            "Failed to record verification for complaint %s: %s",
            complaint.id,
            record_res.error,
        )
