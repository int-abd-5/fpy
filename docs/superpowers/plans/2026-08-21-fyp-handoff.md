# Automated Time-Series Forecasting FYP Handoff and Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the FYP from the current trusted requirement-elicitation and dataset-discovery implementation toward automated preprocessing, model selection, evaluation, packaging, and inference.

**Architecture:** The system uses a hybrid design. The LLM performs evidence-bound extraction and generates one clarification question, while deterministic Python code owns the schema, state transitions, validation, readiness, confirmation, persistence, dataset eligibility, ranking, fetching, checksums, licenses, and caching. The next stages should preserve this trust boundary: model code may consume only a confirmed `ForecastingSpecification` and a validated dataset version.

**Tech Stack:** Python 3.11+, OpenAI Responses API with structured Pydantic output, Pydantic, Typer, SQLite, HTTP adapters, SHA-256 content-addressed storage, pytest, mypy, Ruff, and GitHub. Planned model-stage additions are Pandas or Polars, NumPy, Statsmodels, Scikit-learn, XGBoost or LightGBM, PyTorch, Optuna, MLflow, and FastAPI.

**Spec:** `README.md` and the original FYP forecasting proposal; this handoff records the implementation decisions made in the Codex task.

## Global Constraints

- Keep the LLM untrusted until deterministic evidence, identifier, status, and value checks pass.
- Keep `create_forecast` intent monotonic after it is detected.
- Ask one bounded question per turn and include a context-consistent `Example answer:`.
- Never use assistant suggestions as user evidence.
- Require explicit confirmation before dataset fetching and model handoff.
- Never store or commit raw API keys, passwords, bearer tokens, or database credentials.
- Keep public, redistributable datasets separate from private or user-uploaded storage namespaces.
- Run tests, mypy, Ruff, and `git diff --check` before committing model-stage changes.

## Current Repository State

- Repository: `https://github.com/int-abd-5/fpy.git`
- Current branch: `fix/context-aware-elicitation-prompts`
- Current commit: `22fe37f53024fb70f62f7db12bf6276fee8b1f78`
- Published branch: `origin/fix/context-aware-elicitation-prompts`
- Pull request URL: `https://github.com/int-abd-5/fpy/pull/new/fix/context-aware-elicitation-prompts`
- Validation at handoff: `174 passed`; mypy passed; Ruff passed on changed files.
- Local-only file: `bitcoin_prices.csv` is untracked and was intentionally not pushed.
- Do not assume the default `main` branch contains the latest prompt changes until the feature branch is merged.

## Chat and Account Transfer

The Codex thread/session identifier is not exposed to this repository context, so no reliable session ID can be provided here. Do not invent one. The portable continuation mechanism is this file plus the Git branch and commit above.

For the same OpenAI account, install the Codex/ChatGPT desktop app on the second laptop and sign in. If this Codex chat is available in the app history or Remote view, open it. Local files, terminals, databases, virtual environments, and local Codex state remain on the original computer unless copied separately.

For a different ChatGPT account, use the account's data export, locate `conversations.json`, and upload it into a new conversation on the destination account. OpenAI documents this as a reference workaround; it does not recreate the original chat sidebar or merge the accounts. Do not upload `.env`, API keys, private credentials, or sensitive database files.

## New-Laptop Setup

```powershell
git clone -b fix/context-aware-elicitation-prompts https://github.com/int-abd-5/fpy.git
cd fpy
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set local values in `.env` without committing the file:

```dotenv
OPENAI_API_KEY=replace-with-a-new-or-securely-transferred-key
OPENAI_MODEL=your-structured-output-model
ELICITATION_DB_PATH=elicitation.db
DATASET_STORE_PATH=dataset_store
SCHEMA_VERSION=1.0.0
PROMPT_VERSION=llmrei-long-forecasting-v1
```

Run the smoke checks:

```powershell
python -m pytest -q
python -m mypy src
python -m ruff check src tests
```

If the World Bank demo CSV is needed, copy `bitcoin_prices.csv` separately or create a new local fixture. It is not part of the GitHub branch.

## Implemented Features

### Requirement Elicitation

- Structured extraction through `OpenAIResponsesClient`.
- A 79-slot forecasting schema in `src/forecasting_assistant/domain/schema.py`.
- Intent, slot status, evidence, confidence, corrections, and confirmation state.
- Deterministic normalization and cross-field validation.
- Priority-based clarification selection.
- SQLite persistence for dialogue state, turns, events, and specifications.
- LLMREI-long question generation with one-question validation and deterministic fallback.
- Yes/no recovery for the currently selected enum or boolean slot.
- Monotonic `create_forecast` intent lock.
- Pending-slot and known-context data passed to the extractor/question generator.
- Context-aware examples, including annual World Bank examples such as `3 years`, `annual`, and `overall series`.

### Trusted Dataset Pipeline

- Trusted adapter registry in `src/forecasting_assistant/infrastructure/datasets/registry.py`.
- Dataset adapters in `src/forecasting_assistant/infrastructure/datasets/adapters.py`.
- World Bank API discovery and fetching.
- Explicit recommendation selection before fetching.
- License and reuse checks.
- Schema, integrity, training-point, and source validation.
- SHA-256 content-addressed caching in `dataset_store`.
- Dataset plans, selections, and versions persisted in SQLite.
- Dataset-only commands work without an OpenAI key.

### Demonstration Commands

```powershell
forecast-elicitation interview
forecast-elicitation seed-world-bank-demo
forecast-elicitation discover-datasets DIALOGUE_UUID --user-id demo
forecast-elicitation confirm-dataset PLAN_UUID CANDIDATE_ID --user-id demo
forecast-elicitation fetch-dataset SELECTION_UUID
forecast-elicitation web
```

The World Bank demo target is Pakistan annual consumer price inflation:

```text
indicator: FP.CPI.TOTL.ZG
country: PK
frequency: annual
source reference: world-bank:PK:FP.CPI.TOTL.ZG
provider: World Bank
license: CC BY 4.0
```

## File Map

- `src/forecasting_assistant/domain/schema.py`: 79-slot forecasting schema.
- `src/forecasting_assistant/domain/models.py`: dialogue, slot, question, specification, and dataset models.
- `src/forecasting_assistant/application/orchestrator.py`: turn handling, extraction application, question selection, and confirmation.
- `src/forecasting_assistant/application/state_reducer.py`: deterministic state update and intent-lock behavior.
- `src/forecasting_assistant/application/clarification.py`: readiness and next-slot ranking.
- `src/forecasting_assistant/application/validation.py`: slot and cross-field validation.
- `src/forecasting_assistant/prompts/extractor.py`: extractor instructions, redaction, pending-slot context, and safe provider input.
- `src/forecasting_assistant/prompts/llmrei_long.py`: bounded LLMREI-long prompt, example generation, and question validation.
- `src/forecasting_assistant/infrastructure/llm/openai_responses.py`: structured OpenAI Responses API adapter.
- `src/forecasting_assistant/infrastructure/datasets/adapters.py`: trusted source implementations.
- `src/forecasting_assistant/application/dataset_discovery.py`: discovery, ranking, selection, fetching, and validation orchestration.
- `src/forecasting_assistant/interfaces/cli.py`: interview, demo, discovery, confirmation, fetch, and web commands.
- `tests/integration/test_elicitation_flow.py`: end-to-end elicitation and 15-turn hallucination regression.
- `tests/unit/test_question_policy.py`: LLMREI-long question and context-aware example tests.
- `tests/unit/test_extractor_prompt.py`: extractor boundary, redaction, and pending-slot tests.
- `tests/unit/test_state_reducer.py`: state precedence and intent-lock tests.
- `tests/unit/test_dataset_*.py`: dataset ranking, adapters, persistence, and validation tests.

## Next Implementation Plan

### Task 1: Define the validated model-input contract

**Files:**
- Create: `src/forecasting_assistant/domain/modeling.py`
- Modify: `src/forecasting_assistant/application/dataset_validation.py`
- Test: `tests/unit/test_modeling_contract.py`

- [ ] Write tests for converting a fetched dataset version plus confirmed specification into a typed modeling input.
- [ ] Reject missing target column, missing time column, invalid frequency, insufficient observations, and mismatched dataset type.
- [ ] Preserve source version ID, SHA-256, specification ID, target, time field, horizon, frequency, and quality report.
- [ ] Run `python -m pytest -q tests/unit/test_modeling_contract.py`.

### Task 2: Build deterministic preprocessing

**Files:**
- Create: `src/forecasting_assistant/application/preprocessing.py`
- Create: `src/forecasting_assistant/domain/preprocessing.py`
- Test: `tests/unit/test_preprocessing.py`

- [ ] Implement timestamp parsing, sorting, duplicate policy, missing timestamp policy, missing target policy, and frequency checks.
- [ ] Implement single-series preprocessing first; reject panel/hierarchical data until their grouping contract is implemented.
- [ ] Record every transformation in a preprocessing report with input and output row counts.
- [ ] Add leakage protection so future observations are not used before the backtest cutoff.
- [ ] Run focused tests and the complete suite.

### Task 3: Add candidate forecasting models

**Files:**
- Create: `src/forecasting_assistant/models/protocol.py`
- Create: `src/forecasting_assistant/models/baselines.py`
- Create: `src/forecasting_assistant/models/statistical.py`
- Create: `src/forecasting_assistant/models/tree_based.py`
- Test: `tests/unit/test_model_candidates.py`

- [ ] Define a common fit/predict interface with model name, configuration, required history, and output horizon.
- [ ] Add naive and seasonal-naive baselines first.
- [ ] Add ETS and ARIMA-style statistical candidates.
- [ ] Add lag-feature tree-based candidates only after preprocessing exposes a leakage-safe feature view.
- [ ] Keep PyTorch/deep-learning candidates optional and behind an explicit configuration flag.

### Task 4: Implement rolling backtesting and tuning

**Files:**
- Create: `src/forecasting_assistant/application/backtesting.py`
- Create: `src/forecasting_assistant/application/model_selection.py`
- Modify: `src/forecasting_assistant/domain/models.py`
- Test: `tests/unit/test_backtesting.py`
- Test: `tests/integration/test_model_selection.py`

- [ ] Write tests for expanding-window folds and forecast-horizon-sized test windows.
- [ ] Implement MAE, RMSE, MASE, and sMAPE with safe handling for zero denominators.
- [ ] Compare every candidate against the configured baseline.
- [ ] Tune only within training folds and persist the selected configuration.
- [ ] Return a model-selection report containing fold metrics, aggregate metrics, runtime, and failure reasons.

### Task 5: Package artifacts and provide inference

**Files:**
- Create: `src/forecasting_assistant/application/artifacts.py`
- Create: `src/forecasting_assistant/interfaces/api.py`
- Test: `tests/unit/test_artifacts.py`
- Test: `tests/integration/test_inference_api.py`

- [ ] Package the selected model, preprocessing configuration, specification ID, dataset version ID, checksum, and metrics report.
- [ ] Validate artifact compatibility before loading it.
- [ ] Add a FastAPI endpoint for forecast requests and structured error responses.
- [ ] Add a CLI command that trains or loads the selected artifact and produces a forecast.
- [ ] Add an end-to-end test from fetched fixture to forecast response.

### Task 6: Add experiment tracking and reproducibility

**Files:**
- Create: `src/forecasting_assistant/application/experiment_tracking.py`
- Modify: `README.md`
- Test: `tests/integration/test_reproducibility.py`

- [ ] Record random seeds, package versions, model configurations, source checksums, and run timestamps.
- [ ] Add optional MLflow tracking without making the local demo depend on a server.
- [ ] Document CPU-only, local-GPU, and cloud-GPU execution modes.
- [ ] Add a reproducibility command that reruns a saved experiment from its run metadata.

## Continuation Prompt for the Other Account

Paste this into a new Codex chat after cloning the repository:

```text
Continue the Automated Time-Series Forecasting FYP from the repository state described in docs/superpowers/plans/2026-08-21-fyp-handoff.md. Use branch fix/context-aware-elicitation-prompts at commit 22fe37f53024fb70f62f7db12bf6276fee8b1f78. Read README.md and the handoff plan first. The existing implementation covers schema-guided LLMREI-long requirement elicitation, monotonic create_forecast intent, context-aware examples, World Bank dataset discovery, explicit selection, validation, SHA-256 caching, and SQLite persistence. Do not expose or request raw API keys in chat. The next task is to implement Task 1: the validated model-input contract, using TDD and preserving the existing trust boundary.
```

## Transfer Checklist

- [ ] Install the desktop app and sign into the destination account.
- [ ] Clone branch `fix/context-aware-elicitation-prompts`.
- [ ] Read `README.md` and this handoff file.
- [ ] Create a new `.env` locally and add the API key securely.
- [ ] Run the three smoke checks.
- [ ] Copy `bitcoin_prices.csv` only if the local demo needs it.
- [ ] Keep `elicitation.db` and `dataset_store` local unless their contents are intentionally transferred.
- [ ] Start a new Codex chat with the continuation prompt above.

