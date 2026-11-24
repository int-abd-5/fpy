# Persistent Interview Chat and Output Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the persistent interview feel like a normal chat while keeping diagnostic traces out of its terminal output.

**Architecture:** Keep the existing persistent provider conversation and local state authority. Add conversational handling at the CLI boundary for user questions, while preserving the existing deterministic clarification path for slot questions. Keep pipeline logging available to the file logger, but do not attach the terminal trace sink when running the persistent command.

**Tech Stack:** Python, Typer, asyncio, pytest, existing OpenAI Responses persistent client.

**Spec:** User request in the active task: persistent interview should answer user follow-up questions naturally, and no API/trace details should be shown while it runs.

## Global Constraints

- Do not change the existing LLM prompts.
- Do not remove persistent provider context or file-based pipeline logging.
- Do not display API requests, responses, provider conversation IDs, or trace labels in the persistent interview terminal.
- Preserve the existing ordinary interview diagnostic behavior unless the user explicitly changes it.

### Task 1: Reproduce the current persistent output boundary

**Files:**
- Inspect: `src/forecasting_assistant/interfaces/cli.py`
- Inspect: `src/forecasting_assistant/application/orchestrator.py`
- Test: `tests/integration/test_cli.py`

- [ ] **Step 1: Write failing tests** for persistent mode not emitting trace lines and for a user clarification request being handled without extracting it as a slot answer.
- [ ] **Step 2: Run the focused tests and confirm the failures identify the current output/handling behavior.**

### Task 2: Implement normal-chat handling and quiet persistent output

**Files:**
- Modify: `src/forecasting_assistant/interfaces/cli.py`
- Modify: `src/forecasting_assistant/application/orchestrator.py` only if the focused test proves the existing clarification path is insufficient.
- Test: `tests/integration/test_cli.py`
- Test: `tests/integration/test_elicitation_flow.py`

- [ ] **Step 1: Add a persistent-mode output sink that writes only the user-facing assistant message.**
- [ ] **Step 2: Keep the pipeline logger active but omit terminal trace emission for persistent mode.**
- [ ] **Step 3: Ensure user questions such as “What do you mean?” are answered and the pending question is repeated without corrupting slots.**
- [ ] **Step 4: Run focused tests and confirm they pass.**

### Task 3: Verify the complete change

**Files:**
- No additional production files expected.

- [ ] **Step 1: Run the complete test suite.**
- [ ] **Step 2: Run mypy, targeted lint, and `git diff --check`.**
- [ ] **Step 3: Document the exact command and explain that diagnostics remain in the log file rather than the terminal.**
