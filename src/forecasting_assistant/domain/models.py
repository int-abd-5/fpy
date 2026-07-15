from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class SlotStatus(StrEnum):
    UNMENTIONED = "unmentioned"
    PROVIDED = "provided"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    INVALID = "invalid"
    DONT_CARE = "dont_care"
    CONFIRMED = "confirmed"


class Requiredness(StrEnum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"
    DEFAULTABLE = "defaultable"


class Intent(StrEnum):
    CREATE_FORECAST = "create_forecast"
    NOT_FORECASTING = "not_forecasting"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class SlotState(BaseModel):
    slot_id: str
    value: Any = None
    status: SlotStatus = SlotStatus.UNMENTIONED
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_text: str | None = None
    source_turn: int | None = Field(default=None, ge=1)
    validation_errors: list[str] = Field(default_factory=list)
    confirmed_by_user: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def require_evidence_for_user_values(self) -> "SlotState":
        if self.status in {SlotStatus.PROVIDED, SlotStatus.INFERRED} and not self.evidence_text:
            raise ValueError("provided and inferred values require evidence_text")
        return self


class SlotUpdate(BaseModel):
    slot_id: str
    candidate_value: Any = None
    status: SlotStatus
    confidence: float = Field(ge=0, le=1)
    evidence_text: str


class ExtractorResult(BaseModel):
    intent: Intent
    intent_confidence: float = Field(ge=0, le=1)
    updates: list[SlotUpdate] = Field(default_factory=list)
    correction_detected: bool = False
    unsupported_claims: list[str] = Field(default_factory=list)


class DialogueTurn(BaseModel):
    turn_number: int = Field(ge=1)
    user_message: str
    assistant_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DialogueState(BaseModel):
    dialogue_id: UUID = Field(default_factory=uuid4)
    intent: Intent = Intent.AMBIGUOUS
    slots: dict[str, SlotState]
    turns: list[DialogueTurn] = Field(default_factory=list)
    confirmed: bool = False
    schema_version: str = "1.0.0"


class ValidationIssue(BaseModel):
    slot_id: str | None
    code: str
    message: str
    blocking: bool = True


class ReadinessReport(BaseModel):
    ready: bool
    active_required_slots: list[str]
    unresolved_slots: list[str]
    issues: list[ValidationIssue]


class QuestionRequest(BaseModel):
    slot_id: str
    reason: str
    slot_description: str
    current_state: SlotState
    confirmed_context: dict[str, Any]
    static_question: str
    allowed_values: tuple[str, ...] = ()
    other_active_slot_ids: tuple[str, ...] = ()


class QuestionOutput(BaseModel):
    question: str = Field(min_length=1, max_length=300)


class TurnResult(BaseModel):
    state: DialogueState
    assistant_message: str
    readiness: ReadinessReport
    specification: "ForecastingSpecification | None" = None


class ForecastingSpecification(BaseModel):
    specification_id: UUID = Field(default_factory=uuid4)
    dialogue_id: UUID
    schema_version: str
    values: dict[str, Any]
    user_provided_slots: list[str]
    confirmed_inferred_slots: list[str]
    documented_defaults: dict[str, Any]
    unresolved_optional_slots: list[str]
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
