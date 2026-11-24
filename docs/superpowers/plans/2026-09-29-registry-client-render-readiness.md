# Registry Client Integration and Render Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the FYP to the separately hosted Data Source Registry through its HTTP API and make the FYP web service deployable on Render without changing elicitation prompts.

**Architecture:** Add a dedicated registry API client and a `DatasetSourceAdapter` that translates registry resolution results into the existing `DatasetCandidate` model. The existing secure downloader continues fetching the registry-returned endpoint URLs, while local adapters remain available only when no registry URL is configured. The web service gains an application/registry health endpoint and Render-compatible startup/storage configuration.

**Tech Stack:** Python 3.11+, Pydantic Settings, stdlib `urllib`, existing `SecureHttpClient`, existing SQLite/object-store repositories, Typer, pytest, Render Blueprint YAML.

**Spec:** `docs/superpowers/specs/2026-09-29-registry-client-render-readiness.md`

## Global Constraints

- Modify only the FYP repository; do not modify the separately hosted registry repository.
- Never connect directly to the registry database.
- Use `GET /healthz` and `POST /resolve`; do not invent registry URLs or relationships.
- Accept only registry sources whose `status` is `verified`; keep `include_pending` false in production.
- Fetch returned dataset URLs through the existing `SecureHttpClient`.
- Do not change LLM prompts, prompt versions, slot definitions, or elicitation behavior.
- Keep local adapter behavior when `REGISTRY_API_URL` is unset.
- Never commit secrets or log registry/OpenAI credentials.
- Render startup must bind to `0.0.0.0` and use `$PORT`.

## Review Focus

- A malformed or incomplete registry response must become a controlled source error, not a crash or fabricated candidate. Test in Task 1 and Task 2.
- A registry source marked `pending_review`, `retired`, or lacking an endpoint must never become selectable. Test in Task 2.
- A configured registry outage must not silently fall back to unrelated local catalog data in required mode. Test in Task 3.
- A registry endpoint must still pass the existing secure download URL and content protections. Test in Task 2.
- Render health checks must not expose stack traces or secrets and must return a useful status quickly. Test in Task 3.

---

### Task 1: Add registry configuration and HTTP client

**Files:**
- Create: `src/forecasting_assistant/infrastructure/datasets/registry_client.py`
- Modify: `src/forecasting_assistant/config.py`
- Create: `tests/unit/test_registry_client.py`

**Interfaces:**
- Consumes: registry API contract from the approved spec; `Settings` from `config.py`.
- Produces: `RegistryClient`, `RegistryApiError`, `RegistryUnavailableError`, and registry settings used by the adapter and web health endpoint.

- [ ] **Step 1: Write failing client tests**

Add tests for:

```python
def test_resolve_posts_explicit_registry_payload_without_empty_optional_values(): ...
def test_health_requires_status_ok_and_db_ok(): ...
def test_transient_failures_retry_but_client_errors_do_not(): ...
def test_malformed_json_and_response_shape_raise_registry_api_error(): ...
def test_registry_api_key_is_sent_as_bearer_without_being_exposed_in_errors(): ...
```

Use an injected fake transport so tests never require a live registry. Assert that `POST /resolve` receives JSON with `include_pending=False`, thresholds `0.80` and `0.60`, dependency depth `2`, and source limit `12`, while unset optional values are omitted.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/unit/test_registry_client.py -v`

Expected: FAIL because the settings and client interfaces do not yet exist.

- [ ] **Step 3: Add registry settings**

Modify `Settings` in `src/forecasting_assistant/config.py` with these exact fields and defaults:

```python
registry_api_url: str = ""
registry_api_key: str = ""
registry_timeout_seconds: float = 10.0
registry_max_retries: int = 2
registry_min_relevance: float = 0.80
registry_min_companion_strength: float = 0.60
registry_max_dependency_depth: int = 2
registry_max_sources: int = 12
registry_include_pending: bool = False
registry_required: bool = False
```

Use Pydantic validation for bounded timeout/retry/threshold values. Do not rename existing settings.

- [ ] **Step 4: Implement `RegistryClient`**

Create:

```python
class RegistryClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        transport: RegistryTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None: ...

    def health(self, *, timeout_seconds: float | None = None) -> dict[str, Any]: ...
    def resolve(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_source(self, slug: str) -> dict[str, Any]: ...
```

The default transport must use stdlib HTTP JSON requests, normalize the base URL, allow local `http://127.0.0.1`/`localhost` development URLs, require HTTPS for non-local registry hosts, send `Authorization: Bearer ...` only when configured, and redact credentials from errors. Retry only timeouts, connection failures, and 5xx responses with bounded backoff. Validate that health returns a mapping with `status == "ok"` and `db_ok is True`; validate that resolve returns mapping keys `target_sources`, `companion_sources`, `lineage`, and `warnings` with list values.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run: `pytest tests/unit/test_registry_client.py -v`

Expected: PASS with no network access.

- [ ] **Step 6: Commit the isolated client work**

Commit only the new settings, client, and focused tests with message: `feat: add registry api client configuration`.

### Task 2: Implement registry-backed dataset discovery and fetching

**Files:**
- Create: `src/forecasting_assistant/infrastructure/datasets/registry_adapter.py`
- Modify: `src/forecasting_assistant/infrastructure/datasets/registry.py`
- Create: `tests/unit/test_registry_adapter.py`
- Modify: `tests/unit/test_dataset_sources.py`

**Interfaces:**
- Consumes: `RegistryClient` from Task 1, `DatasetSourceAdapter`, `DatasetSearchQuery`, `DatasetCandidate`, and `SecureHttpClient`.
- Produces: `RegistryDatasetAdapter` with `source_id == "data-registry"`; `build_default_adapters(http, settings=...)` behavior used by CLI and web.

- [ ] **Step 1: Write failing adapter tests**

Add tests for:

```python
def test_search_maps_verified_target_source_and_companion_metadata(): ...
def test_search_omits_pending_retired_unhealthy_or_url_less_sources(): ...
def test_search_builds_explicit_resolve_payload_from_query(): ...
def test_fetch_uses_secure_http_client_and_preserves_registry_metadata(): ...
def test_describe_returns_cached_candidate_by_stable_registry_slug(): ...
def test_configured_registry_replaces_remote_catalog_adapters_but_keeps_local_uploads(): ...
```

Use a fake `RegistryClient` and fake `HttpClient`. Assert target candidates use the registry slug as their canonical identifier, carry `registry` metadata including the original response, and preserve companion fields such as `dependency_score`, `relation_type`, `depth`, and `note`.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/unit/test_registry_adapter.py -v`

Expected: FAIL because the adapter and configured factory behavior do not yet exist.

- [ ] **Step 3: Implement source mapping**

Implement `RegistryDatasetAdapter`:

```python
class RegistryDatasetAdapter:
    source_id = "data-registry"

    def __init__(self, client: RegistryClient, http: HttpClient, *, settings: Settings) -> None: ...
    def search(self, query: DatasetSearchQuery) -> list[DatasetCandidate]: ...
    def describe(self, candidate_id: str) -> DatasetCandidate: ...
    def fetch(self, candidate: DatasetCandidate) -> FetchResult: ...
```

Build the resolve payload from confirmed query values only. Map verified target sources to production `DatasetCandidate` objects with stable IDs, provider/license metadata, geography, tags, fields, frequency, freshness, relevance score, endpoint type, fetch hint, lineage, and warnings. Map endpoint type `csv`/`array_csv` to `AcquisitionMode.DOWNLOAD`; map other fetchable API types to `AcquisitionMode.API`. Treat registry-verified sources as `SourceRole.OFFICIAL_SECONDARY` unless the response clearly identifies an aggregator. Preserve complete non-secret registry metadata under `metadata["registry"]` and companions under `metadata["registry_companions"]`.

- [ ] **Step 4: Implement fetch and description**

Use the candidate's registry-returned `source_url`/endpoint URL with `HttpClient.get_bytes`; do not add a second download implementation. Add registry slug and fetch-hint metadata to the returned `FetchResult.metadata` while preserving the secure client result. `describe` must return a deep copy from the adapter's candidate cache and raise `KeyError` for unknown IDs.

- [ ] **Step 5: Wire the adapter factory**

Change `build_default_adapters` to accept an optional `Settings` value without breaking existing callers:

```python
def build_default_adapters(
    http: HttpClient,
    *,
    settings: Settings | None = None,
) -> list[DatasetSourceAdapter]: ...
```

When `registry_api_url` is empty, preserve the current adapter list exactly. When it is configured, include `LocalUploadAdapter` and `RegistryDatasetAdapter`; do not silently mix unrelated local catalog sources into the hosted registry path. Use `registry_required` to control failure behavior at the application wiring layer in Task 3.

- [ ] **Step 6: Run adapter and regression tests**

Run: `pytest tests/unit/test_registry_adapter.py tests/unit/test_dataset_sources.py -v`

Expected: PASS, including the pre-existing local adapter tests.

- [ ] **Step 7: Commit the adapter work**

Commit only registry adapter/factory changes and their tests with message: `feat: resolve catalog datasets through registry api`.

### Task 3: Wire configuration into CLI/web and add Render health behavior

**Files:**
- Modify: `src/forecasting_assistant/interfaces/cli.py`
- Modify: `src/forecasting_assistant/interfaces/web.py`
- Create: `tests/unit/test_render_readiness.py`
- Modify: `tests/unit/test_web_interface.py`

**Interfaces:**
- Consumes: `Settings`, `RegistryClient`, `build_default_adapters`, and the existing `DatasetDiscoveryService`.
- Produces: CLI/web dataset services that use the registry configuration and a `GET /healthz` response suitable for Render.

- [ ] **Step 1: Write failing wiring and health tests**

Add tests for:

```python
def test_cli_dataset_service_passes_settings_to_adapter_factory(monkeypatch): ...
def test_web_dashboard_uses_registry_configured_adapters(monkeypatch, tmp_path): ...
def test_healthz_reports_app_and_registry_status_without_secrets(monkeypatch, tmp_path): ...
def test_required_registry_failure_returns_service_unavailable(monkeypatch, tmp_path): ...
def test_web_server_start_command_accepts_render_host_and_port(monkeypatch): ...
```

Use a fake registry client/adapter and instantiate the HTTP handler through `DashboardServer` without starting a listening process. Assert that `/healthz` returns JSON and never includes `OPENAI_API_KEY` or `REGISTRY_API_KEY`.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/unit/test_render_readiness.py tests/unit/test_web_interface.py -v`

Expected: FAIL for the new registry wiring and `/healthz` behavior.

- [ ] **Step 3: Wire settings into dataset service construction**

Update both CLI `build_dataset_service()` and `DashboardServer.__init__()` to pass `get_settings()` into `build_default_adapters`. Construct the registry adapter from the same settings instance so the CLI and web service cannot drift. If `registry_required` is true and the registry URL is absent, fail at service construction with a clear configuration error; if it is configured but unavailable, expose a controlled required-dependency failure rather than falling back to unrelated catalog adapters.

- [ ] **Step 4: Add the web `/healthz` endpoint**

Add a `DashboardServer.health_payload()` method and route `GET /healthz`. The response should include only non-secret fields such as application status, registry configured/required status, and registry health status. Use a short health timeout and no retry loop for the health probe. Return HTTP 200 when the app is ready and either the registry is not required or the required registry health check succeeds; return HTTP 503 when the required registry is unavailable. Keep the endpoint independent of the LLM and dialogue database contents except for basic initialization.

- [ ] **Step 5: Make hosted startup explicit**

Keep local defaults unchanged, but ensure the CLI web command supports the Render command `forecast-elicitation web --host 0.0.0.0 --port $PORT --no-open`. Add focused coverage for host/port forwarding and confirm no browser is opened when `--no-open` is used.

- [ ] **Step 6: Run the focused and full tests**

Run: `pytest tests/unit/test_render_readiness.py tests/unit/test_web_interface.py tests/integration/test_cli.py -v`

Then run: `pytest -q`

Expected: all tests pass and existing persistent interview/UI behavior remains unchanged.

- [ ] **Step 7: Commit the application wiring**

Commit only CLI/web wiring and tests with message: `feat: make web service registry aware and render ready`.

### Task 4: Add Render configuration and deployment documentation

**Files:**
- Create: `render.yaml`
- Modify: `README.md`
- Create: `.env.example`

**Interfaces:**
- Consumes: the startup command and environment names from Tasks 1 and 3.
- Produces: reproducible Render configuration and operator instructions for connecting to the separately deployed registry service.

- [ ] **Step 1: Write the deployment documentation checklist**

Before editing, verify the README will document:

- Build command: `pip install .`
- Start command: `forecast-elicitation web --host 0.0.0.0 --port $PORT --no-open`
- Health path: `/healthz`
- `OPENAI_API_KEY` and `REGISTRY_API_URL` as secrets/configuration.
- Optional `REGISTRY_API_KEY`.
- `/var/data` values for `ELICITATION_DB_PATH`, `ELICITATION_LOG_PATH`, and `DATASET_STORE_PATH` when a persistent disk is attached.
- The separately deployed registry's HTTPS URL and required `/healthz` check.
- The limitation that multiple FYP instances require external shared state.

- [ ] **Step 2: Add `.env.example`**

Document safe local placeholders only; never include real credentials. Include local defaults and commented Render examples.

- [ ] **Step 3: Add `render.yaml`**

Define only the FYP web service. Use Python runtime, `pip install .`, the hosted start command, `/healthz`, and environment variables with secret values marked for dashboard entry. Do not define the separate registry service or its database in this file. Configure `/var/data` as the optional persistent-disk mount for the FYP's SQLite/log/object-store paths.

- [ ] **Step 4: Update README deployment instructions**

Explain manual deployment and Blueprint deployment, environment variable setup, persistent storage choice, registry connectivity test, and first-run verification. Include curl examples for the FYP `/healthz` and registry `/healthz` without exposing secrets.

- [ ] **Step 5: Validate configuration files**

Run: `python -c "import yaml; yaml.safe_load(open('render.yaml'))"` if PyYAML is available; otherwise validate the YAML structure with the repository's available tooling. Run: `python -m compileall src`.

- [ ] **Step 6: Commit deployment files and documentation**

Commit only `render.yaml`, `.env.example`, and README changes with message: `docs: document render deployment with remote registry`.

### Task 5: Final verification and handoff

**Files:**
- Modify only if verification identifies an issue in files from Tasks 1–4.
- Test: full existing test suite and focused registry/Render tests.

**Interfaces:**
- Consumes: all completed implementation tasks.
- Produces: verified local behavior, deployment checklist, and a concise list of changed files.

- [ ] **Step 1: Run formatting/static checks available in the project**

Run: `ruff check src tests` and `mypy src` when configured and available; report any pre-existing tool limitations separately from failures.

- [ ] **Step 2: Run the complete test suite**

Run: `pytest -q`

Expected: all tests pass without a live OpenAI key or registry.

- [ ] **Step 3: Perform a local registry contract smoke test with fakes**

Exercise the path `DatasetSearchQuery -> POST /resolve payload -> DatasetCandidate -> secure fetch metadata` using fake registry and download transports. Confirm pending/unverified entries are excluded and companion metadata is retained.

- [ ] **Step 4: Review the diff for scope and secrets**

Run: `git diff --check`, inspect `git diff`, and confirm no prompt files, API keys, registry database code, unrelated generated files, or existing user changes were altered.

- [ ] **Step 5: Provide deployment handoff**

Report the exact Render settings, environment variables, health-check URL, persistent-disk paths, registry URL requirement, local verification commands, test results, and any limitations that remain.
