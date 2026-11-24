# Ontology-Guided Forecasting Interview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the paper's ontology-guided interview principles to make the forecasting interviewer choose relevant questions, close completed branches, and avoid reopening intent or data-source decisions.

**Architecture:** Keep the LLM responsible for extracting answers and phrasing one question. Add an explicit forecasting interview ontology and deterministic gate-pruning/re-ranking layer around the existing schema and slot selector. The existing prompts and forecasting schema values remain unchanged.

**Tech Stack:** Python 3.12 virtual environment, Pydantic models, pytest, mypy.

**Spec:** arXiv:2605.05828v1, “From Chat to Interview: Agentic Requirements Elicitation with an Experience Ontology.”

## Global Constraints

- Do not change the existing LLM instruction strings.
- Do not add another LLM call for scoring or slot selection.
- Preserve current catalog aliases, deterministic recovery, and intermediate stopping behavior.
- Keep user evidence restricted to the current user message.

---

### Task 1: Make the forecasting ontology explicit

**Files:**
- Create: `src/forecasting_assistant/application/interview_ontology.py`
- Modify: `src/forecasting_assistant/application/clarification.py`
- Test: `tests/unit/test_clarification.py`

- [x] Add a deterministic mapping from schema areas and slot IDs to ontology aspect/dimension labels.
- [x] Add `ontology_path(slot_id)` and `gate_pruned_slots(schema, state)` helpers.
- [x] Make priority-slot payloads expose `aspect`, `dimension`, and `gate_status` without changing prompt instructions.
- [x] Add tests proving completed intent and inactive source branches are pruned.

### Task 2: Apply ontology metadata to selection and re-ranking

**Files:**
- Modify: `src/forecasting_assistant/application/clarification.py`
- Modify: `src/forecasting_assistant/prompts/extractor.py`
- Test: `tests/unit/test_extractor_prompt.py`
- Test: `tests/unit/test_clarification.py`

- [x] Add deterministic relevance bonuses from already accepted slots and the latest user message.
- [x] Preserve source-first gating and intermediate core priority.
- [x] Ensure a resolved forecast intent cannot re-enter the candidate list.
- [x] Verify the structured priority payload contains the ontology path and remains JSON serializable.

### Task 3: Verify the reported conversation

**Files:**
- Test: `tests/integration/test_elicitation_flow.py`

- [x] Add the exact conversation regression: forecast request, “our data list,” then a non-intent next question.
- [x] Run focused tests, the full pytest suite, mypy, and targeted Ruff checks.
- [x] Update the plan checkboxes only after verification passes.
