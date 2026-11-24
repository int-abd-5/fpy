# Forecasting Dialogue Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the forecasting interview accept answers on the first attempt, ask about data availability before dataset columns, reject unusable placeholders, expose redacted API/state transitions, and use novice-friendly questions.

**Architecture:** Keep the LLM as an evidence-bound extractor and question writer. Add deterministic pending-slot recovery and validation at the application boundary, and emit opt-in redacted trace events from the orchestrator and OpenAI adapter. Dataset column existence is checked only after a dataset schema is available.

**Tech Stack:** Python 3.11+, Pydantic, pytest, OpenAI Responses API, Typer CLI, SQLite event repository.

**Spec:** Existing forecasting schema and elicitation workflow in `README.md` and `docs/elicitation_workflow_advisor_guide.md`.

## Global Constraints

- Preserve secret redaction and never log API keys or raw credentials.
- Keep structured extraction and deterministic state reduction as separate boundaries.
- Maintain one selected question per turn and include an illustrative example answer.
- Preserve the existing Python requirement of `>=3.11`.
- Do not require a network connection for tests.

### Task 1: Regression Tests for Pending Answers and Source Ordering

**Files:**
- Modify: `tests/integration/test_elicitation_flow.py`
- Modify: `tests/unit/test_question_policy.py`
- Create or modify: `tests/unit/test_clarification.py`

- [ ] Write tests proving `7 days` fills the pending duration slot, the source mode is selected before column slots, and refusal placeholders do not fill column/source slots.
- [ ] Run the focused tests and confirm they fail for the current implementation.

### Task 2: Deterministic Recovery and Dataset-Aware Validation

**Files:**
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `src/forecasting_assistant/application/clarification.py`
- Modify: `src/forecasting_assistant/application/validation.py`
- Modify: `src/forecasting_assistant/application/normalization.py` only if normalization support is required
- Modify: `src/forecasting_assistant/domain/schema.py` for novice-facing wording and source priority

- [ ] Recover valid pending `duration`, `string`, `enum`, and `boolean` answers before applying unrelated extractor output.
- [ ] Prioritize `source_mode` and `source_reference` before target/time/series columns when no dataset schema is available.
- [ ] Reject phrases such as `no dataset`, `not available`, and `the system will fetch it` for field names and source identifiers.
- [ ] Add dataset-column validation when known columns are present, without pretending to validate columns before a dataset is loaded.

### Task 3: Traceability and Novice-Friendly Questions

**Files:**
- Modify: `src/forecasting_assistant/infrastructure/llm/openai_responses.py`
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `src/forecasting_assistant/interfaces/cli.py`
- Modify: `src/forecasting_assistant/domain/models.py` if a trace model is needed
- Add tests under `tests/unit/` and `tests/integration/`

- [ ] Add opt-in trace output showing turn number, pending slot, sanitized user input, API request stage, sanitized structured response, reducer result, and next slot.
- [ ] Keep traces off by default and redact credentials, tokens, and secret references appropriately.
- [ ] Rewrite technical slot descriptions and generated question instructions in plain language while retaining internal slot identifiers.
- [ ] Add explanatory parentheticals only where the concept cannot be expressed plainly.

### Task 4: Verification

**Files:**
- No additional production files.

- [ ] Run the full pytest suite.
- [ ] Run mypy on `src`.
- [ ] Run targeted Ruff on all modified production and test files.
- [ ] Run `git diff --check` and inspect the final diff for secret exposure or unrelated changes.
