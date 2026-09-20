"""Pydantic v2 schemas and validation rules for all system commands."""

from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)

from .engines.severity import PRIORITY_FOR_LEVEL, severity_level_for_score
from .ontology import CATEGORIES, is_valid_issue, normalize_code
from .state_machine import ACTIVE_STATES, Status


class Actor(str, Enum):
    CITIZEN = "CITIZEN"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"
    AGENT1 = "AGENT1"
    AGENT2 = "AGENT2"
    AGENT3 = "AGENT3"
    SYSTEM = "SYSTEM"


class PriorityEnum(str, Enum):
    NORMAL = "NORMAL"
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class CreateComplaintCommand(BaseModel):
    command: Literal["CREATE_COMPLAINT"] = "CREATE_COMPLAINT"
    citizen_name: str
    citizen_contact: str
    raw_text: str
    language: str = "en"
    latitude: float
    longitude: float
    address_text: str
    category: str
    issue: str
    category_confidence: float = Field(ge=0.0, le=1.0)
    civic_relevance: Literal["LOW", "MEDIUM", "HIGH"]
    credibility: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity_score: int = Field(ge=0, le=10)
    severity_level: str
    priority: str
    severity_factors: List[Dict[str, Any]]
    priority_factors: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    department_code: str
    structured_summary: str
    ai_reasoning: Dict[str, Any]
    missing_info: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    outcome: Literal["CLASSIFIED", "HUMAN_REVIEW", "OUT_OF_SCOPE", "MERGED"]
    merge_into_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_business_rules(self) -> "CreateComplaintCommand":
        cat_norm = normalize_code(self.category)
        if cat_norm not in CATEGORIES:
            raise ValueError(f"Category '{self.category}' is not in canonical ontology")

        if not is_valid_issue(cat_norm, self.issue):
            raise ValueError(
                f"Issue '{self.issue}' does not belong to category '{self.category}'"
            )

        expected_level = severity_level_for_score(self.severity_score)
        if self.severity_level.strip().upper() != expected_level:
            raise ValueError(
                f"Severity level '{self.severity_level}' does not match expected band "
                f"'{expected_level}' for score {self.severity_score}"
            )

        try:
            PriorityEnum(self.priority.strip().upper())
        except ValueError:
            raise ValueError(
                f"Priority '{self.priority}' is invalid; must be one of "
                f"{[p.value for p in PriorityEnum]}"
            )

        if self.outcome == "MERGED" and not self.merge_into_id:
            raise ValueError("merge_into_id is required when outcome is MERGED")

        return self


class LinkClusterCommand(BaseModel):
    command: Literal["LINK_CLUSTER"] = "LINK_CLUSTER"
    complaint_id: str
    kind: Literal["DUPLICATE", "ROOT_CAUSE"]
    cluster_id: Optional[int] = None
    new_cluster: Optional[Dict[str, Any]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @model_validator(mode="after")
    def validate_cluster_target(self) -> "LinkClusterCommand":
        has_id = self.cluster_id is not None
        has_new = self.new_cluster is not None
        if has_id == has_new:
            raise ValueError("Exactly one of cluster_id or new_cluster must be provided")

        if has_new:
            req_keys = {"lat", "lng", "hypothesis", "confidence"}
            if not req_keys.issubset(self.new_cluster.keys()):
                raise ValueError(
                    f"new_cluster dict must contain required keys: {req_keys}"
                )
        return self


class SetPriorityCommand(BaseModel):
    command: Literal["SET_PRIORITY"] = "SET_PRIORITY"
    complaint_id: str
    priority: str
    priority_factors: Union[List[Dict[str, Any]], Dict[str, Any]]
    reasoning: str

    @model_validator(mode="after")
    def validate_priority(self) -> "SetPriorityCommand":
        try:
            PriorityEnum(self.priority.strip().upper())
        except ValueError:
            raise ValueError(f"Invalid priority '{self.priority}'")
        return self


class FlagHumanReviewCommand(BaseModel):
    command: Literal["FLAG_HUMAN_REVIEW"] = "FLAG_HUMAN_REVIEW"
    complaint_id: str
    reason: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class MarkOutOfScopeCommand(BaseModel):
    command: Literal["MARK_OUT_OF_SCOPE"] = "MARK_OUT_OF_SCOPE"
    complaint_id: str
    reason: str


class AssignCommand(BaseModel):
    command: Literal["ASSIGN"] = "ASSIGN"
    complaint_id: str
    officer_id: int
    note: Optional[str] = None


class ChangeStatusCommand(BaseModel):
    command: Literal["CHANGE_STATUS"] = "CHANGE_STATUS"
    complaint_id: str
    new_status: str
    reason: str


class SubmitResolutionCommand(BaseModel):
    command: Literal["SUBMIT_RESOLUTION"] = "SUBMIT_RESOLUTION"
    complaint_id: str
    officer_id: int
    description: str
    after_evidence_ids: List[int] = Field(min_length=1)


class RecordVerificationCommand(BaseModel):
    command: Literal["RECORD_VERIFICATION"] = "RECORD_VERIFICATION"
    complaint_id: str
    evidence_relevant: Optional[bool] = None
    location_consistent: Optional[bool] = None
    visual_change_detected: Optional[bool] = None
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: Literal["ADMIN_REVIEW", "REJECT", "NEEDS_MORE_EVIDENCE"]
    reasoning: str


class SendFollowupCommand(BaseModel):
    command: Literal["SEND_FOLLOWUP"] = "SEND_FOLLOWUP"
    complaint_id: str
    message: str
    level: int = Field(ge=1, le=3)


class EscalateCommand(BaseModel):
    command: Literal["ESCALATE"] = "ESCALATE"
    complaint_id: str
    reason: str
    dossier: str


class CloseCommand(BaseModel):
    command: Literal["CLOSE"] = "CLOSE"
    complaint_id: str
    closure_reason: Literal["CITIZEN_CONFIRMED", "AUTO_TIMEOUT"]


class ReopenCommand(BaseModel):
    command: Literal["REOPEN"] = "REOPEN"
    complaint_id: str
    reason: str


Command = Annotated[
    Union[
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
    ],
    Field(discriminator="command"),
]

_command_adapter = TypeAdapter(Command)


def parse_command(data: Dict[str, Any]) -> Command:
    """Validate and parse raw dictionary payload into a typed Command."""
    if not isinstance(data, dict):
        raise ValueError("Command payload must be a JSON object (dict)")
    cmd_type = data.get("command")
    if not cmd_type:
        raise ValueError("Missing 'command' discriminator in payload")
    try:
        return _command_adapter.validate_python(data)
    except Exception as exc:
        raise ValueError(f"Validation error for command '{cmd_type}': {exc}") from exc


# Allowed actors and states table
COMMAND_RULES: Dict[str, Dict[str, Any]] = {
    "CREATE_COMPLAINT": {
        "allowed_actors": {Actor.AGENT2, Actor.SYSTEM},
        "requires_existing": False,
        "allowed_states": set(),
    },
    "LINK_CLUSTER": {
        "allowed_actors": {Actor.AGENT2, Actor.AGENT3, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": ACTIVE_STATES,
    },
    "SET_PRIORITY": {
        "allowed_actors": {Actor.AGENT2, Actor.AGENT3, Actor.SYSTEM, Actor.ADMIN},
        "requires_existing": True,
        "allowed_states": {
            Status.CLASSIFIED,
            Status.UNDER_REVIEW,
            Status.ASSIGNED,
            Status.IN_PROGRESS,
            Status.REOPENED,
            Status.ESCALATED,
        },
    },
    "FLAG_HUMAN_REVIEW": {
        "allowed_actors": {Actor.AGENT1, Actor.AGENT2, Actor.AGENT3, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": ACTIVE_STATES,
    },
    "MARK_OUT_OF_SCOPE": {
        "allowed_actors": {Actor.AGENT2, Actor.ADMIN},
        "requires_existing": True,
        "allowed_states": {Status.AI_ANALYZING, Status.HUMAN_REVIEW},
    },
    "ASSIGN": {
        "allowed_actors": {Actor.ADMIN},
        "requires_existing": True,
        "allowed_states": {Status.UNDER_REVIEW},
    },
    "CHANGE_STATUS": {
        "allowed_actors": {Actor.ADMIN, Actor.OFFICER, Actor.AGENT3, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": set(Status),  # refined by change_status table
    },
    "SUBMIT_RESOLUTION": {
        "allowed_actors": {Actor.OFFICER},
        "requires_existing": True,
        "allowed_states": {Status.IN_PROGRESS},
    },
    "RECORD_VERIFICATION": {
        "allowed_actors": {Actor.AGENT3},
        "requires_existing": True,
        "allowed_states": {Status.AI_VERIFICATION},
    },
    "SEND_FOLLOWUP": {
        "allowed_actors": {Actor.AGENT3, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": {
            Status.CLASSIFIED,
            Status.UNDER_REVIEW,
            Status.ASSIGNED,
            Status.IN_PROGRESS,
            Status.ESCALATED,
        },
    },
    "ESCALATE": {
        "allowed_actors": {Actor.AGENT3, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": ACTIVE_STATES,
    },
    "CLOSE": {
        "allowed_actors": {Actor.CITIZEN, Actor.SYSTEM},
        "requires_existing": True,
        "allowed_states": {Status.CITIZEN_CONFIRMATION},
    },
    "REOPEN": {
        "allowed_actors": {Actor.CITIZEN},
        "requires_existing": True,
        "allowed_states": {Status.CITIZEN_CONFIRMATION},
    },
}
