# Forecasting Requirement Elicitation

This repository implements the first milestone of an automated time-series forecasting pipeline: turning a free-text request into a validated, explicitly confirmed `ForecastingSpecification`. It stops at the contract boundary for the future data-source planner; it does not fetch data or train forecasting models.

## Research Basis

The design combines two research directions:

- [LLMREI: Requirements Elicitation with LLMs](https://arxiv.org/abs/2507.02564) and its [replication prompts](https://doi.org/10.5281/zenodo.14988928) provide the adaptive, professional, one-question interview behavior.
- [Schema-Guided Dialogue State Tracking](https://arxiv.org/abs/2002.01359) provides explicit intents, described slots, categorical constraints, state tracking, and schema-versioned dialogue behavior.
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) provides the provider contract used for Pydantic extraction and question objects.

The hybrid rule is deliberate: the LLM extracts evidence-bound candidate updates and words one selected question; deterministic application code owns slot definitions, state precedence, validation, question priority, readiness, confirmation, and persistence.

## Pipeline

```text
user message
  -> schema-conditioned structured extraction
  -> evidence and identifier checks
  -> deterministic state reducer
  -> normalization and cross-field validation
  -> readiness and clarification ranking
  -> bounded LLMREI-long question or static fallback
  -> explicit confirmation
  -> ForecastingSpecification
  -> future data-source planner
```

The versioned schema contains 79 detailed slots across request, target, time, series, source, history, quality, seasonality, covariates, output, evaluation, operations, and governance areas.

## Trust Boundary

- LLM output is untrusted until identifiers, evidence, values, and statuses pass deterministic checks.
- Evidence must be a case-insensitive substring of the current user message; assistant suggestions cannot become user facts.
- An extractor cannot mark a value as user-confirmed.
- Confirmed values cannot be overwritten unless explicit correction intent is detected.
- Readiness requires a forecasting intent, all active required/conditional values, confirmed required inferences, and no blocking validation issues.
- Question output must contain exactly one bounded question about the selected slot. Invalid output retries once, then uses the schema's static question.
- Provider failure preserves dialogue state and uses a deterministic fallback.

## Setup

Requires Python 3.11 or later.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

On macOS or Linux, activate with `source .venv/bin/activate` and copy with `cp .env.example .env`.

Configure `.env`:

```dotenv
OPENAI_API_KEY=your-provider-key
OPENAI_MODEL=your-structured-output-model
ELICITATION_DB_PATH=elicitation.db
SCHEMA_VERSION=1.0.0
PROMPT_VERSION=llmrei-long-forecasting-v1
```

The model remains configurable. Automated tests use injected fakes and never require a network connection or API key.

## Interactive CLI

```powershell
forecast-elicitation interview
```

Resume an existing dialogue:

```powershell
forecast-elicitation interview --dialogue-id 00000000-0000-0000-0000-000000000000
```

Commands:

- `/show` prints the current persisted, redacted dialogue state.
- `/confirm` explicitly confirms a ready specification and prints formatted JSON.
- `/quit` exits without confirming.

The CLI emits one assistant message per user turn.

## Schema and State

Schema version `1.0.0` is loaded through `load_schema()`. Unsupported versions fail closed. Every dialogue stores its schema version, and every slot starts as `unmentioned`.

Slot statuses:

- `unmentioned`: no supported evidence has been supplied.
- `provided`: directly supported by the current user message.
- `inferred`: derived from user evidence and awaiting confirmation when required.
- `ambiguous`: multiple interpretations remain.
- `conflicting`: a new value conflicts with an accepted confirmed value.
- `invalid`: normalization or validation failed.
- `dont_care`: the user explicitly deferred a value where policy permits it.
- `confirmed`: explicitly accepted through the confirmation flow.

Conditional slots are activated only by named Python predicates; rule strings are never evaluated dynamically.

## Privacy and Secrets

- Never enter raw API keys, passwords, bearer tokens, signatures, or database credentials as forecasting requirements.
- Protected sources accept only externally managed references such as `secret://warehouse-readonly`.
- Provider prompts, state snapshots, events, transcripts, and specifications are recursively redacted before external transmission or SQLite persistence.
- Safe `secret://` references are preserved; embedded query credentials are not.
- SQL statements are parameterized, and audit events are append-only.

## Verification

Run focused and complete checks:

```powershell
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest -q
python -m ruff check src tests evaluation scripts
python -m mypy src
```

Build and validate the deterministic benchmark:

```powershell
python evaluation/build_scenarios.py
python scripts/evaluate_elicitation.py --condition all --client fake
```

The benchmark contains exactly 60 scenarios:

- 15 complete
- 15 missing required
- 10 ambiguous
- 10 multi-series or hierarchical
- 5 contradictory
- 5 probabilistic/covariate

It reports intent accuracy, slot micro precision/recall/F1, average and joint goal accuracy, clarification precision/success, completion rate, average turns, unsupported-value rate, confirmation-correction rate, and one-question compliance for `hybrid`, `schema_no_clarification`, and `unrestricted_llmrei_long` conditions.

## Planner Handoff

Explicit confirmation emits:

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

The future data-source planner should consume this object only after readiness passes and explicit confirmation is recorded. It may use source mode/reference, worksheet or table, schema fields, quality policies, history, covariates, and governance constraints, but must resolve `secret://` references outside dialogue storage.
