# Graph Report - fpy  (2026-09-29)

## Corpus Check
- 79 files · ~52,463 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 918 nodes · 2895 edges · 49 communities (29 shown, 20 thin omitted)
- Extraction: 71% EXTRACTED · 29% INFERRED · 0% AMBIGUOUS · INFERRED: 834 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `095fceaa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DialogueState
- load_schema
- safe_provider_value
- test_validation.py
- Intent
- test_openai_adapter.py
- DatasetCandidate
- DatasetSearchQuery
- Forecasting Requirement Elicitation
- DatasetVersion
- QuestionRequest
- interfaces/__init__.py
- cli.py
- KeyError
- evaluate_elicitation.py
- http.py
- RegistryClient
- SourceRole
- FakeAdapter
- RegistryDatasetAdapter
- ValueError
- MemoryCatalogRepository
- model_validator
- StrEnum
- RuntimeError
- evaluation/__init__.py
- scripts/__init__.py
- datasets/__init__.py
- forecasting-requirement-elicitation
- Connection
- FakeHttp
- web.py
- validate_dataset_payload
- SQLiteDatasetCatalogRepository
- .__init__
- ContentAddressedObjectStore
- ForecastingSpecification
- RegistryClient
- test_render_readiness.py
- FetchResult
- HttpClient
- Settings
- SQLiteDialogueRepository
- Path
- UUID

## God Nodes (most connected - your core abstractions)
1. `load_schema()` - 101 edges
2. `DatasetCandidate` - 77 edges
3. `DialogueState` - 73 edges
4. `SlotStatus` - 71 edges
5. `create_initial_state()` - 70 edges
6. `DatasetSearchQuery` - 56 edges
7. `Intent` - 53 edges
8. `ExtractorResult` - 50 edges
9. `QuestionOutput` - 48 edges
10. `ElicitationEngine` - 47 edges

## Surprising Connections (you probably didn't know these)
- `test_interview_uses_one_asyncio_loop_for_all_turns()` --uses--> `TurnResult`  [INFERRED]
  tests/integration/test_cli.py → src/forecasting_assistant/domain/models.py
- `test_build_engine_wires_the_persistent_pipeline_logger()` --uses--> `Settings`  [INFERRED]
  tests/integration/test_cli.py → src/forecasting_assistant/config.py
- `test_extractor_candidate_value_has_a_typed_strict_schema()` --uses--> `ExtractorResult`  [INFERRED]
  tests/unit/test_openai_adapter.py → src/forecasting_assistant/domain/models.py
- `test_non_local_http_registry_url_is_rejected()` --uses--> `RegistryClient`  [INFERRED]
  tests/unit/test_registry_client.py → src/forecasting_assistant/infrastructure/datasets/registry_client.py
- `test_healthz_reports_app_and_registry_status_without_secrets()` --calls--> `LocalUploadAdapter`  [INFERRED]
  tests/unit/test_render_readiness.py → src/forecasting_assistant/infrastructure/datasets/adapters.py

## Import Cycles
- None detected.

## Communities (49 total, 20 thin omitted)

### Community 0 - "DialogueState"
Cohesion: 0.05
Nodes (84): DialogueRepository, KeyError, _candidate_status(), catalog_dataset_detail_deferred(), catalog_dataset_schema_deferred(), ClarificationCandidate, evaluate_readiness(), intermediate_core_slot_ids() (+76 more)

### Community 1 - "load_schema"
Cohesion: 0.07
Nodes (85): fixture, model_validator, apply_extraction(), _apply_update(), _canonical_evidence(), _check_contract(), _resolved_intent(), UnknownSlotError (+77 more)

### Community 2 - "safe_provider_value"
Cohesion: 0.16
Nodes (12): Durable, redacted observability helpers for the elicitation pipeline., JsonlPipelineLogger, Any, Path, Append one redacted, machine-readable record for every pipeline trace event., _context_slot(), _is_secret_key(), Any (+4 more)

### Community 3 - "test_validation.py"
Cohesion: 0.12
Nodes (41): _duration_from_text(), _enum_key(), is_iana_timezone(), _items(), _normalize_enum_value(), normalize_value(), Any, validate_dialogue() (+33 more)

### Community 4 - "Intent"
Cohesion: 0.15
Nodes (48): FakeLLMClient, ExtractorResult, Intent, QuestionOutput, Protocol, StructuredLLMClient, FakeLLMClient, InMemoryDialogueRepository (+40 more)

### Community 5 - "test_openai_adapter.py"
Cohesion: 0.08
Nodes (42): AsyncOpenAI, Exception, MonkeyPatch, SimpleNamespace, LLMContractError, OpenAIResponsesClient, PersistentOpenAIResponsesClient, Any (+34 more)

### Community 6 - "DatasetCandidate"
Cohesion: 0.11
Nodes (13): DatasetSourceAdapter, DatasetCandidate, FetchResult, NASAPowerAdapter, PMDWIS2Adapter, WHOGHOAdapter, WorldBankAdapter, DatasetSourceAdapter (+5 more)

### Community 7 - "DatasetSearchQuery"
Cohesion: 0.17
Nodes (13): _date(), _duration_text(), Any, query_from_specification(), _string_list(), DatasetRanker, _frequency_unit(), _geography_matches() (+5 more)

### Community 8 - "Forecasting Requirement Elicitation"
Cohesion: 0.13
Nodes (14): Deploy the FYP web service on Render, Forecast Specification and Dataset Handoff, Forecasting Requirement Elicitation, Interactive CLI, Intermediate Interview Boundary, Pipeline, Privacy and Secrets, Remote data registry (+6 more)

### Community 9 - "DatasetVersion"
Cohesion: 0.13
Nodes (17): DatasetCandidateNotSelectableError, DatasetDiscoveryService, DatasetPlanNotFoundError, DatasetSelectionNotFoundError, KeyError, UUID, ValueError, Store a normalized derivative without overwriting its immutable raw parent. (+9 more)

### Community 10 - "QuestionRequest"
Cohesion: 0.18
Nodes (23): QuestionRequest, build_question_input(), _contains_phrase(), _context_value(), _contextual_example(), _duration_unit(), example_answer(), static_fallback_question() (+15 more)

### Community 12 - "cli.py"
Cohesion: 0.13
Nodes (28): callback, command, DatasetDiscoveryService, ElicitationEngine, SQLiteDialogueRepository, build_dataset_service(), build_engine(), _compose_trace_sinks() (+20 more)

### Community 14 - "evaluate_elicitation.py"
Cohesion: 0.23
Nodes (15): build_scenarios(), _case(), main(), Any, validate_scenarios(), compute_metrics(), _divide(), evaluate() (+7 more)

### Community 15 - "http.py"
Cohesion: 0.18
Nodes (9): HTTPRedirectHandler, Request, Any, ValueError, SecureHttpClient, UnsafeDatasetUrlError, validate_public_https_url(), _ValidatedRedirectHandler (+1 more)

### Community 16 - "RegistryClient"
Cohesion: 0.12
Nodes (24): Protocol, RuntimeError, _clean_payload(), _is_local_host(), _normalize_base_url(), Any, The registry returned an invalid or non-successful API response., The registry could not be reached after bounded retries. (+16 more)

### Community 17 - "SourceRole"
Cohesion: 0.14
Nodes (22): AcquisitionMode, CatalogClass, LicenseAssessment, StrEnum, SelectionStatus, SourceRole, _candidate(), international_catalog_adapters() (+14 more)

### Community 18 - "FakeAdapter"
Cohesion: 0.53
Nodes (12): _candidate(), FakeAdapter, parametrize, Path, _service(), test_discovery_returns_only_top_three_and_isolates_adapter_failures(), test_executable_payload_fails_before_object_storage(), test_invalid_or_inadequate_dataset_payloads_fail_closed() (+4 more)

### Community 19 - "RegistryDatasetAdapter"
Cohesion: 0.10
Nodes (25): DatasetCandidate, DatasetSearchQuery, date, FetchResult, HttpClient, Settings, _as_optional_string(), _first_field_value() (+17 more)

### Community 34 - "FakeHttp"
Cohesion: 0.31
Nodes (6): FakeHttp, Any, test_ndma_mhvra_and_open_data_pakistan_are_not_automatic_sources(), test_pmd_wis2_core_metadata_is_production_eligible_input(), test_research_catalog_stays_separate(), test_who_adapter_returns_concrete_matching_indicator_endpoint()

### Community 35 - "web.py"
Cohesion: 0.15
Nodes (22): Connection, DialogueState, Path, ReadinessReport, _connect(), dashboard_html(), _extract_uploaded_columns(), _json_default() (+14 more)

### Community 36 - "validate_dataset_payload"
Cohesion: 0.43
Nodes (6): DatasetPayloadValidationError, _json_point_count(), Any, ValueError, validate_dataset_payload(), QualityReport

### Community 37 - "SQLiteDatasetCatalogRepository"
Cohesion: 0.18
Nodes (7): DatasetSelection, Connection, Path, UUID, SQLiteDatasetCatalogRepository, Path, test_dataset_catalog_round_trips_candidate_plan_selection_and_version()

### Community 38 - ".__init__"
Cohesion: 0.18
Nodes (9): BaseHTTPRequestHandler, BaseSettings, HTTPStatus, get_settings(), Settings, DashboardServer, test_settings_accept_an_explicit_model_name(), test_settings_default_model_allows_dataset_only_commands() (+1 more)

### Community 40 - "ForecastingSpecification"
Cohesion: 0.08
Nodes (19): ForecastingSpecification, DialogueRepository, Any, Protocol, UUID, Any, BaseModel, Connection (+11 more)

### Community 42 - "test_render_readiness.py"
Cohesion: 0.36
Nodes (9): Run the web interface; PORT is used automatically when provided by Render., web(), run_web_server(), _settings(), test_cli_dataset_service_passes_settings_to_adapter_factory(), test_healthz_reports_app_and_registry_status_without_secrets(), test_required_registry_failure_returns_service_unavailable(), test_web_dashboard_uses_registry_configured_adapters() (+1 more)

## Knowledge Gaps
- **14 isolated node(s):** `ApprovedFutureSource`, `forecasting-requirement-elicitation`, `Deploy the FYP web service on Render`, `Forecast Specification and Dataset Handoff`, `Interactive CLI` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_schema()` connect `load_schema` to `DialogueState`, `test_validation.py`, `Intent`, `test_openai_adapter.py`, `.__init__`, `cli.py`, `evaluate_elicitation.py`?**
  _High betweenness centrality (0.249) - this node is a cross-community bridge._
- **Why does `ForecastingSpecification` connect `ForecastingSpecification` to `DialogueState`, `load_schema`, `Intent`, `DatasetSearchQuery`, `DatasetVersion`, `cli.py`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `DatasetCandidate` connect `DatasetCandidate` to `validate_dataset_payload`, `SQLiteDatasetCatalogRepository`, `DatasetSearchQuery`, `DatasetVersion`, `SourceRole`, `FakeAdapter`, `MemoryCatalogRepository`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `load_schema()` (e.g. with `main()` and `evaluate()`) actually correct?**
  _`load_schema()` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `DatasetCandidate` (e.g. with `DatasetDiscoveryService` and `DatasetRanker`) actually correct?**
  _`DatasetCandidate` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `DialogueState` (e.g. with `_candidate_status()` and `catalog_dataset_detail_deferred()`) actually correct?**
  _`DialogueState` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 64 inferred relationships involving `SlotStatus` (e.g. with `_candidate_status()` and `evaluate_readiness()`) actually correct?**
  _`SlotStatus` has 64 INFERRED edges - model-reasoned connections that need verification._