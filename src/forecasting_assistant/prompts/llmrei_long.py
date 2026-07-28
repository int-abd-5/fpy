from __future__ import annotations

import json
import re

from forecasting_assistant.domain.models import QuestionOutput, QuestionRequest
from forecasting_assistant.prompts.extractor import safe_provider_value


def build_question_instructions() -> str:
    return (
        "You are a forecasting requirements interviewer following LLMREI-long guidance.\n"
        "Your only goal is to elicit requirements for the selected slot in the forecasting schema.\n"
        "Ask exactly one concise question at a time.\n"
        "Use the user's wording and confirmed context whenever possible.\n"
        "Probe ambiguity with clarification questions; do not assume or fill in missing details.\n"
        "Do not ask about any other slot, feature, model, dataset, metric, target, horizon, or value unless the user explicitly mentions it.\n"
        "Do not propose features, models, datasets, metrics, values, or alternatives on your own.\n"
        "Do not invent assumptions, examples, summaries, numbering, or analysis.\n"
        "Keep the conversation strictly focused on collecting one requirement per turn."
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = phrase.replace("_", " ").strip().lower()
    if not normalized:
        return False
    return re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text.lower()) is not None


def validate_question(output: QuestionOutput, request: QuestionRequest) -> bool:
    question = output.question.strip()
    if len(question) > 300 or question.count("?") != 1 or not question.endswith("?"):
        return False

    for slot_id in request.other_active_slot_ids:
        if slot_id != request.slot_id and _contains_phrase(question, slot_id):
            return False

    confirmed_text = json.dumps(
        request.confirmed_context, ensure_ascii=False, sort_keys=True, default=str
    ).lower()
    for candidate in request.allowed_values:
        if _contains_phrase(question, candidate) and candidate.lower() not in confirmed_text:
            return False
    return True


def build_question_input(request: QuestionRequest) -> str:
    payload = safe_provider_value(request.model_dump(mode="python"))
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def static_fallback_question(request: QuestionRequest) -> QuestionOutput:
    return QuestionOutput(question=request.static_question)
