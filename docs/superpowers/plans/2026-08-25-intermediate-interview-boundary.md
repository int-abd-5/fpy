# Intermediate Interview Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the elicitation interview collect a concise, high-value forecasting brief, show the highest-priority unresolved requirements in numbered API input, and stop for explicit confirmation before entering advanced machine-learning details.

**Architecture:** Keep the existing evidence-bound extractor, deterministic reducer, and question writer. Add a deterministic intermediate policy that defines core requirements, ranks active unresolved slots, and treats non-core advanced slots as deferred once the core brief is complete. Pass the ranked policy as structured request context without changing prompt instruction text.

**Tech Stack:** Python 3.11+, Pydantic, pytest, OpenAI Responses API, SQLite persistence.

**Spec:** User-provided LLMREI-long conversation in the current task and the forecasting schema in `src/forecasting_assistant/domain/schema.py`.

## Global Constraints

- Do not modify the prompt instruction strings in `src/forecasting_assistant/prompts/`.
- Preserve explicit user confirmation before a specification is finalized.
- Keep advanced hierarchy, covariate, governance, and model-evaluation details deferred in intermediate mode.
- Do not remove schema slots; deferred values remain available for later pipeline stages.
- Do not require a network connection for tests.

### Task 1: Regression tests for priority context and bounded readiness

**Files:**
- Modify: `tests/unit/test_clarification.py`
- Modify: `tests/unit/test_extractor_prompt.py`
- Modify: `tests/unit/test_question_policy.py`
- Modify: `tests/integration/test_elicitation_flow.py`

- [x] Add a test proving the API input contains numbered priority slots in descending priority order.
- [x] Add a test proving a state with the intermediate core brief resolved is ready for confirmation even when advanced slots remain unresolved.
- [x] Add a test proving a missing core requirement still produces a question.
- [x] Run the focused tests and confirm they fail before production changes.

### Task 2: Implement the intermediate policy

**Files:**
- Modify: `src/forecasting_assistant/application/clarification.py`
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `src/forecasting_assistant/domain/models.py`
- Modify: `src/forecasting_assistant/prompts/extractor.py`
- Modify: `src/forecasting_assistant/prompts/llmrei_long.py`

- [x] Define a core slot set with source, target meaning, frequency, horizon, output granularity, dataset shape, and unit, plus target/time columns when the dataset schema is known or an uploaded source requires them.
- [x] Add a function that returns numbered active priority slots for provider input.
- [x] Make readiness use the intermediate core boundary while retaining blocking validation issues.
- [x] Add ranked priority context to extractor and question inputs without changing instruction strings.
- [x] Keep the existing question selection behavior inside the core boundary.

### Task 3: Confirmation and documentation

**Files:**
- Modify: `src/forecasting_assistant/application/orchestrator.py`
- Modify: `README.md`
- Modify: `.env.example` only if a setting is required (expected: no new setting).

- [x] Render a concise human-readable confirmation summary rather than dumping every unresolved advanced slot.
- [x] Document that `/confirm` completes the intermediate brief and advanced requirements remain deferred.
- [x] Preserve downstream access to unresolved schema slots.

### Task 4: Verification

- [x] Run the full pytest suite.
- [x] Run mypy on `src`.
- [x] Run targeted Ruff checks on changed files and `git diff --check`.
- [x] Inspect the diff to ensure prompt instruction strings were not changed by this task.
