"""Confidence gating rules."""

AUTO_THRESHOLD: float = 0.85
REVIEW_THRESHOLD: float = 0.60


def gate(confidence: float) -> str:
    """Classify confidence into AUTO, REVIEW, or HUMAN."""
    if confidence >= AUTO_THRESHOLD:
        return "AUTO"
    elif confidence >= REVIEW_THRESHOLD:
        return "REVIEW"
    return "HUMAN"
