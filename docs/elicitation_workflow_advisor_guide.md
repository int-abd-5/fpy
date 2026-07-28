# Requirement Elicitation Workflow Advisor Guide

## Purpose

This module is the first stage of the FYP forecasting pipeline. It converts a user's natural-language forecasting request into a validated `ForecastingSpecification`. It does not fetch data or train models yet. Its output is the formal contract that the next stage, the data-source planner, will consume.

## High-Level Flow

1. User starts the CLI with `forecast-elicitation interview`.
2. System creates a new `DialogueState` with all schema slots initially `unmentioned`.
3. User sends a forecasting request.
4. LLM extractor returns structured intent and slot updates.
5. Deterministic checks reject unsupported slot IDs and evidence not present in the current user message.
6. State reducer normalizes values, applies precedence rules, and validates each slot.
7. Readiness checker finds missing, invalid, ambiguous, or conflicting active slots.
8. Clarification policy chooses the next highest-priority slot.
9. LLMREI-style question generator asks one focused question for that selected slot.
10. Loop repeats until the specification is ready.
11. User runs `/confirm`.
12. Final `ForecastingSpecification` is saved and printed as JSON.

## Research Mapping

- LLMREI contribution: adaptive requirements interview behavior, professional wording, one focused follow-up question, ambiguity probing.
- Schema-Guided Dialogue contribution: explicit intent, slot definitions, allowed values, dialogue state tracking, schema versioning, conditional slots.
- Our hybrid choice: LLM proposes evidence-bound updates and words questions; deterministic Python code owns validation, prioritization, confirmation, persistence, and final readiness.

## Main Components

- CLI entrypoint: `src/forecasting_assistant/interfaces/cli.py`
- Orchestrator: `src/forecasting_assistant/application/orchestrator.py`
- Schema: `src/forecasting_assistant/domain/schema.py`
- Domain models: `src/forecasting_assistant/domain/models.py`
- Extractor prompt: `src/forecasting_assistant/prompts/extractor.py`
- LLMREI question prompt: `src/forecasting_assistant/prompts/llmrei_long.py`
- State reducer: `src/forecasting_assistant/application/state_reducer.py`
- Normalization: `src/forecasting_assistant/application/normalization.py`
- Validation: `src/forecasting_assistant/application/validation.py`
- Clarification policy: `src/forecasting_assistant/application/clarification.py`
- SQLite persistence: `src/forecasting_assistant/infrastructure/persistence/sqlite_repository.py`

## Schema Size

- Total slots: 79
- Required slots: 16
- Conditional slots: 24
- Optional slots: 32
- Defaultable slots: 7

## Required Slots

These must be resolved before final confirmation:

- `intent`
- `problem_statement`
- `business_goal`
- `success_criteria`
- `target_column`
- `target_description`
- `target_unit`
- `time_column`
- `frequency`
- `forecast_horizon`
- `dataset_type`
- `source_mode`
- `source_reference`
- `forecast_type`
- `output_granularity`
- `primary_metric`

## Important Conditional Slots

Conditional slots activate only when relevant. Examples:

- `file_format` activates when `source_mode = upload`.
- `series_id_columns` activates when `dataset_type = panel` or `hierarchical`.
- `hierarchy_columns` activates when `dataset_type = hierarchical`.
- `prediction_interval_levels` or `quantiles` activate when probabilistic output is requested.
- `privacy_constraints` activates when sensitive data is present.
- `authentication_reference` activates when the source is protected.

## Minimum And Maximum User Questions

Minimum practical questions:

- 1 user message can provide all required information in one detailed prompt.
- Then `/confirm` is needed to save the final specification.
- So the minimum interview is one complete requirement message plus confirmation.

Normal expected questions:

- Around 8 to 16 focused questions for a simple dataset, depending on how much the first prompt contains.
- The system asks one slot at a time, so users are not forced to understand the whole schema.

Maximum schema-driven questions:

- Up to 79 slot questions if every required, conditional, optional, and defaultable slot is deliberately collected.
- In current policy, not every optional/defaultable slot blocks completion.
- The blocking maximum is normally 16 required slots plus only the conditional slots activated by earlier answers.

Why this is acceptable:

- A real user is not expected to know schema names.
- The assistant asks natural questions like "Which column contains the timestamps?" instead of asking for internal slot IDs.
- The system can extract several slots from one user answer, reducing total turns.

## Where Final Requirements Are Saved

Configured database path:

```dotenv
ELICITATION_DB_PATH=elicitation.db
```

Default local database:

```text
C:\Users\Abdul\Desktop\fyp\fpy\elicitation.db
```

SQLite tables:

- `dialogues`: latest full dialogue state as JSON.
- `events`: append-only audit log of user messages, extraction results, validation events, and assistant responses.
- `specifications`: final confirmed requirements as `specification_json`.

The final confirmed object is saved only after `/confirm` succeeds.

Useful query:

```powershell
sqlite3 elicitation.db "SELECT specification_json FROM specifications ORDER BY confirmed_at DESC LIMIT 1;"
```

## Final Specification Shape

The saved JSON has this structure:

```json
{
  "specification_id": "uuid",
  "dialogue_id": "uuid",
  "schema_version": "1.0.0",
  "values": {},
  "user_provided_slots": [],
  "confirmed_inferred_slots": [],
  "documented_defaults": {},
  "unresolved_optional_slots": [],
  "confirmed_at": "ISO-8601 timestamp"
}
```

The next pipeline stage should read `values` and use fields such as `source_mode`, `source_reference`, `target_column`, `time_column`, `frequency`, `forecast_horizon`, quality settings, and governance constraints.

## Current User Commands

- `forecast-elicitation interview`: start a new interview.
- `forecast-elicitation interview --dialogue-id <uuid>`: resume an old interview.
- `/show`: print current dialogue state.
- `/confirm`: save final requirements when ready.
- `/quit`: exit without confirmation.

## Example Advisor Demo

Use this scenario:

```text
I want to forecast the btc_usd_close column from my CSV dataset for bitcoin daily prices.
```

Then answer follow-up questions with:

```text
business goal: investment monitoring
success criteria: low MAE
target column: btc_usd_close
target description: Bitcoin daily closing price
target unit: USD
time column: date
frequency: 1 day
forecast horizon: 7 days
dataset type: single_series
source mode: upload
source reference: bitcoin_prices.csv
file format: csv
forecast type: point
output granularity: daily
primary metric: mae
```

When the assistant prints a confirmation summary, enter:

```text
/confirm
```

## Safeguards

- LLM output is not trusted directly.
- Unknown slot IDs are rejected.
- Evidence must come from the current user message.
- Assistant suggestions cannot become user facts.
- Confirmed values cannot be silently overwritten.
- Raw API keys and credentials are redacted or rejected.
- Protected credentials must be referenced as `secret://...`.
- SQL writes are parameterized.
- Events are append-only for auditability.

## Recent Robustness Fixes

- Natural language durations like `7 days`, `1 week`, and `the following week` normalize to structured durations.
- Enum aliases normalize correctly, for example `CSV -> upload`, `uploaded -> upload`, and `single_time_series -> single_series`.
- Short selected-slot answers like `upload` can be recovered deterministically if the LLM extractor fails.

## Likely Advisor Questions

Q: Why not let the LLM generate the full specification directly?
A: Because direct generation can hallucinate fields. Our design uses the LLM only for extraction and question wording, while deterministic code validates and stores the final contract.

Q: What happens if the user gives many details in one sentence?
A: The extractor can fill multiple slots in one turn, reducing the number of questions.

Q: What happens if the user gives an invalid value?
A: Validation marks the slot `invalid`, and the clarification policy asks for that slot again.

Q: What happens if the user changes an earlier answer?
A: If correction intent is detected, the old value is replaced. Otherwise conflicting changes are marked `conflicting`.

Q: Where is the final output used?
A: The future data-source planner consumes the confirmed `ForecastingSpecification`.

Q: Can optional slots remain empty?
A: Yes. Required and active conditional slots block completion; optional slots can remain unresolved unless policy treats them as high-impact.

Q: How do we inspect the final requirements?
A: Use `/confirm` output, query the `specifications` table, or load the `ForecastingSpecification` from the repository.

Q: Is the implementation testable without an API key?
A: Yes. Unit, integration, and fake benchmark tests use injected fake LLM clients.

Q: What is stored for audit?
A: Full redacted dialogue state, append-only events, and confirmed specifications.

Q: What is the main limitation right now?
A: It completes requirement elicitation only. Data fetching, forecasting model training, deployment, and API serving are future pipeline stages.

## Verification Commands

```powershell
python -m pytest -q
python -m ruff check src tests evaluation scripts
python -m mypy src
python scripts/evaluate_elicitation.py --condition all --client fake
```

