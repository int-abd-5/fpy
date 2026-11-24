# Deterministic Interview Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the persistent forecasting interview without changing its LLM prompts by making explicit answers to the currently pending slot authoritative, normalizing duration answers consistently, and preventing malformed values from reaching catalog queries.

**Architecture:** Keep the persistent provider conversation for natural-language interpretation and explanations, but make the application state reducer authoritative for an answer to the slot selected by the application. Apply fixes in small, independently tested layers: pending-answer precedence, source/intent safeguards, and registry-query sanitization. Evaluate the pilot against the existing six live scenarios before deciding whether to keep it.

**Tech Stack:** Python 3.9+, Pydantic, pytest, SQLite repositories, persistent OpenAI Responses client, Render-backed dataset registry adapter.

**Spec:** `Decisions.md`, `Flow.md`, and `evaluation/live_workflow_scenarios.json`.

## Global Constraints

- Do not modify the LLM prompts.
- Do not change `main` directly; all implementation remains on the isolated pilot branch until an explicit keep decision.
- Preserve the existing persistent provider conversation behavior.
- Treat explicit user answers to the application-selected pending slot as higher priority than provider guesses.
- Store a test result after each step in `evaluation/pilot_step_results.json`.
- Keep credentials, raw API responses, and private source data out of committed evaluation artifacts.

## Review Focus

- A user answer such as `5 years` must fill `forecast_horizon` once, even if the provider returns numeric `5`.
- Catalog phrases such as `your data list` and `the catalog` must fill `source_mode=catalog` without asking for a file identifier.
- Forecast language must not be downgraded to a non-forecast intent by a later persistent turn.
- Structured wrappers such as `{\"text\": \"Pakistan's GDP growth\"}` must not be stringified into a registry query.
- Explicit annual frequency and geography must survive conversion from the confirmed specification to the registry request.

---

### Task 1: Capture the baseline

**Files:**
- Create: `evaluation/pilot_step_results.json`

- [x] Run `./.venv/bin/python -m pytest -q` and record the exact result.
- [x] Preserve the prior live scenario report as the comparison baseline.

### Task 2: Make pending-slot answers authoritative

**Files:**
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `src/forecasting_assistant/application/normalization.py`
- Modify: `src/forecasting_assistant/application/state_reducer.py`
- Test: `tests/integration/test_elicitation_flow.py`
- Test: `tests/unit/test_state_reducer.py`
- Test: `tests/unit/test_validation.py`

**Interfaces:**
- `ElicitationEngine.handle_user_message()` must prefer a valid deterministic answer for the selected pending slot over a conflicting provider update.
- Duration normalization must accept a numeric candidate when the evidence/current message supplies its unit, producing the existing `{\"periods\": number, \"unit\": unit}` shape.

- [x] Write a failing regression test for numeric provider horizon plus `5 years` evidence/current message.
- [x] Write a failing regression test showing a pending-slot answer is retained when the provider also returns a conflicting update.
- [x] Run the focused tests and confirm they fail for the intended reason.
- [x] Implement only the normalization and pending-slot precedence needed by those tests.
- [x] Run focused tests, then the complete automated suite.
- [x] Append the step result to `evaluation/pilot_step_results.json`.

### Task 3: Protect forecast intent and catalog source selection

**Files:**
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `src/forecasting_assistant/application/state_reducer.py`
- Test: `tests/integration/test_elicitation_flow.py`
- Test: `tests/unit/test_state_reducer.py`

**Interfaces:**
- Explicit catalog answers normalize to `source_mode=catalog` on the first valid response.
- Once forecast intent is established by the user’s request, later ambiguous provider intent cannot reopen or replace it.

- [x] Write focused failing tests for persistent-turn intent drift and catalog-source behavior.
- [x] Run them to verify the failure.
- [x] Implement the smallest deterministic guard without changing prompt text.
- [x] Run focused tests and the complete automated suite.
- [x] Append the step result to `evaluation/pilot_step_results.json`.

### Task 4: Sanitize confirmed values before registry queries

**Files:**
- Modify: `src/forecasting_assistant/application/normalization.py`
- Modify: `src/forecasting_assistant/application/dataset_query.py`
- Test: `tests/unit/test_dataset_query.py`
- Test: `tests/unit/test_validation.py`

**Interfaces:**
- String-valued specification fields are unwrapped or rejected when the provider returns a known text wrapper.
- `query_from_specification()` emits plain-string target/prompt values and preserves explicit geography/frequency.

- [x] Write failing tests for wrapped target values and explicit annual frequency.
- [x] Run them to verify the failure.
- [x] Implement value sanitization at the state/query boundary.
- [x] Run focused tests and the complete automated suite.
- [x] Append the step result to `evaluation/pilot_step_results.json`.

### Task 4b: Recover explicit initial time cues

**Files:**
- Modify: `src/forecasting_assistant/application/normalization.py`
- Modify: `src/forecasting_assistant/application/state_reducer.py`
- Test: `tests/unit/test_state_reducer.py`

**Interfaces:**
- On the first user message only, unambiguous cadence words such as `annually` and horizon phrases such as `next 5 years` may fill an otherwise unmentioned slot.
- Later answers are not treated as initial-message temporal inference.

- [x] Write a failing regression test for an initial message containing `annually` and `next 5 years`.
- [x] Run it to verify it fails.
- [x] Implement minimal explicit frequency and horizon extraction without changing prompts.
- [x] Run focused tests and the complete automated suite.
- [x] Append the step result to `evaluation/pilot_step_results.json`.

### Task 5: Evaluate and decide

**Files:**
- Modify: `scripts/run_live_workflows.py` only if the evaluation needs a documented pilot setting.
- Create/replace: `evaluation/live_workflow_results_pilot.json`
- Modify: `Decisions.md`
- Modify: `Flow.md`

- [x] Run all six live scenarios with the same scenario inputs and sanitized reporting.
- [x] Compare completion rate, turn count, repeated-question count, query quality, fetch success, and latency against the baseline.
- [x] Run the full automated suite and focused lint.
- [x] Record a keep/discard recommendation in `Decisions.md`.
- [x] Leave the pilot isolated until the user explicitly asks to merge or push it.
