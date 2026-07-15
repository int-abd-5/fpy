# Task 5 Report: Deterministic State Reducer

## Implemented

- Added a pure, deep-copying `apply_extraction()` reducer.
- Rejects unknown slots and blank or non-substring evidence before any state mutation.
- Matches evidence case-insensitively against the current message only.
- Normalizes candidates, records status, validation errors, confidence, evidence, and source turn.
- Preserves confirmed values as conflicts unless correction intent is explicit.
- Replaces explicit corrections and clears user confirmation.
- Downgrades extractor-supplied `CONFIRMED` statuses to `PROVIDED`; orchestration owns confirmation.
- Validates slot identifiers against both the dialogue state and schema registry.
- Deep-copies normalized mutable candidates before storing them.
- Applies multiple updates in order without I/O or assistant messages.

## Tests

- TDD red phase: initial focused run failed at collection because `state_reducer` did not exist.
- Focused reducer suite: `19 passed`.
- Full suite: `66 passed`.
- Scoped Ruff: `ruff check src/forecasting_assistant/application/state_reducer.py tests/unit/test_state_reducer.py` passed.

## Concerns

- The reducer relies on the existing schema-shaped normalization and validation rules; malformed values are retained as `INVALID` state rather than discarded.
- Commit: `fix: harden reducer trust boundaries`.
