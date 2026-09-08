from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from forecasting_assistant.application.clarification import (
    evaluate_readiness,
    rank_priority_slots,
    select_next_slot,
)
from forecasting_assistant.application.normalization import normalize_value
from forecasting_assistant.application.state_reducer import apply_extraction
from forecasting_assistant.application.validation import (
    is_unusable_reference,
    validate_dialogue,
    validate_slot,
)
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
    SlotState,
    SlotStatus,
    SlotUpdate,
    TurnResult,
)
from forecasting_assistant.domain.schema import ForecastingSchema, create_initial_state
from forecasting_assistant.infrastructure.llm.protocol import StructuredLLMClient
from forecasting_assistant.infrastructure.persistence.protocol import DialogueRepository
from forecasting_assistant.prompts.extractor import safe_provider_value
from forecasting_assistant.prompts.llmrei_long import (
    static_fallback_question,
    validate_question,
)


class DialogueNotFoundError(KeyError):
    pass


TraceSink = Callable[[str, dict[str, Any]], None]


class ElicitationEngine:
    def __init__(
        self,
        schema: ForecastingSchema,
        llm_client: StructuredLLMClient,
        repository: DialogueRepository,
        trace_sink: TraceSink | None = None,
    ) -> None:
        self._schema = schema
        self._llm = llm_client
        self._repository = repository
        self._trace_sink = trace_sink

    def _trace(self, stage: str, payload: dict[str, Any]) -> None:
        if self._trace_sink is None:
            return
        try:
            self._trace_sink(stage, safe_provider_value(payload))
        except Exception:  # noqa: BLE001 - tracing must never interrupt the interview
            return

    @staticmethod
    def _trace_state(state: DialogueState) -> dict[str, Any]:
        return {
            "dialogue_id": str(state.dialogue_id),
            "provider_conversation_id": state.provider_conversation_id,
            "intent": state.intent.value,
            "available_dataset_columns": state.dataset_columns,
            "slots": {
                slot_id: {
                    "value": safe_provider_value(slot.value),
                    "status": slot.status.value,
                    "evidence_text": safe_provider_value(slot.evidence_text),
                    "source_turn": slot.source_turn,
                }
                for slot_id, slot in state.slots.items()
                if slot.status != SlotStatus.UNMENTIONED
            },
        }

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

    def set_dataset_columns(
        self, dialogue_id: UUID, columns: list[str]
    ) -> DialogueState:
        state = self._load(dialogue_id)
        normalized: list[str] = []
        seen: set[str] = set()
        for column in columns:
            value = str(column).strip()
            key = value.casefold()
            if value and key not in seen:
                normalized.append(value)
                seen.add(key)
        if not normalized:
            raise ValueError("at least one dataset column is required")
        state.dataset_columns = normalized
        self._repository.save_state(state)
        self._repository.append_event(
            dialogue_id,
            "dataset_schema_available",
            {"columns": normalized},
        )
        self._trace(
            "dataset.schema_available",
            {"columns": normalized, "state_after": self._trace_state(state)},
        )
        return state.model_copy(deep=True)

    def attach_uploaded_file(
        self,
        dialogue_id: UUID,
        *,
        source_reference: str,
        filename: str,
        columns: list[str],
    ) -> DialogueState:
        """Attach a file supplied through an interface as an explicit user action."""
        state = self._load(dialogue_id)
        normalized_columns: list[str] = []
        seen: set[str] = set()
        for column in columns:
            value = str(column).strip()
            key = value.casefold()
            if value and key not in seen:
                normalized_columns.append(value)
                seen.add(key)

        evidence = f"Uploaded file: {filename}"
        file_format = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
        if file_format == "xls":
            file_format = "xlsx"
        for slot_id, value in {
            "source_mode": "upload",
            "source_reference": source_reference,
            "file_format": file_format,
        }.items():
            slot = state.slots[slot_id]
            slot.value = value
            slot.status = SlotStatus.PROVIDED
            slot.evidence_text = evidence
            slot.source_turn = len(state.turns) or None
            slot.confirmed_by_user = False
            slot.validation_errors = []
        state.dataset_columns = normalized_columns
        self._repository.save_state(state)
        self._repository.append_event(
            dialogue_id,
            "uploaded_file_attached",
            {
                "filename": filename,
                "source_reference": source_reference,
                "columns": normalized_columns,
            },
        )
        self._trace(
            "dataset.upload_attached",
            {
                "filename": filename,
                "columns": normalized_columns,
                "state_after": self._trace_state(state),
            },
        )
        return state.model_copy(deep=True)

    def _confirmed_context(self, state: DialogueState) -> dict[str, Any]:
        return {
            slot_id: slot.value
            for slot_id, slot in state.slots.items()
            if slot_id != "authentication_reference"
            and (slot.confirmed_by_user or slot.status == SlotStatus.CONFIRMED)
        }

    def _known_context(self, state: DialogueState) -> dict[str, Any]:
        return {
            slot_id: slot.value
            for slot_id, slot in state.slots.items()
            if slot_id != "authentication_reference"
            and slot.value is not None
            and slot.status != SlotStatus.UNMENTIONED
        }

    def _question_request(self, state: DialogueState, slot_id: str, reason: str) -> QuestionRequest:
        definition = self._schema.get(slot_id)
        active_ids = tuple(
            candidate.slot_id
            for candidate in self._schema.slots
            if candidate.slot_id != slot_id and is_slot_active(candidate, state)
        )
        return QuestionRequest(
            dialogue_id=state.dialogue_id,
            provider_conversation_id=state.provider_conversation_id,
            slot_id=slot_id,
            reason=reason,
            slot_description=definition.description,
            current_state=state.slots[slot_id].model_copy(deep=True),
            confirmed_context=self._confirmed_context(state),
            known_context=self._known_context(state),
            static_question=definition.static_question,
            allowed_values=definition.allowed_values,
            other_active_slot_ids=active_ids,
            available_dataset_columns=tuple(state.dataset_columns),
            priority_slots=tuple(rank_priority_slots(self._schema, state)),
        )

    def _sync_provider_context(self, state: DialogueState) -> None:
        getter = getattr(self._llm, "conversation_id_for", None)
        if not callable(getter):
            return
        conversation_id = getter(state.dialogue_id)
        if conversation_id and conversation_id != state.provider_conversation_id:
            state.provider_conversation_id = conversation_id

    async def _ask(self, request: QuestionRequest) -> str:
        for _ in range(2):
            try:
                output = await self._llm.ask(request)
            except Exception:
                break
            if validate_question(output, request):
                self._trace(
                    "question.accepted",
                    {"slot_id": request.slot_id, "question": output.question},
                )
                return output.question
            self._trace(
                "question.rejected",
                {"slot_id": request.slot_id, "question": output.question},
            )
        return static_fallback_question(request).question

    def _recover_selected_slot_answer(
        self,
        state: DialogueState,
        turn_number: int,
        message: str,
    ) -> tuple[DialogueState, str] | None:
        candidate = select_next_slot(self._schema, state)
        if candidate is None:
            return None
        definition = self._schema.get(candidate.slot_id)
        if definition.value_type not in {"enum", "boolean", "string", "duration"}:
            return None
        normalized = normalize_value(definition, message)
        if (
            candidate.slot_id == "source_mode"
            and self._is_affirmative_answer(message)
            and self._is_catalog_confirmation(self._previous_assistant_message(state))
        ):
            normalized = "catalog"
        if is_unusable_reference(candidate.slot_id, normalized):
            return None
        if candidate.slot_id == "intent" and self._is_affirmative_answer(message):
            normalized = Intent.CREATE_FORECAST.value
        if definition.value_type == "enum" and normalized not in definition.allowed_values:
            return None
        if definition.value_type == "boolean" and not isinstance(normalized, bool):
            return None
        if definition.value_type == "string" and (
            not isinstance(normalized, str) or not normalized.strip()
        ):
            return None
        if definition.value_type == "duration" and (
            not isinstance(normalized, dict) or validate_slot(
                definition,
                SlotState(
                    slot_id=candidate.slot_id,
                    value=normalized,
                    status=SlotStatus.PROVIDED,
                    evidence_text=message,
                ),
            )
        ):
            return None

        intent = state.intent
        intent_confidence = state.slots["intent"].confidence or 0.0
        if state.slots["intent"].value == Intent.CREATE_FORECAST.value:
            intent = Intent.CREATE_FORECAST
            intent_confidence = max(intent_confidence, 0.99)
        if candidate.slot_id == "intent" and normalized == Intent.CREATE_FORECAST.value:
            intent = Intent.CREATE_FORECAST
            intent_confidence = 1.0

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

    @staticmethod
    def _is_affirmative_answer(message: str) -> bool:
        normalized = message.strip().casefold()
        return normalized in {
            "yes",
            "y",
            "yeah",
            "yep",
            "correct",
            "confirm",
            "confirmed",
            "sure",
            "ok",
            "okay",
            "please do",
        }

    @staticmethod
    def _is_catalog_confirmation(question: str | None) -> bool:
        if not question:
            return False
        return "find the data in our catalog" in question.casefold()

    @staticmethod
    def _is_confirmation_prompt(question: str | None) -> bool:
        if not question:
            return False
        normalized = question.casefold()
        return "confirm" in normalized and "example answer:" in normalized

    @staticmethod
    def _previous_assistant_message(state: DialogueState) -> str | None:
        if len(state.turns) < 2:
            return None
        return state.turns[-2].assistant_message

    @staticmethod
    def _is_clarification_question(message: str) -> bool:
        normalized = message.strip().casefold()
        return "?" in message or normalized.startswith(
            (
                "what ",
                "which ",
                "how ",
                "why ",
                "do you mean",
                "can you ",
                "could you ",
                "please explain",
                "time span for",
            )
        )

    @staticmethod
    def _is_explanation_request(message: str) -> bool:
        normalized = " ".join(message.strip().casefold().split())
        return any(
            phrase in normalized
            for phrase in (
                "what do you mean",
                "what does this mean",
                "what are you asking",
                "what is meant by",
                "can you explain",
                "could you explain",
                "please explain",
                "why are you asking",
                "how can we improve",
            )
        )

    @staticmethod
    def _clarification_explanation(slot_id: str) -> str:
        explanations = {
            "source_mode": (
                "This asks where the data should come from: an uploaded file, an online "
                "service, a database, or our catalog."
            ),
            "frequency": (
                "This asks how often a new data value is recorded, such as every minute, "
                "day, week, or month."
            ),
            "forecast_horizon": (
                "This asks how far into the future you want predictions, such as the next "
                "7 days or 3 years."
            ),
            "target_description": "This asks exactly what value the system should predict.",
            "target_unit": "This asks which unit is used for the value being predicted.",
            "dataset_type": (
                "This asks whether the data describes one item, several separate items, "
                "or groups of items."
            ),
            "forecast_type": (
                "This asks whether you want one predicted value, an uncertainty range, "
                "or both."
            ),
            "output_granularity": (
                "This asks how you want the results grouped and displayed, for example "
                "one result per day for each item."
            ),
            "contains_sensitive_data": (
                "This asks whether the data contains personal, confidential, or regulated "
                "information."
            ),
            "target_column": (
                "This asks which field in the selected data contains the number to predict."
            ),
            "time_column": (
                "This asks which field tells us when each data value happened."
            ),
        }
        return explanations.get(slot_id, "This asks for the information described in the question.")

    def _explain_and_repeat(self, request: QuestionRequest) -> str:
        question = static_fallback_question(request).question
        return f"{self._clarification_explanation(request.slot_id)} {question}"

    async def _answer_user_question(
        self, message: str, request: QuestionRequest
    ) -> str:
        responder = getattr(self._llm, "answer_user_question", None)
        if callable(responder):
            try:
                answer = await responder(message, request)
            except Exception as error:  # noqa: BLE001 - provider boundary fallback
                self._trace(
                    "chat.answer_failure",
                    {"error_type": type(error).__name__},
                )
            else:
                if isinstance(answer, str) and answer.strip():
                    answer = answer.strip()
                    self._trace("chat.answer_accepted", {"answer": answer})
                    return answer
        return self._explain_and_repeat(request)

    def _pending_answer_feedback(
        self, state: DialogueState, message: str, slot_id: str | None = None
    ) -> str | None:
        candidate = (
            self._schema.get(slot_id)
            if slot_id is not None
            else select_next_slot(self._schema, state)
        )
        if candidate is None or len(state.turns) < 2 or not state.turns[-2].assistant_message:
            return None
        if self._is_clarification_question(message):
            return None
        definition = self._schema.get(candidate.slot_id)
        normalized = normalize_value(definition, message)
        invalid = is_unusable_reference(candidate.slot_id, normalized)
        if definition.value_type == "enum":
            invalid = invalid or normalized not in definition.allowed_values
        elif definition.value_type == "duration":
            invalid = invalid or not isinstance(normalized, dict) or bool(
                validate_slot(
                    definition,
                    SlotState(
                        slot_id=candidate.slot_id,
                        value=normalized,
                        status=SlotStatus.PROVIDED,
                        evidence_text=message,
                    ),
                )
            )
        if not invalid:
            return None
        if candidate.slot_id == "source_mode":
            if self._is_catalog_confirmation(self._previous_assistant_message(state)):
                return "Which source should I use instead? Example answer: upload a file."
            return (
                "Did you mean that I should find the data in our catalog? "
                "Example answer: yes."
            )
        if candidate.slot_id == "dataset_type":
            return (
                "Please tell me whether your data covers one item, several separate items, "
                "or groups of items. Example answer: several separate items."
            )
        if candidate.slot_id == "forecast_type":
            return (
                "Please choose one predicted value, a range showing uncertainty, or both. "
                "Example answer: one predicted value."
            )
        if candidate.slot_id == "frequency":
            return (
                "Please say how often a new data value is recorded, such as once per "
                "minute or once per day."
            )
        if candidate.slot_id == "forecast_horizon":
            return (
                "Please say how far into the future to predict, such as 7 days or 3 months."
            )
        if definition.value_type == "duration":
            return "Please provide a duration, such as 1 hour or 3 months."
        return "Please answer the question using one of the choices described."

    def _render_confirmation(self, state: DialogueState) -> str:
        def value(slot_id: str) -> Any:
            slot = state.slots.get(slot_id)
            if slot is None or slot.value is None:
                return None
            if slot.status in {SlotStatus.INVALID, SlotStatus.CONFLICTING, SlotStatus.AMBIGUOUS}:
                return None
            return slot.value

        def display(raw: Any) -> str | None:
            if raw is None:
                return None
            if isinstance(raw, dict) and {"periods", "unit"} <= set(raw):
                periods = raw["periods"]
                period_text = str(int(periods)) if isinstance(periods, float) and periods.is_integer() else str(periods)
                unit = str(raw["unit"])
                if period_text != "1" and not unit.endswith("s"):
                    unit += "s"
                return f"{period_text} {unit}"
            if isinstance(raw, list):
                return ", ".join(str(item) for item in raw)
            return str(raw)

        target = display(value("target_description")) or display(value("problem_statement"))
        geography = display(value("geography"))
        source_mode = display(value("source_mode"))
        source_text = {
            "catalog": "our data catalog",
            "upload": "your uploaded file",
            "api": "the connected online service",
            "database": "the connected database",
        }.get(source_mode or "", source_mode or "the selected data source")
        details = [
            f"the target is {target}" if target else None,
            f"for {geography}" if geography else None,
            f"using {source_text}",
            f"every {display(value('frequency'))}" if display(value("frequency")) else None,
            f"for the next {display(value('forecast_horizon'))}" if display(value("forecast_horizon")) else None,
            f"with values measured in {display(value('target_unit'))}" if value("target_unit") else None,
            f"reported as {display(value('output_granularity'))}" if value("output_granularity") else None,
        ]
        summary = ", ".join(item for item in details if item)
        return f"I understand that {summary}. Can I confirm these requirements? Example answer: yes."

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
        self._trace(
            "turn.completed",
            {
                "dialogue_id": str(state.dialogue_id),
                "turn_number": state.turns[-1].turn_number,
                "assistant_message": assistant_message,
                "ready": readiness.ready,
                "state_after": self._trace_state(state),
            },
        )
        return TurnResult(
            state=state.model_copy(deep=True),
            assistant_message=assistant_message,
            readiness=readiness,
        )

    async def handle_user_message(self, dialogue_id: UUID, message: str) -> TurnResult:
        state = self._load(dialogue_id)
        previous_assistant_message = state.turns[-1].assistant_message if state.turns else None
        confirmation_requested = self._is_confirmation_prompt(previous_assistant_message)
        turn_number = len(state.turns) + 1
        state.turns.append(DialogueTurn(turn_number=turn_number, user_message=message))
        pending_before = select_next_slot(self._schema, state)
        self._trace(
            "turn.user_message",
            {
                "turn_number": turn_number,
                "message": message,
                "pending_slot": pending_before.slot_id if pending_before else None,
                "state_before": self._trace_state(state),
            },
        )
        self._repository.append_event(
            dialogue_id,
            "user_message",
            {"turn_number": turn_number, "message": message},
        )

        if confirmation_requested and self._is_explanation_request(message):
            readiness = evaluate_readiness(self._schema, state)
            assistant = (
                "This is a summary of the forecasting requirements I have understood. "
                f"{self._render_confirmation(state)}"
            )
            self._repository.append_event(
                dialogue_id,
                "clarification_requested",
                {"turn_number": turn_number, "stage": "confirmation"},
            )
            return self._finish_turn(state, assistant, readiness)

        if (
            pending_before is not None
            and previous_assistant_message
            and self._is_clarification_question(message)
        ):
            request = self._question_request(
                state, pending_before.slot_id, pending_before.reason
            )
            assistant = await self._answer_user_question(message, request)
            readiness = evaluate_readiness(self._schema, state)
            self._repository.append_event(
                dialogue_id,
                "clarification_requested",
                {
                    "turn_number": turn_number,
                    "slot_id": pending_before.slot_id,
                },
            )
            self._trace(
                "question.clarified",
                {"slot_id": pending_before.slot_id, "question": assistant},
            )
            return self._finish_turn(state, assistant, readiness)

        if confirmation_requested and self._is_affirmative_answer(message):
            specification = self.confirm_specification(dialogue_id, confirm=True)
            state = self._load(dialogue_id)
            state.turns.append(DialogueTurn(turn_number=turn_number, user_message=message))
            readiness = evaluate_readiness(self._schema, state)
            self._trace(
                "specification.confirmed",
                {
                    "specification_id": str(specification.specification_id),
                    "deferred_slots": specification.deferred_slots,
                },
            )
            result = self._finish_turn(
                state,
                "Confirmed. The forecasting requirements are complete.",
                readiness,
            )
            return result.model_copy(update={"specification": specification})

        try:
            extraction = await self._llm.extract(message, state.model_copy(deep=True))
            self._sync_provider_context(state)
            self._trace("state.extraction_received", extraction.model_dump(mode="json"))
            recovered = self._recover_selected_slot_answer(state, turn_number, message)
            extracted_slot_ids = {update.slot_id for update in extraction.updates}
            recovery_is_for_pending_slot = (
                recovered is not None and recovered[1] not in extracted_slot_ids
            )
            bad_intent_for_recovery = extraction.intent in {
                Intent.NOT_FORECASTING,
                Intent.UNSUPPORTED,
            } | ({Intent.AMBIGUOUS} if recovered is not None and recovered[1] == "intent" else set())
            if recovered is not None and (
                recovery_is_for_pending_slot or bad_intent_for_recovery
            ):
                state, slot_id = recovered
                self._trace(
                    "state.recovery_applied",
                    {"slot_id": slot_id, "state_after": self._trace_state(state)},
                )
                self._repository.append_event(
                    dialogue_id,
                    "deterministic_recovery_applied",
                    {
                        "turn_number": turn_number,
                        "slot_id": slot_id,
                        "message": message,
                        "reason": "overrode unsupported intent for selected slot answer",
                    },
                )
            else:
                updated = apply_extraction(
                    state,
                    extraction,
                    self._schema,
                    turn_number,
                    message,
                )
                state = updated
                self._trace(
                    "state.extraction_applied",
                    {"state_after": self._trace_state(state)},
                )
                self._repository.append_event(
                    dialogue_id,
                    "extraction_applied",
                    extraction.model_dump(mode="json"),
                )
        except Exception as error:
            recovered = self._recover_selected_slot_answer(state, turn_number, message)
            if recovered is not None:
                state, slot_id = recovered
                self._trace(
                    "state.recovery_applied",
                    {"slot_id": slot_id, "state_after": self._trace_state(state)},
                )
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
                self._trace(
                    "state.extractor_failure",
                    {"error_type": type(error).__name__},
                )
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
                self._trace(
                    "state.next_slot",
                    {
                        "slot_id": candidate.slot_id,
                        "reason": candidate.reason,
                        "state_before_question": self._trace_state(state),
                    },
                )
                request = self._question_request(state, candidate.slot_id, candidate.reason)
                assistant = (
                    self._pending_answer_feedback(
                        state,
                        message,
                        pending_before.slot_id if pending_before is not None else None,
                    )
                    or await self._ask(request)
                )
                self._sync_provider_context(state)
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
        deferred_slots: list[str] = []
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
                else:
                    deferred_slots.append(definition.slot_id)
                continue
            if slot.value is None or slot.status in {
                SlotStatus.INVALID,
                SlotStatus.AMBIGUOUS,
                SlotStatus.CONFLICTING,
            }:
                if definition.requiredness != Requiredness.OPTIONAL:
                    deferred_slots.append(definition.slot_id)
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
            deferred_slots=deferred_slots,
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
