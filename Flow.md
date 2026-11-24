# Execution Flow

This document maps how a request travels through the repository. It is a file/function map for debugging and onboarding, not a replacement for the code. Update it whenever a new entry point, branch, API call, persistence step, or handoff is added or changed.

**Baseline documented:** 2026-11-18
**Primary application entry point:** `forecasting_assistant.interfaces.cli:app`
**State authority:** `ElicitationEngine` plus `SQLiteDialogueRepository`
**Current endpoint:** validated dataset handoff; model training is outside the current repository.

## How to maintain this file

For every implementation iteration:

1. Update the relevant flow section and the file/function table.
2. Add a new edge when execution crosses a new module, process, service, or storage system.
3. Update the error path if a fallback, retry, or fail-closed rule changes.
4. Add the related decision ID from `Decisions.md` when the reason for the edge is policy-driven.
5. Update the baseline date or commit identifier at the top.

## System overview

```text
CLI command or browser request
        |
        v
interface adapter
  cli.py / web.py
        |
        v
ElicitationEngine
        |
        +--> LLM provider adapter
        |      extract / ask / follow-up explanation
        |
        +--> deterministic application rules
        |      normalize -> reduce -> validate -> rank next slot -> readiness
        |
        +--> SQLite repository
        |      dialogue state, turns, events, confirmed specification
        |
        +--> JSONL pipeline logger
               redacted trace events

confirmed ForecastingSpecification
        |
        v
DatasetDiscoveryService
        |
        +--> DatasetSearchQuery
        +--> local/source adapters or hosted registry API
        +--> deterministic eligibility and ranking
        +--> SourcePlan with recommendations and reasons
        |
        v
explicit DatasetSelection
        |
        v
adapter fetch -> payload validation -> content-addressed object store
        |
        v
immutable DatasetVersion / handoff to the future modelling stage
```

## Deliverable III LaTeX report flow

The report is generated from the committee's supplied `FastFyp.cls` and `main.tex`, the existing Deliverable III content, the current implementation details, and recorded FYP-I results.

```text
FYPFast (1)/main.tex + FastFyp.cls + cover assets
output/latex/F26-012-deliverable-iii/main.tex + Chapters/ + fypbib.bib
        |
        v
tmp/pdfs/f26-deliverable-iii-template/build_report.py
  - assemble the complete report in the committee's main.tex structure
  - add Chapters 7, 9, and 10; reserve Chapter 8 for the FYP-II User Manual
  - set title-page and declaration details
  - format functional requirements as an explained, testable bullet list
  - create the relevant SDG 8/9 diagram and retain IEEE reference styling
  - copy FastFyp.cls and fypbib.bib into the source package
        |
        v
output/latex/F26-012-deliverable-iii-template/main.tex
        |
        +--> Tectonic + BibTeX --> build/main.pdf
        |      rerun references and contents; check compiler warnings
        |
        +--> render key pages and inspect layout, figures, tables, declarations,
               TOC/LoF/LoT, chapter boundaries, references, and final page count
                         |
                         v
output/final_submission/deliverable-iii-template/F26-012.pdf
output/latex/F26-012-deliverable-iii-template-source.zip
```

The latest build is 80 pages. It keeps the template's blank second page, 11-point body font, 1.5 line spacing, chapter-wise numbering, headers, and page-numbered contents and lists. The author names and roll numbers and the date are filled; the three signature rules remain blank for the students to sign. Figure 2.1 contains only an original summary of SDG 8 and SDG 9. The PDF filename is `F26-012.pdf`. See `Decisions.md` D-021 through D-026.

## LLM dataset/dependency context artifact

`docs/dataset_variable_dependency_context.json` is a manually supplied context document for LLM use; the application does not automatically load it into prompts. It is grounded in the current dataset domain model, query builder, registry adapter, and settings:

```text
domain/datasets.py + application/dataset_query.py
  + infrastructure/datasets/registry_adapter.py + config.py
      -> explain current request fields, source metadata, and defaults
      -> distinguish registry thresholds from per-variable min/max values
      -> state relationship/causality limits and fields not yet sent by code
      -> docs/dataset_variable_dependency_context.json
```

See `Decisions.md` D-020. Revise the context when the registry contract or adapter changes; do not assume this file changes runtime behavior.

## Entry points and initialization

### CLI commands

```text
forecast-elicitation interview
  -> interfaces.cli.interview()
  -> interfaces.cli.build_engine(persistent=False)
  -> get_settings()
  -> load_schema()
  -> JsonlPipelineLogger()
  -> SQLiteDialogueRepository.initialize()
  -> OpenAIResponsesClient()
  -> ElicitationEngine()
  -> asyncio.run(_run_interview(...))
```

```text
forecast-elicitation persistent-interview
  -> interfaces.cli.persistent_interview()
  -> interfaces.cli.build_engine(persistent=True)
  -> same repository/schema/logger wiring
  -> PersistentOpenAIResponsesClient()
  -> asyncio.run(_run_interview(...))
```

The normal interview uses a provider-stateless client. The persistent pilot uses one provider conversation per dialogue, but both modes use the same application engine and SQLite state. See `Decisions.md` D-002 and D-004.

```text
forecast-elicitation web --no-open
  -> interfaces.cli.web()
  -> interfaces.web.run_web_server()
  -> DashboardServer.__init__()
       -> get_settings()
       -> load_schema()
       -> SQLiteDialogueRepository.initialize()
       -> SQLiteDatasetCatalogRepository.initialize()
       -> JsonlPipelineLogger()
       -> PersistentOpenAIResponsesClient()
       -> ElicitationEngine()
       -> RegistryClient() when REGISTRY_API_URL is configured
       -> DatasetDiscoveryService()
       -> ThreadingHTTPServer()
```

## Dialogue lifecycle

### 1. Start or resume a dialogue

```text
CLI _run_interview() / POST /api/dialogues
  -> ElicitationEngine.start_dialogue()
  -> create_initial_state(schema)
  -> SQLiteDialogueRepository.save_state(state)
  -> SQLiteDialogueRepository.append_event("dialogue_started", ...)
  -> return DialogueState
```

The browser stores only the dialogue UUID in `sessionStorage`; the state itself is loaded from the backend. A resumed CLI or browser session calls `get_state()` and loads the persisted state.

### 2. Receive one user message

```text
CLI _run_interview() / POST /api/dialogues/{dialogue_id}/message
  -> ElicitationEngine.handle_user_message(dialogue_id, message)
  -> _load(dialogue_id)
  -> inspect previous assistant message
  -> append DialogueTurn(user_message=message)
  -> select_next_slot(schema, state)
  -> trace turn.user_message
  -> append SQLite event user_message
```

From here the engine chooses one of the short-circuit paths before calling extraction.

### 3. Short-circuit paths

```text
user asks what the confirmation means
  -> _is_explanation_request()
  -> _render_confirmation()
  -> save assistant response and return
```

```text
user asks what the current question means
  -> _is_clarification_question()
  -> _question_request()
  -> PersistentOpenAIResponsesClient.answer_user_question()
       or deterministic _explain_and_repeat()
  -> no extractor call and no slot update
  -> save assistant response and return
```

```text
the previous message was the final confirmation prompt and the user is affirmative
  -> confirm_specification(confirm=True)
  -> save specification and confirmed state
  -> return "Confirmed..."
```

These branches exist so an explanation request or a confirmation answer is not accidentally interpreted as a new forecasting fact.

## Extraction and state transition

### 4. Provider extraction

```text
ElicitationEngine.handle_user_message()
  -> llm_client.extract(message, state_copy)
  -> OpenAIResponsesClient.extract()
  -> build_extractor_instructions()
  -> build_extractor_input(message, state, schema)
  -> _request_context(dialogue_id, provider_conversation_id)
       normal client: {store: false}
       persistent client: create/reuse conversation + {store: true}
  -> client.responses.parse(..., text_format=ExtractorResult)
  -> trace api.extract.request
  -> trace api.extract.response or api.extract.failure
  -> return ExtractorResult
```

The provider receives the current message, the schema-conditioned state context, and the extraction instructions. It does not directly write SQLite.

### 5. Apply or recover the extraction

```text
ExtractorResult
  -> _sync_provider_context()
  -> _recover_selected_slot_answer()
  -> if recovery is appropriate:
       normalize_value()
       validate the selected slot
       apply_extraction() for the selected slot
       trace state.recovery_applied
     else:
       apply_extraction()
         -> state_reducer._check_contract()
              verify slot IDs
              verify evidence is attributable to current message
              ignore unsupported updates when other valid updates exist
              raise UnsupportedEvidenceError when all updates are unsupported
         -> _resolved_intent()
         -> _apply_update() for each valid update
              normalize value
              preserve confirmed values unless explicit correction is detected
              validate slot
              assign status, evidence, confidence, source turn
       trace state.extraction_applied
       append extraction_applied event
```

If the provider call fails or state application raises and no deterministic recovery is possible:

```text
provider/state error
  -> trace state.extractor_failure
  -> choose static question for the current next slot
  -> append extractor_failed event
  -> save assistant response
```

This is the main boundary that prevents an `UnsupportedEvidenceError` from silently erasing previously stored values: the current state is loaded first, and the fallback/recovery path works from that state.

## Validation, readiness, and next question

```text
updated DialogueState
  -> validate_dialogue(schema, state)
  -> append validation_completed event
  -> evaluate_readiness(schema, state)
       -> identify active required and conditional slots
       -> ignore catalog dataset details while catalog schema is unavailable
       -> identify intermediate unresolved core slots
       -> collect blocking validation issues
```

If the intermediate brief is ready:

```text
readiness.ready
  -> _render_confirmation(state)
  -> _finish_turn()
  -> save state
  -> append assistant_response event
  -> trace turn.completed
```

Otherwise:

```text
not ready
  -> select_next_slot(schema, state)
       -> source_mode/source_reference gate first
       -> intermediate core candidates next
       -> otherwise required/high-impact unresolved candidate
  -> trace state.next_slot with slot_id and reason
  -> _question_request()
       -> selected slot description
       -> current slot state
       -> confirmed and known context
       -> allowed values
       -> dataset columns when available
       -> ranked priority slots
  -> _pending_answer_feedback() when the latest answer is invalid
     otherwise _ask(request)
```

`_ask()` calls `llm_client.ask()` at most twice. Each call follows:

```text
QuestionRequest
  -> OpenAIResponsesClient.ask()
  -> build_question_instructions()
  -> build_question_input(request)
  -> provider responses.parse(..., text_format=QuestionOutput)
  -> validate_question(output, request)
  -> accept one bounded question
```

If both attempts fail, `static_fallback_question(request)` produces the schema question with an example answer. The final message is persisted by `_finish_turn()`.

## Confirmation and specification handoff

```text
user confirms
  -> ElicitationEngine.confirm_specification(dialogue_id, confirm=True)
  -> evaluate_readiness()
  -> iterate active schema slots
       -> copy usable values
       -> record user_provided_slots
       -> record confirmed_inferred_slots
       -> record documented_defaults
       -> record unresolved_optional_slots
       -> record deferred_slots
  -> build ForecastingSpecification
  -> state.confirmed = true
  -> SQLiteDialogueRepository.save_state()
  -> SQLiteDialogueRepository.save_specification()
  -> append specification_confirmed event
```

The CLI then calls `build_dataset_service()` and discovers catalog data. The web `POST /api/dialogues/{dialogue_id}/confirm` does the same and returns both the specification and a serialized source plan.

## Upload path

```text
browser file input
  -> FileReader -> base64
  -> POST /api/dialogues/{dialogue_id}/upload
  -> DashboardServer._store_upload()
       -> size and suffix checks
       -> write under dataset_store/uploads/{dialogue_id}/
       -> _extract_uploaded_columns()
       -> ElicitationEngine.attach_uploaded_file()
            -> set source_mode=upload
            -> set source_reference and file_format
            -> set dataset_columns
            -> save state and uploaded_file_attached event
  -> return state and column list
```

The upload is an explicit user action, so it can provide source and schema evidence without requiring an LLM interpretation of the file operation.

## Catalog discovery path

### 1. Build the query

```text
confirmed ForecastingSpecification
  -> DatasetDiscoveryService.discover_for_specification()
  -> query_from_specification()
  -> DatasetSearchQuery
       target / prompt
       geography / frequency / history
       source mode / source reference
       license and sensitive-data constraints
       production or research purpose
```

### 2. Search configured adapters

```text
DatasetDiscoveryService.discover()
  -> for each configured DatasetSourceAdapter.search(query)
       collect DatasetCandidate
       save candidate
       record source error without aborting every other source
  -> DatasetRanker.rank(candidate, query)
  -> split eligible and unavailable candidates
  -> sort deterministically
  -> keep top three eligible recommendations
  -> keep up to ten unavailable alternatives with reasons
  -> save SourcePlan
```

When `REGISTRY_API_URL` is configured, `build_default_adapters()` uses `LocalUploadAdapter` and `RegistryDatasetAdapter`. The registry adapter follows this path:

```text
RegistryDatasetAdapter.search(query)
  -> RegistryClient.health()
  -> _resolve_payload(query)
       canonical target, prompt, geo, frequency, thresholds
  -> RegistryClient.resolve(payload)
  -> map verified target_sources into DatasetCandidate
       retain companions, lineage, warnings, endpoint metadata
  -> return candidates to DatasetDiscoveryService
```

The registry request body is built from the confirmed specification. It is not built from the raw chat transcript alone. The canonical target mapping turns phrases such as inflation, GDP, bitcoin, or life expectancy into registry target identifiers when a mapping exists.

### 3. Browser catalog response

```text
POST /api/dialogues/{dialogue_id}/confirm
  -> confirm_specification()
  -> dataset_service.discover_for_specification()
  -> _source_plan_payload(plan)
  -> browser renders recommendations, scores, limitations, and source errors
```

The browser does not fetch a dataset merely because it was recommended. The user must select one.

## Dataset selection and fetch

```text
browser Use this dataset
  -> POST /api/dataset-plans/{plan_id}/confirm
  -> DatasetDiscoveryService.confirm_dataset()
       require confirm=True
       verify candidate is an eligible recommendation in this plan
       verify user scope when required
       save DatasetSelection(status=confirmed)
```

```text
browser Fetch dataset
  -> POST /api/dataset-selections/{selection_id}/fetch
  -> DatasetDiscoveryService.fetch_selection()
       load confirmed selection and candidate
       reject discovery-only/request-required acquisition
       enforce user scope for non-redistributable data
       reuse fresh cached DatasetVersion when valid
       adapter.fetch(candidate)
       _validate_fetched_content()
       validate_dataset_payload()
       ContentAddressedObjectStore.put()
       build DatasetVersion with SHA-256, license, query identity, quality metadata
       save version and mark selection fetched
  -> return DatasetVersion
```

The current endpoint is this validated dataset version. The future modelling stage should consume it together with `ForecastingSpecification`.

## Persistence and observability map

| Information | Runtime owner | Persistence/visibility |
| --- | --- | --- |
| Slot values and statuses | `DialogueState` | `dialogues.state_json` in SQLite |
| User/assistant turns | `DialogueState.turns` | `dialogues.state_json` and `events` |
| Provider conversation ID | `DialogueState.provider_conversation_id` | SQLite state |
| Confirmed specification | `ForecastingSpecification` | `specifications.specification_json` |
| State/business events | `SQLiteDialogueRepository.append_event()` | `events` table |
| API requests/responses and decisions | trace sinks from provider/engine | `ELICITATION_LOG_PATH` JSONL |
| Catalog query and recommendations | `SourcePlan` | dataset catalog repository tables |
| Raw/derived dataset bytes | `ContentAddressedObjectStore` | `DATASET_STORE_PATH` |
| Dataset metadata and quality | `DatasetVersion` | dataset catalog repository |

The JSONL log is sanitized through `safe_provider_value()` before writing. The UI does not display these traces, but developers can inspect them when the visible conversation is surprising.

## Error and fallback paths

```text
OpenAI request error
  -> provider traces error type, message, elapsed time, and cause chain
  -> engine attempts deterministic selected-slot recovery where possible
  -> otherwise static next-slot question
  -> state is preserved
```

```text
unsupported extraction evidence
  -> state reducer rejects unsupported update(s)
  -> if the current answer can be normalized for the selected slot:
       deterministic recovery applies that answer
     otherwise:
       static question is returned and prior state remains
```

```text
registry health/resolve error
  -> RegistryClient retries bounded transient failures
  -> adapter reports a source error to DatasetDiscoveryService
  -> other configured adapters may still be considered
  -> if REGISTRY_REQUIRED is true, /healthz reports 503 when registry is unavailable
```

```text
dataset fetch or validation error
  -> reject the payload
  -> do not create a DatasetVersion
  -> return a safe error to CLI/browser
```

## Live workflow evaluation path

The reproducible live test path is separate from the normal user interface but uses the same application objects:

```text
evaluation/live_workflow_scenarios.json
  -> scripts/run_live_workflows.py
  -> for each scenario, sequentially:
       create temporary SQLite state and object store
       create PersistentOpenAIResponsesClient
       start one dialogue
       optionally attach a synthetic uploaded CSV
       send initial message
       inspect the engine-selected pending slot
       send the scenario’s answer
       optionally ask one plain-language clarification
       continue until explicit confirmation or the eight-turn cap
       build DatasetSearchQuery
       call configured catalog adapters/registry
       select the top eligible recommendation with a synthetic user scope
       attempt validated fetch
  -> evaluation/live_workflow_results.json
```

The result file keeps the visible user/assistant transcript, per-turn latency, total latency, selected query, recommendations, source errors, fetch status, and dataset version metadata. It does not contain the OpenAI API key. A turn-cap failure is a measured product outcome, not a successful completion.

Latest baseline on 2026-10-20:

| Measure | Result |
| --- | ---: |
| Scenarios | 6 |
| Reached confirmation and discovery | 1 |
| Produced an eligible recommendation | 1 |
| Completed validated dataset fetch | 1 |
| Hit the eight-turn interview cap | 5 |
| Main repeated failure | Forecast horizon values such as “5 years” |

Pilot evaluation on the isolated `codex/pilot-deterministic-interview` branch:

| Measure | Baseline | Final pilot |
| --- | ---: | ---: |
| Scenarios reaching confirmation | 1/6 | 5/6 |
| Validated dataset fetches | 1 | 2 |
| Average interview turns | 7.50 | 5.50 |
| Repeated user-answer retries | 11 total | 0 total |
| Average scenario runtime | 53.22 s | 28.26 s |

The final pilot report is `evaluation/live_workflow_results_pilot_final.json`; the per-step automated test ledger is `evaluation/pilot_step_results.json`. The upload scenario still exceeded the eight-turn cap. One catalog fetch returned HTTP 502 from the selected WHO endpoint, while the state and query fixes themselves completed the interview and produced an eligible recommendation.

Use the scenario transcript to distinguish provider extraction, state recovery, slot ranking, catalog query construction, and dataset-fetch behavior. See `Decisions.md` D-016.

## File and function map

| Responsibility | File | Main functions/classes |
| --- | --- | --- |
| CLI commands and dependency wiring | `src/forecasting_assistant/interfaces/cli.py` | `build_engine`, `build_dataset_service`, `_run_interview`, `interview`, `persistent_interview`, `discover_datasets`, `confirm_dataset`, `fetch_dataset`, `web` |
| Browser HTTP boundary and UI | `src/forecasting_assistant/interfaces/web.py` | `dashboard_html`, `DashboardServer`, `health_payload`, `_store_upload`, `run_web_server` |
| Orchestration | `src/forecasting_assistant/application/orchestrator.py` | `ElicitationEngine`, `handle_user_message`, `_recover_selected_slot_answer`, `_ask`, `confirm_specification`, `_finish_turn` |
| Slot priority and readiness | `src/forecasting_assistant/application/clarification.py` | `select_next_slot`, `rank_priority_slots`, `evaluate_readiness`, catalog deferral helpers |
| State contract and reduction | `src/forecasting_assistant/application/state_reducer.py` | `_check_contract`, `_canonical_evidence`, `_apply_update`, `apply_extraction` |
| Normalization and validation | `src/forecasting_assistant/application/normalization.py`, `validation.py` | `normalize_value`, `normalize_extracted_value`, `extract_explicit_frequency`, `extract_explicit_forecast_horizon`, `validate_slot`, `validate_dialogue`, `is_unusable_reference` |
| Interview schema and domain models | `src/forecasting_assistant/domain/schema.py`, `domain/models.py` | `load_schema`, `create_initial_state`, `SlotDefinition`, `DialogueState`, `ExtractorResult`, `ForecastingSpecification` |
| LLM provider adapters | `src/forecasting_assistant/infrastructure/llm/openai_responses.py` | `OpenAIResponsesClient`, `PersistentOpenAIResponsesClient`, `extract`, `ask`, `answer_user_question` |
| Provider input construction | `src/forecasting_assistant/prompts/extractor.py`, `prompts/llmrei_long.py` | `build_extractor_instructions`, `build_extractor_input`, `build_question_instructions`, `build_question_input`, `validate_question` |
| Dialogue persistence | `src/forecasting_assistant/infrastructure/persistence/sqlite_repository.py` | `SQLiteDialogueRepository.initialize`, `save_state`, `load_state`, `append_event`, `save_specification` |
| Trace persistence and redaction | `src/forecasting_assistant/infrastructure/observability/pipeline_logger.py` | `JsonlPipelineLogger.__call__` |
| Dataset query construction | `src/forecasting_assistant/application/dataset_query.py` | `query_from_specification` |
| Dataset discovery and fetch lifecycle | `src/forecasting_assistant/application/dataset_discovery.py` | `DatasetDiscoveryService.discover_for_specification`, `discover`, `confirm_dataset`, `fetch_selection` |
| Eligibility and ranking | `src/forecasting_assistant/application/dataset_ranking.py` | `DatasetRanker.rank`, `ranking_sort_key` |
| Registry API client | `src/forecasting_assistant/infrastructure/datasets/registry_client.py` | `RegistryClient.health`, `resolve`, `_request` |
| Registry-to-domain adapter | `src/forecasting_assistant/infrastructure/datasets/registry_adapter.py` | `RegistryDatasetAdapter.search`, `_resolve_payload`, `_candidate_from_source`, `fetch` |
| Source registration | `src/forecasting_assistant/infrastructure/datasets/registry.py` | `build_default_adapters` |
| Secure endpoint download | `src/forecasting_assistant/infrastructure/datasets/http.py` | `validate_public_https_url`, `SecureHttpClient.get_bytes` |
| Payload validation | `src/forecasting_assistant/application/dataset_validation.py` | `validate_dataset_payload` |
| Dataset byte storage | `src/forecasting_assistant/infrastructure/datasets/object_store.py` | `ContentAddressedObjectStore.put` |
| Deployment contract | `render.yaml`, `src/forecasting_assistant/config.py` | Render start/health settings and environment-backed `Settings` |
| Live workflow scenarios | `evaluation/live_workflow_scenarios.json`, `scripts/run_live_workflows.py` | Sequential live conversations through confirmation, discovery, selection, and fetch |
| Live workflow results | `evaluation/live_workflow_results.json`, `evaluation/live_workflow_results_pilot_final.json` | Baseline and pilot transcripts, timings, queries, recommendations, and fetch outcomes |
| LLM dataset/dependency context | `docs/dataset_variable_dependency_context.json` | Portable LLM context for catalog fields, variable ranges, dependency thresholds, companion relations, and current API limits |
| LaTeX report generation | `tmp/build_f26_native_latex.py`, `output/latex/F26-012-native/main.tex` | Convert report content to native LaTeX with the supplied class and chapter-wise figure/table counters |
| Report figures and build output | `output/latex/F26-012-native/Figures/`, `output/latex/F26-012-native/build/main.pdf` | Committee logos, extracted diagrams, full SDG grid, and compiled report |

## Debugging checkpoints

| Symptom | First place to inspect | What it distinguishes |
| --- | --- | --- |
| A correct first answer disappears | `api.extract.response`, `state.extraction_received`, `state.extraction_applied`, `state.recovery_applied` | Provider extraction vs evidence rejection vs recovery |
| The same question repeats | `state.next_slot`, `validation_completed`, slot status in `turn.completed` | Priority loop vs invalid value vs failed extraction |
| “Your data list” becomes a file question | `source_mode` status and `catalog_dataset_*_deferred` behavior | Source normalization/deferral vs provider wording |
| Confirmation never appears | `evaluate_readiness` output and blocking issues | Missing core slot vs validation issue |
| Registry returns no catalog data | registry request payload, registry response, source errors, rank rejection reasons | Query construction vs registry response vs local eligibility |
| Dataset fetch fails | adapter response, payload validation, secure URL checks | Endpoint/security/content problem |
| Browser cannot continue | browser network request and matching `do_GET`/`do_POST` route | Frontend state vs backend route/error |

## Future extension boundary

The intended next flow after `DatasetVersion` is:

```text
DatasetVersion + ForecastingSpecification
  -> schema inspection and normalization
  -> hierarchical/panel structure inference
  -> time-aware train/validation split
  -> baseline and candidate model search
  -> backtesting and metric comparison
  -> selected forecasting artifact
  -> optional API/package export
```

That path is intentionally shown as a planned extension, not as a claim about current code. When implementation begins, add exact files/functions and a new decision record before replacing these planned edges with confirmed ones.


## Deliverable III author-voice document build (2026-11-22)

`output/latex/F26-012-deliverable-iii-template/main.tex` supplies the full report. Revision fragments in `tmp/report-voice/` hold disjoint chapter edits; `assemble.py` restores their original order and checks chapter/section headings, labels, references, citation keys, graphics references and numeric table values. It writes the revised root `main.tex` under `output/latex/F26-012-deliverable-iii-voice/`. Tectonic compiles that source with the unchanged FAST class and project bibliography. The final ZIP includes the report source, class, bibliography, figures, PDF, build instructions and an unchanged `university-template-original/` archive. This is a document workflow and does not alter the application's interview or dataset execution.

## Final Deliverable III packaging (2026-11-22)

The editable source now flows from `output/latex/F26-012-deliverable-iii-voice/` into `output/latex/F26-012-deliverable-iii-final/`. The final directory keeps the supplied `FastFyp.cls` unchanged, updates the report front matter and bibliography metadata, and compiles `main.tex` with `fypbib.bib` and `Figures/` to `build/main.pdf`. The ZIP in Downloads packages the root source, compiled `F26-012.pdf`, build instructions, and the byte-identical original template archive. The package does not change the forecasting application's runtime flow.
