from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from forecasting_assistant.application.clarification import (
    evaluate_readiness,
    select_next_slot,
)
from forecasting_assistant.application.normalization import normalize_value
from forecasting_assistant.application.state_reducer import apply_extraction
from forecasting_assistant.application.validation import validate_dialogue
from forecasting_assistant.domain.conditions import is_slot_active
from forecasting_assistant.domain.models import (
    DialogueState,
    DialogueTurn,
    ExtractorResult,
    ForecastingSpecification,
    Intent,
    QuestionRequest,
    ReadinessReport,
    Requiredness,
    SlotStatus,
    SlotUpdate,
    TurnResult,
)
from forecasting_assistant.domain.schema import ForecastingSchema, create_initial_state
from forecasting_assistant.infrastructure.llm.protocol import StructuredLLMClient
from forecasting_assistant.infrastructure.persistence.protocol import DialogueRepository
from forecasting_assistant.prompts.llmrei_long import (
    static_fallback_question,
    validate_question,
)


class DialogueNotFoundError(KeyError):
    pass


class ElicitationEngine:
    def __init__(
        self,
        schema: ForecastingSchema,
        llm_client: StructuredLLMClient,
        repository: DialogueRepository,
    ) -> None:
        self._schema = schema
        self._llm = llm_client
        self._repository = repository

    def start_dialogue(self) -> DialogueState:
        state = create_initial_state(self._schema)
        self._repository.save_state(state)
        self._repository.append_event(
            state.dialogue_id,
            "dialogue_started",
            {"schema_version": state.schema_version},
        )
        return state.model_copy(deep=True)

    def _load(self, dialogue_id: UUID) -> DialogueState:
        state = self._repository.load_state(dialogue_id)
        if state is None:
            raise DialogueNotFoundError(str(dialogue_id))
        return state

    def get_state(self, dialogue_id: UUID) -> DialogueState:
        return self._load(dialogue_id).model_copy(deep=True)

    def _confirmed_context(self, state: DialogueState) -> dict[str, Any]:
        return {
            slot_id: slot.value
            for slot_id, slot in state.slots.items()
            if slot_id != "authentication_reference"
            and (slot.confirmed_by_user or slot.status == SlotStatus.CONFIRMED)
        }

    def _question_request(self, state: DialogueState, slot_id: str, reason: str) -> QuestionRequest:
        definition = self._schema.get(slot_id)
        active_ids = tuple(
            candidate.slot_id
            for candidate in self._schema.slots
            if candidate.slot_id != slot_id and is_slot_active(candidate, state)
        )
        return QuestionRequest(
            slot_id=slot_id,
            reason=reason,
            slot_description=definition.description,
            current_state=state.slots[slot_id].model_copy(deep=True),
            confirmed_context=self._confirmed_context(state),
            static_question=definition.static_question,
            allowed_values=definition.allowed_values,
            other_active_slot_ids=active_ids,
        )

    async def _ask(self, request: QuestionRequest) -> str:
        for _ in range(2):
            try:
                output = await self._llm.ask(request)
            except Exception:
                break
            if validate_question(output, request):
                return output.question
        return static_fallback_question(request).question

    def _recover_selected_enum_answer(
        self,
        state: DialogueState,
        turn_number: int,
        message: str,
    ) -> tuple[DialogueState, str] | None:
        candidate = select_next_slot(self._schema, state)
        if candidate is None:
            return None
        definition = self._schema.get(candidate.slot_id)
        if definition.value_type != "enum":
            return None
        normalized = normalize_value(definition, message)
        if normalized not in definition.allowed_values:
            return None

        intent = state.intent
        intent_confidence = state.slots["intent"].confidence or 0.0
        if state.slots["intent"].value == Intent.CREATE_FORECAST.value:
            intent = Intent.CREATE_FORECAST
            intent_confidence = max(intent_confidence, 0.99)

        recovered = apply_extraction(
            state,
            ExtractorResult(
                intent=intent,
                intent_confidence=intent_confidence,
                updates=[
                    SlotUpdate(
                        slot_id=candidate.slot_id,
                        candidate_value=normalized,
                        status=SlotStatus.PROVIDED,
                        confidence=1.0,
                        evidence_text=message,
                    )
                ],
            ),
            self._schema,
            turn_number,
            message,
        )
        return recovered, candidate.slot_id

    def _render_confirmation(self, state: DialogueState) -> str:
        values = {
            slot_id: slot.value
            for slot_id, slot in state.slots.items()
            if slot.value is not None
            and slot.status not in {SlotStatus.INVALID, SlotStatus.CONFLICTING, SlotStatus.AMBIGUOUS}
            and slot_id != "authentication_reference"
        }
        rendered = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
        return f"Please confirm this forecasting specification: {rendered}"

    def _finish_turn(
        self,
        state: DialogueState,
        assistant_message: str,
        readiness: ReadinessReport,
    ) -> TurnResult:
        state.turns[-1].assistant_message = assistant_message
        self._repository.save_state(state)
        self._repository.append_event(
            state.dialogue_id,
            "assistant_response",
            {
                "turn_number": state.turns[-1].turn_number,
                "message": assistant_message,
                "ready": readiness.ready,
            },
        )
        return TurnResult(
            state=state.model_copy(deep=True),
            assistant_message=assistant_message,
            readiness=readiness,
        )

    async def handle_user_message(self, dialogue_id: UUID, message: str) -> TurnResult:
        state = self._load(dialogue_id)
        turn_number = len(state.turns) + 1
        state.turns.append(DialogueTurn(turn_number=turn_number, user_message=message))
        self._repository.append_event(
            dialogue_id,
            "user_message",
            {"turn_number": turn_number, "message": message},
        )

        try:
            extraction = await self._llm.extract(message, state.model_copy(deep=True))
            updated = apply_extraction(
                state,
                extraction,
                self._schema,
                turn_number,
                message,
            )
            updated.intent = extraction.intent
            state = updated
            self._repository.append_event(
                dialogue_id,
                "extraction_applied",
                extraction.model_dump(mode="json"),
            )
        except Exception as error:
            recovered = self._recover_selected_enum_answer(state, turn_number, message)
            if recovered is not None:
                state, slot_id = recovered
                self._repository.append_event(
                    dialogue_id,
                    "deterministic_recovery_applied",
                    {
                        "turn_number": turn_number,
                        "slot_id": slot_id,
                        "message": message,
                    },
                )
            else:
                readiness = evaluate_readiness(self._schema, state)
                candidate = select_next_slot(self._schema, state)
                if candidate is None:
                    assistant = "Please describe the forecasting requirement you want to define."
                else:
                    assistant = static_fallback_question(
                        self._question_request(state, candidate.slot_id, candidate.reason)
                    ).question
                self._repository.append_event(
                    dialogue_id,
                    "extractor_failed",
                    {"error_type": type(error).__name__},
                )
                return self._finish_turn(state, assistant, readiness)

        if state.intent in {Intent.NOT_FORECASTING, Intent.UNSUPPORTED}:
            readiness = evaluate_readiness(self._schema, state)
            return self._finish_turn(
                state,
                "This assistant supports time-series forecasting requirements only.",
                readiness,
            )

        issues = validate_dialogue(self._schema, state)
        self._repository.append_event(
            dialogue_id,
            "validation_completed",
            {"issues": [issue.model_dump(mode="json") for issue in issues]},
        )
        readiness = evaluate_readiness(self._schema, state)
        if readiness.ready:
            assistant = self._render_confirmation(state)
        else:
            candidate = select_next_slot(self._schema, state)
            if candidate is None:
                assistant = "Please provide more forecasting details."
            else:
                request = self._question_request(state, candidate.slot_id, candidate.reason)
                assistant = await self._ask(request)
        return self._finish_turn(state, assistant, readiness)

    def confirm_specification(
        self, dialogue_id: UUID, *, confirm: bool
    ) -> ForecastingSpecification:
        if confirm is not True:
            raise ValueError("explicit confirmation is required")
        state = self._load(dialogue_id)
        readiness = evaluate_readiness(self._schema, state)
        if not readiness.ready:
            raise ValueError("dialogue is not ready for confirmation")

        values: dict[str, Any] = {}
        defaults: dict[str, Any] = {}
        user_provided: list[str] = []
        confirmed_inferred: list[str] = []
        unresolved_optional: list[str] = []
        for definition in self._schema.slots:
            if not is_slot_active(definition, state):
                continue
            slot = state.slots[definition.slot_id]
            if definition.requiredness == Requiredness.DEFAULTABLE and slot.value is None:
                defaults[definition.slot_id] = definition.default_value
                values[definition.slot_id] = definition.default_value
                continue
            if definition.requiredness == Requiredness.OPTIONAL and slot.value is None:
                unresolved_optional.append(definition.slot_id)
                continue
            if slot.status == SlotStatus.INFERRED and not slot.confirmed_by_user:
                if definition.requiredness == Requiredness.OPTIONAL:
                    unresolved_optional.append(definition.slot_id)
                continue
            if slot.value is None or slot.status in {
                SlotStatus.INVALID,
                SlotStatus.AMBIGUOUS,
                SlotStatus.CONFLICTING,
            }:
                continue
            if definition.slot_id == "authentication_reference":
                if not isinstance(slot.value, str) or not slot.value.startswith("secret://"):
                    continue
            values[definition.slot_id] = slot.value
            if slot.status == SlotStatus.INFERRED and slot.confirmed_by_user:
                confirmed_inferred.append(definition.slot_id)
            else:
                user_provided.append(definition.slot_id)

        specification = ForecastingSpecification(
            dialogue_id=dialogue_id,
            schema_version=self._schema.version,
            values=values,
            user_provided_slots=user_provided,
            confirmed_inferred_slots=confirmed_inferred,
            documented_defaults=defaults,
            unresolved_optional_slots=unresolved_optional,
        )
        state.confirmed = True
        self._repository.save_state(state)
        self._repository.save_specification(specification)
        self._repository.append_event(
            dialogue_id,
            "specification_confirmed",
            {"specification_id": str(specification.specification_id)},
        )
        return specification
