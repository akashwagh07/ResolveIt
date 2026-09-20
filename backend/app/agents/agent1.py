"""Agent 1: Intake and civic classification agent."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from ..llm import MediaError, MediaPart, generate_json, load_media
from ..ontology import is_valid_issue, resolve_alias
from .prompts import SYSTEM_PROMPT, build_user_prompt


class Agent1Input(BaseModel):
    """Input payload provided to Agent 1."""
    text: Optional[str] = None
    language_hint: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_text: Optional[str] = None
    media_paths: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_has_content(self) -> "Agent1Input":
        has_text = bool(self.text and self.text.strip())
        has_media = bool(self.media_paths and len(self.media_paths) > 0)
        if not has_text and not has_media:
            raise ValueError("Agent 1 input must contain at least text or one media path")
        return self


ContextTag = Literal[
    "SCHOOL_NEARBY",
    "HOSPITAL_NEARBY",
    "MAJOR_ROAD",
    "TRANSIT_AREA",
    "HIGH_PEDESTRIAN",
    "SAFETY_HAZARD",
    "HEALTH_HAZARD",
    "TRAFFIC_IMPACT",
]


class ObservationItem(BaseModel):
    fact: str
    source: Literal["TEXT", "IMAGE", "AUDIO", "VIDEO"]


class AlternativeItem(BaseModel):
    category: str
    issue: str
    confidence: float


class Agent1Output(BaseModel):
    """Structured LLM output for civic classification."""
    civic_relevance: Literal["LOW", "MEDIUM", "HIGH"]
    relevance_reason: str
    category: str
    issue: str
    description: str
    duration_text: Optional[str] = None
    duration_days: Optional[float] = None
    size_hint: Literal["SMALL", "MEDIUM", "LARGE", "UNKNOWN"] = "UNKNOWN"
    context_tags: List[ContextTag] = Field(default_factory=list)
    language: str = "en"
    transcript: Optional[str] = None
    translation_en: Optional[str] = None
    location_mentions: List[str] = Field(default_factory=list)
    image_matches_text: Optional[bool] = None
    observations: List[ObservationItem] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    alternatives: List[AlternativeItem] = Field(default_factory=list)
    confidence: float
    confidence_reason: str


class LocationResult(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_text: Optional[str] = None
    source: Literal["GPS", "TEXT", "NONE"]


class EvidenceFlags(BaseModel):
    text: bool
    image: bool
    audio: bool
    video: bool


class Agent1Result(BaseModel):
    """Final post-processed result returned to callers."""
    output: Agent1Output
    location: LocationResult
    evidence_flags: EvidenceFlags
    model_used: str
    cached: bool
    latency_ms: float
    warnings: List[str] = Field(default_factory=list)


def run_agent1(inp: Agent1Input, *, use_cache: bool = True) -> Agent1Result:
    """
    Run Agent 1 classification pipeline.
    Loads media, executes LLM generation, applies deterministic post-processing,
    and returns an Agent1Result.
    """
    warnings: List[str] = []

    # 1. Load media
    media_parts: List[MediaPart] = []
    for path in inp.media_paths:
        part = load_media(path)
        media_parts.append(part)

    # 2. Compute evidence flags deterministically from real inputs
    has_text = bool(inp.text and inp.text.strip())
    has_image = any(m.kind == "IMAGE" for m in media_parts)
    has_audio = any(m.kind == "AUDIO" for m in media_parts)
    has_video = any(m.kind == "VIDEO" for m in media_parts)

    evidence_flags = EvidenceFlags(
        text=has_text,
        image=has_image,
        audio=has_audio,
        video=has_video,
    )

    # 3. Construct user prompt with delimiters
    user_prompt = build_user_prompt(
        text=inp.text,
        language_hint=inp.language_hint,
        address_text=inp.address_text,
    )

    # 4. Generate structured JSON via LLM wrapper
    llm_res = generate_json(
        prompt=user_prompt,
        schema=Agent1Output,
        system=SYSTEM_PROMPT,
        media=media_parts if media_parts else None,
        thinking="low",
        purpose="agent1_classification",
        use_cache=use_cache,
    )

    raw_output = llm_res.parsed

    # 5. Deterministic Post-Processing
    # Normalize aliases
    norm_cat, norm_iss = resolve_alias(raw_output.category, raw_output.issue)

    # Validate category and issue against canonical ontology
    final_cat = norm_cat
    final_iss = norm_iss
    confidence = float(raw_output.confidence)

    if not is_valid_issue(final_cat, final_iss):
        warnings.append(
            f"Invalid category/issue pair ({final_cat}, {final_iss}) returned by LLM; defaulted to OTHER/OTHER"
        )
        final_cat = "OTHER"
        final_iss = "OTHER"
        confidence = min(confidence, 0.5)

    # If image_matches_text is false, cap confidence at 0.7
    if raw_output.image_matches_text is False:
        if confidence > 0.7:
            confidence = 0.7
            warnings.append("Confidence capped at 0.7 due to mismatch between text and image evidence")

    # Clamp confidence to [0.0, 1.0]
    confidence = max(0.0, min(1.0, confidence))

    # Process alternatives: resolve aliases, filter invalid, max 2
    post_alts: List[AlternativeItem] = []
    for alt in raw_output.alternatives:
        alt_cat, alt_iss = resolve_alias(alt.category, alt.issue)
        if is_valid_issue(alt_cat, alt_iss):
            post_alts.append(
                AlternativeItem(
                    category=alt_cat,
                    issue=alt_iss,
                    confidence=max(0.0, min(1.0, float(alt.confidence))),
                )
            )
        if len(post_alts) >= 2:
            break

    post_output = Agent1Output(
        civic_relevance=raw_output.civic_relevance,
        relevance_reason=raw_output.relevance_reason,
        category=final_cat,
        issue=final_iss,
        description=raw_output.description,
        duration_text=raw_output.duration_text,
        duration_days=raw_output.duration_days,
        size_hint=raw_output.size_hint,
        context_tags=raw_output.context_tags,
        language=raw_output.language,
        transcript=raw_output.transcript,
        translation_en=raw_output.translation_en,
        location_mentions=raw_output.location_mentions,
        image_matches_text=raw_output.image_matches_text,
        observations=raw_output.observations,
        missing_info=raw_output.missing_info,
        alternatives=post_alts,
        confidence=confidence,
        confidence_reason=raw_output.confidence_reason,
    )

    # Location resolution: GPS always wins, else text mention, else NONE
    # Coordinates from the LLM are never trusted or used.
    if inp.latitude is not None and inp.longitude is not None:
        loc = LocationResult(
            latitude=inp.latitude,
            longitude=inp.longitude,
            address_text=inp.address_text or (post_output.location_mentions[0] if post_output.location_mentions else None),
            source="GPS",
        )
    elif post_output.location_mentions or (inp.address_text and inp.address_text.strip()):
        loc = LocationResult(
            latitude=None,
            longitude=None,
            address_text=inp.address_text or (post_output.location_mentions[0] if post_output.location_mentions else None),
            source="TEXT",
        )
    else:
        loc = LocationResult(
            latitude=None,
            longitude=None,
            address_text=None,
            source="NONE",
        )

    return Agent1Result(
        output=post_output,
        location=loc,
        evidence_flags=evidence_flags,
        model_used=llm_res.model_used,
        cached=llm_res.cached,
        latency_ms=llm_res.latency_ms,
        warnings=warnings,
    )
