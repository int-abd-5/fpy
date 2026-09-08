# Forecasting Requirement Elicitation

This repository implements the first two milestones of an automated time-series forecasting pipeline: turning a free-text request into a validated, explicitly confirmed `ForecastingSpecification`, then discovering, ranking, explicitly selecting, and safely caching suitable datasets. It does not train forecasting models.

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
  -> production and research dataset catalogs
  -> deterministic eligibility and ranking
  -> top-three recommendations
  -> explicit dataset confirmation
  -> validated, versioned dataset cache
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
ELICITATION_LOG_PATH=logs/elicitation_pipeline.jsonl
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

To inspect the complete data flow during an interview, enable the redacted trace:

```bash
forecast-elicitation interview --trace
```

For the persistent-context pilot, run:

```bash
forecast-elicitation persistent-interview
```

This pilot creates one OpenAI Conversations API conversation for each dialogue and reuses it for the extraction, question, and user-follow-up chat calls. The conversation ID is saved with the local dialogue state, while SQLite remains authoritative for slot values, validation, readiness, and confirmation. The pilot uses provider-side storage, so use it only with data that is appropriate for that retention policy. The normal `interview` command remains stateless at the provider. Follow-up questions such as “What does this mean?” are answered in plain language and do not fill or change the pending requirement.

Every interview also appends the same redacted pipeline events to `logs/elicitation_pipeline.jsonl` by default. Set `ELICITATION_LOG_PATH` in `.env` to change the location. The file records timestamps, API request features and inputs, structured responses, state recovery/reducer results, selected next slots, and the exact assistant message shown to the user. API keys and credential values are redacted, but user messages can still contain sensitive business data; treat this file as sensitive.

The normal `interview --trace` command additionally prints those events to the terminal. API keys and credential values are never printed. Persistent interview is always chat-only in the terminal, even if the compatibility flag `persistent-interview --trace` is supplied; its diagnostics remain in the JSONL log file.

Useful trace stages include:

- `api.extract.request`: the instructions and JSON input sent for answer extraction.
- `api.extract.response`: the structured intent and slot updates returned by the model.
- `state.extraction_applied` or `state.recovery_applied`: what the application stored.
- `state.next_slot`: why the next question was selected.
- `api.question.request` and `api.question.response`: the question-generation exchange.

Commands:

- `/show` prints the current persisted, redacted dialogue state.
- `/confirm` explicitly confirms a ready specification and prints formatted JSON.
- `/quit` exits without confirming.

The CLI emits one assistant message per user turn.

## Web Preview

Run the persistent interview preview locally:

```bash
forecast-elicitation web --no-open
```

Then open `http://127.0.0.1:8765/`. The preview provides a chat-style interface, a CSV/JSON/Excel/Parquet upload button, a plain-language requirements view, and catalog recommendations with dataset selection and fetching. The web UI uses the persistent provider conversation and never displays API traces. The API key stays in the backend process; do not put it in browser code.

For the current FYP demonstration, host the UI and Python API together as one private service with persistent storage for SQLite, uploaded files, cached datasets, and the JSONL pipeline log. A later production deployment can split these responsibilities into a web client, a Python API service, managed database, and object storage, but the browser must still call the API rather than the OpenAI service directly.

## Intermediate Interview Boundary

The interview runs in an intermediate stage. It ranks at most twelve unresolved high-priority requirements for the provider and asks only what is needed for a useful brief: the forecast target, data source, forecast horizon, output grouping, and target unit. When the user supplies a file, data timing, data shape, provider, and privacy details can be checked from that file. When the user chooses the catalog, those dataset facts stay deferred until a catalog item has been selected and inspected.

For the catalog path, choosing the catalog is only a source choice. Before a catalog dataset has been selected and its schema inspected, the interview does not ask for column names, item identifiers, hierarchy levels, or other dataset-shape details. It completes and confirms the forecasting brief first, then dataset discovery and explicit dataset selection happen. After the selected dataset makes its columns available through `set_dataset_columns()`, the deferred dataset questions become eligible.

If the user asks what a question means, the application explains that specific question in simple language, repeats it with an example answer, and does not send that clarification message to the extractor or modify any slot.

Once that core brief is valid, the assistant presents a plain-language summary and asks for confirmation. Advanced choices such as covariates, detailed missing-value policies, model evaluation strategy, and privacy restrictions remain recorded as deferred slots instead of generating a long interview. The confirmed specification preserves those deferred slot IDs for later pipeline stages.

After `/confirm`, the CLI prints up to three eligible dataset recommendations. Discovery can also be run separately for a previously confirmed dialogue:

```powershell
forecast-elicitation discover-datasets DIALOGUE_UUID --user-id USER_SCOPE
forecast-elicitation confirm-dataset PLAN_UUID CANDIDATE_ID --user-id USER_SCOPE
forecast-elicitation fetch-dataset SELECTION_UUID
```

The production catalog includes local uploads, PMD WIS2, World Bank and NASA POWER machine sources plus fail-closed registrations for Pakistani and international official catalogs. NDMA, PDMA, PMD CDPC, publication-only portals, aggregators, and sources with unresolved rights cannot be fetched automatically. AutoForecast and Monash remain in a separate research catalog.

Public, explicitly redistributable payloads use a shared SHA-256 object store. Purchased, private, non-redistributable, and user-uploaded data use hashed per-user namespaces. All selections, versions, checksums, license snapshots, and source plans are persisted in SQLite.

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

## Forecast Specification and Dataset Handoff

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

The dataset planner consumes this object only after readiness passes and explicit confirmation is recorded. It uses source mode/reference, schema fields, quality policies, history, geography, and governance constraints, but resolves `secret://` references outside dialogue storage. Dataset fetching requires a second explicit confirmation of one eligible recommendation.
