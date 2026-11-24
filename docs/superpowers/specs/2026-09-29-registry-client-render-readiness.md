# Data Registry Client Integration and Render Readiness

## Status

Approved design; implementation pending execution plan.

## Goal

Make the forecasting FYP application production-ready for deployment on Render while integrating with the separately hosted Data Source Registry through its HTTP API. The FYP must resolve and fetch catalog data through the registry API without connecting directly to the registry database and without changing any LLM prompts or elicitation behavior.

## Scope

### In scope

- Add a registry HTTP client to the FYP application.
- Call the registry health endpoint before catalog resolution.
- Send confirmed forecasting requirements to `POST /resolve`.
- Convert verified registry target sources into the FYP's existing dataset-discovery model.
- Preserve companion-source, hierarchy, lineage, tag, score, freshness, and fetch-hint metadata.
- Fetch actual source data through the returned `endpoint_url` using the existing secure HTTP layer.
- Add bounded timeout, retry, response validation, and useful error reporting.
- Make registry configuration environment-driven.
- Add an application health endpoint suitable for Render health checks.
- Make application database, object-store, and log paths configurable for Render storage.
- Ensure the web process binds to Render's host and port.
- Add unit and integration-style tests using mocked registry responses.
- Document local and Render deployment configuration.

### Out of scope

- Direct database access to the registry.
- Changes to the separate `/Users/int_abd_5/Desktop/fyp_dataset` repository.
- Deployment or migration of the registry database.
- Changes to LLM prompts, prompt versions, slot definitions, or elicitation rules.
- Automatically treating companion relationships as causal claims.
- Replacing the existing local adapters when no registry URL is configured.

## Existing contract

The registry is a separately hosted FastAPI service. Its integration contract is documented in `docs/PIPELINE_INTEGRATION.md` in the registry repository.

The FYP will use these endpoints:

- `GET /healthz`: registry readiness check; both `status == "ok"` and `db_ok == true` are required.
- `POST /resolve`: resolve a confirmed forecasting request into `target_sources`, `companion_sources`, `lineage`, and `warnings`.
- `GET /sources/{slug}`: optional metadata refresh for a selected source when required.

The FYP must not invent source URLs or relations. It may fetch actual data only from endpoint URLs returned by the registry and accepted after validation.

## Architecture

```text
Confirmed ForecastingSpecification
              |
              v
     RegistryDatasetAdapter
              |
              v
       Registry HTTP Client
          |             |
       /healthz      /resolve
              |
              v
     DatasetCandidate objects
              |
              v
 Existing DatasetDiscoveryService
              |
              v
 Existing SecureHttpClient -> returned endpoint_url
              |
              v
 Existing validation, object store, and forecasting pipeline
```

The registry adapter is an additional source adapter. Existing local, upload, and public-source adapters remain available for local development and fallback when `REGISTRY_API_URL` is unset. In a Render deployment, registry use is required by configuration.

## Registry client

Add a small client dedicated to registry JSON calls rather than using the dataset-download path for POST requests. It should:

- Normalize and validate the configured base URL.
- Build `/healthz`, `/resolve`, and optional `/sources/{slug}` URLs without string concatenation bugs.
- Use a short connect/read timeout configured by environment.
- Retry transient connection, timeout, and 5xx failures with bounded exponential backoff.
- Never retry unchanged 4xx validation errors.
- Parse JSON responses and reject malformed response shapes with actionable errors.
- Optionally send a configured bearer/service token through an environment variable, without requiring authentication in local development.
- Avoid logging secrets or full authorization headers.

The existing secure download client remains responsible for fetching returned dataset URLs. Registry metadata calls and data downloads must remain separate so registry API behavior cannot bypass dataset URL security checks.

## Resolve request mapping

The adapter converts the existing `DatasetSearchQuery` into the registry request. It should prefer explicit confirmed fields and use the existing target-description/problem-statement fallback only when no canonical field is available.

The request should include:

- `prompt`: the confirmed user forecasting description.
- `target`: explicit canonical target when available.
- `fields`: explicit target fields when available.
- `domains`: known domain values.
- `geo`: confirmed geography.
- `frequency`: confirmed frequency when available.
- `min_relevance`: configurable, default `0.80`.
- `min_companion_strength`: configurable, default `0.60`.
- `max_dependency_depth`: configurable, default `2`.
- `max_sources`: configurable, default `12`.
- `include_pending`: `false` by default and forced false for production.

The adapter should avoid sending speculative values that were not confirmed by the user. Empty optional values should be omitted rather than serialized as misleading strings.

## Source mapping

For each registry `target_sources` entry:

- Use the registry `slug` as the stable candidate identity.
- Map `name`, description, provider, endpoint URL, endpoint type, status, health, frequency, timestamps, tags, fields, geography, license, and scores into the existing `DatasetCandidate` fields or metadata.
- Keep the complete registry item, excluding secrets if any, under namespaced metadata for downstream lineage and auditability.
- Accept only `status == "verified"`.
- Prefer `health == "ok"`.
- Permit `health == "unknown"` only when the normal fetch and downstream validation succeed.
- Reject missing or non-HTTP(S) endpoint URLs.

For each `companion_sources` entry:

- Preserve it as companion metadata associated with the target candidate or source plan.
- Preserve `field`, `relation_type`, `matched_via`, `dependency_score`, `prior_strength`, `evidence_type`, `depth`, and `note`.
- Do not represent a companion as a target dataset solely because it is related.
- Do not interpret `driver_of`, `correlates_with`, or dependency scores as proof of causality.

The resulting candidate must remain compatible with the current `DatasetDiscoveryService`, `DatasetRanker`, `fetch_selection`, and object-store flow. No new source role is required for the first integration; companion data is metadata for later feature assembly unless the existing pipeline explicitly selects it.

## Fetch behavior

When a registry candidate is selected:

1. Re-check its stored registry status and endpoint URL.
2. Fetch the returned endpoint through `SecureHttpClient`.
3. Apply the existing content-size, redirect, public-host, HTTPS, and executable-content protections.
4. Parse or store the response using the existing adapter/object-store flow.
5. Preserve registry slug, provider, endpoint type, tags, scores, timestamps, fetch hint, lineage, and warnings in the dataset version metadata.
6. Let existing schema/time/geography/unit/missing-value validation decide whether the result is usable.

Registry metadata must not cause the FYP to bypass existing download security or data validation.

## Configuration

Add environment-backed settings with safe local defaults:

- `REGISTRY_API_URL`: empty by default; when empty, local adapters continue to work.
- `REGISTRY_API_KEY`: optional service credential; never print it.
- `REGISTRY_TIMEOUT_SECONDS`: bounded default suitable for interactive use.
- `REGISTRY_MAX_RETRIES`: small bounded retry count.
- `REGISTRY_MIN_RELEVANCE`: default `0.80`.
- `REGISTRY_MIN_COMPANION_STRENGTH`: default `0.60`.
- `REGISTRY_MAX_DEPENDENCY_DEPTH`: default `2`.
- `REGISTRY_MAX_SOURCES`: default `12`.
- `REGISTRY_INCLUDE_PENDING`: default `false`; production must remain false.
- `REGISTRY_REQUIRED`: default false for local development; true on Render.

Existing application settings remain environment-driven:

- `ELICITATION_DB_PATH`
- `ELICITATION_LOG_PATH`
- `DATASET_STORE_PATH`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

No secret values are committed to the repository.

## Failure behavior

- If the registry is not configured locally, continue using existing local adapters.
- If the registry is required and health fails, return a clear dependency-unavailable response and do not silently invent catalog data.
- If `/resolve` returns no verified target sources, report that no matching catalog source was found and preserve warnings for the UI/log.
- If a source is pending, retired, missing an endpoint URL, or not verified, skip it.
- If a returned endpoint fetch fails, record the source-specific failure and allow existing discovery fallback behavior where configured.
- If all configured registry candidates fail, return a user-readable catalog-unavailable result rather than a generic exception.
- Do not expose upstream response bodies, API keys, or internal stack traces in user-facing responses.

## Render readiness

The FYP web service must:

- Bind to `0.0.0.0`.
- Read the port from `$PORT`.
- Disable browser auto-open in hosted mode.
- Expose a fast `/healthz` endpoint.
- Keep file paths configurable so a Render persistent disk can be mounted, for example under `/var/data`.
- Use `/var/data` paths for SQLite state, logs, and dataset artifacts if the service is deployed with local persistent storage.
- Document that multiple instances require moving shared state to an external database/object store.

The Render deployment instructions will be for this FYP service only. The separate registry deployment will be referenced by its public `REGISTRY_API_URL`, not managed by this repository.

## Testing

Add tests for:

- Configuration defaults and environment overrides.
- Correct `/resolve` payload construction from a confirmed specification.
- Omission of unconfirmed optional fields.
- Health success and health failure.
- Retry on timeout/5xx and no retry on 4xx.
- Malformed registry response handling.
- Filtering of unverified, pending, retired, and URL-less sources.
- Mapping of target and companion metadata.
- Fetching through the existing secure HTTP client.
- Required-registry failure behavior.
- Web `/healthz` response and Render host/port startup configuration.
- Regression coverage for existing local adapters and unchanged elicitation prompts.

## Documentation deliverables

Update the FYP README with:

- Local setup with and without a registry.
- Required environment variables.
- Example local registry configuration.
- Render build/start commands.
- Render health-check path.
- Persistent-disk path configuration.
- How to set `REGISTRY_API_URL` to the separately deployed registry service.
- Operational checks for registry health and source resolution.

## Acceptance criteria

- The FYP can resolve a confirmed request through a separately hosted registry API.
- It never connects directly to the registry database.
- It never uses pending or unverified registry sources in production mode.
- It fetches returned data through the existing secure downloader.
- Registry failures produce controlled, diagnosable behavior.
- Existing prompts and elicitation behavior are unchanged.
- The service starts on Render using `0.0.0.0` and `$PORT`.
- The service exposes a working health endpoint.
- Tests pass without requiring a live registry or OpenAI key.
