from __future__ import annotations

import json
import re

from forecasting_assistant.domain.models import QuestionOutput, QuestionRequest
from forecasting_assistant.prompts.extractor import safe_provider_value


def build_question_instructions() -> str:
    return (
        "You are a forecasting requirements interviewer following LLMREI-long guidance.\n"
        "Ask exactly one concise question about the selected slot.\n"
        "Adapt to the user's terminology and confirmed context.\n"
        "Probe ambiguity; do not assume an answer.\n"
        "Do not ask about any other slot.\n"
        "Do not propose features, models, datasets, metrics, or values unless examples were explicitly requested.\n"
        "Do not output analysis, summaries, numbering, or multiple alternatives."
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
