# Project Decisions

This file records the reasoning behind important project and implementation decisions. It is intentionally different from a changelog: a changelog says what changed, while this file explains why the system is shaped this way and what trade-offs were accepted.

**Project:** Automated Tabular Time-Series Forecasting
**Repository:** `forecasting-requirement-elicitation`
**Baseline documented:** 2026-11-18
**Current implementation scope:** requirement elicitation, explicit confirmation, dataset discovery, dataset ranking, safe dataset fetching, and dataset handoff. Model training and forecast generation are not implemented in this repository yet.

## How to maintain this file

Update this file in the same iteration as every material change. Add a new decision record when a change introduces a new policy, boundary, dependency, data contract, or user-visible behavior. Update an existing record when the implementation changes but the underlying rationale remains the same.

Every new record should answer:

1. What problem or evidence led to the decision?
2. What alternatives were considered?
3. Why was this option selected?
4. What are the consequences and trade-offs?
5. Which files or components are affected?
6. What evidence would cause us to revisit it?

The runtime pipeline also records operational reasons separately. For interview turns, `state.next_slot` records the selected slot and reason; for catalog results, ranking records the score breakdown, limitations, and rejection reasons. Those runtime records explain an individual execution, while the records below explain the stable design choice.

## Decision index

| ID | Decision | Status | Main reason |
| --- | --- | --- | --- |
| D-001 | Use a hybrid LLM plus deterministic pipeline | Accepted | Natural-language flexibility is useful, but requirements and safety rules must remain predictable. |
| D-002 | Make the schema and SQLite state authoritative | Accepted | A persistent, inspectable state prevents the provider from silently redefining the interview. |
| D-003 | Require evidence-bound extraction | Accepted | The system must not store a value that cannot be tied to the user’s current message. |
| D-004 | Keep provider context persistent only in the persistent pilot | Accepted | Previous conversational context helps the LLM avoid repetition, but provider context must not replace application state. |
| D-005 | Stop the first interview at an intermediate useful brief | Accepted | A novice should not be forced through every advanced modelling choice before a dataset can be found. |
| D-006 | Defer catalog-specific questions until a dataset is selected | Accepted | The catalog, not the novice, should provide columns, frequency, provider, and schema facts. |
| D-007 | Validate generated questions and fall back deterministically | Accepted | A malformed or over-broad question must not block the interview or cause a repeated loop. |
| D-008 | Require explicit confirmation before handoff | Accepted | Dataset discovery and downstream work should use a user-approved specification, not an unreviewed inference. |
| D-009 | Treat the hosted registry as an API boundary | Accepted | The FYP service needs verified metadata without coupling itself directly to the registry database. |
| D-010 | Rank and reject catalog candidates deterministically | Accepted | Relevance alone is not enough; provenance, rights, temporal fit, quality, and access must also be considered. |
| D-011 | Validate and content-address fetched data | Accepted | A selected endpoint may return unsafe, malformed, or non-dataset content; immutable hashes make reuse auditable. |
| D-012 | Keep observability redacted and append-only | Accepted | Debugging needs the request/response path, but secrets must never be exposed in logs or state. |
| D-013 | Share the same application engine between CLI and web | Accepted | Fixes to elicitation and state behavior should apply consistently to both interfaces. |
| D-014 | Keep forecasting-model training outside the current repository boundary | Accepted for current milestone | The current milestone proves the requirements-to-dataset handoff before adding model-training complexity. |
| D-015 | Deploy the FYP service separately from the registry service | Accepted | The FYP can be hosted and scaled independently while using the registry’s public HTTPS API. |
| D-016 | Use sequential live workflow scenarios as an acceptance check | Accepted | Synthetic conversations expose real provider latency, repetition, state drift, catalog-query quality, and fetch behavior together. |
| D-017 | Let explicit pending answers and first-turn time cues override provider formatting errors | Accepted in pilot | The provider repeatedly returned malformed numeric durations or conflicting slot values even when the user’s answer was clear. |
| D-018 | Use a clean square SDG 9 asset in the report | Superseded by D-019 | The old crop included part of SDG 8 and became blurred when enlarged. |
| D-019 | Use the full SDG grid with relevant alignment in the caption | Superseded by D-024 | The user first selected the full grid; the newer formatting checklist says to show only relevant SDGs. |
| D-020 | Provide a code-grounded dataset/dependency context JSON | Accepted | The LLM needs precise meanings for variable ranges, companion thresholds, graph depth, and current API behavior. |
| D-021 | Build Deliverable III from the committee LaTeX class and recorded FYP-I evidence | Accepted | The report must show what the prototype shares, what the experiments measured, and which work remains for FYP-II. |
| D-022 | Use the committee's LaTeX source layout for Deliverable III | Accepted | The report must use the supplied `main.tex` structure and original class. |
| D-023 | Match the declaration layout in the earlier LaTeX report | Superseded by D-026 | The reference layout is retained, with a completed date and author signature fields. |
| D-024 | Show only the SDGs relevant to this project | Accepted | The formatting review requests relevant SDG figures rather than the complete 17-goal grid. |
| D-025 | Apply the report checklist while preserving the committee template | Accepted | Correct content structure and typography without replacing the university's class or recorded FYP-I evidence. |
| D-026 | Date declaration pages and leave real signature fields for the authors | Accepted | The checklist requires a dated declaration and signatures; the report must not fabricate signatures. |

## Decision records

### D-001 — Hybrid LLM plus deterministic pipeline

**Status:** Accepted
**Decision:** Use the LLM for natural-language extraction, plain-language clarification, and one-question wording. Use Python for schema ownership, state transitions, normalization, validation, question priority, readiness, confirmation, dataset ranking, and fetching.

**Context:** A completely free-form interviewer was prone to hallucinating slot values, repeating questions, and treating a user’s conversational answer as a different requirement. A completely rule-based interviewer would be predictable but poor at understanding phrases such as “your data list,” “the next five years,” or a user asking what a question means.

**Options considered:**

- Let the LLM own the full dialogue state and decide what is valid.
- Use only fixed questions and exact answer matching.
- Use the LLM for interpretation while deterministic code applies and checks its proposal.

**Why this option:** It preserves the useful language ability of the LLM without allowing an untrusted response to rewrite the application state. The design also matches the project’s research basis: adaptive requirements elicitation is combined with schema-guided state tracking.

**Consequences:** The codebase has more layers and contracts, but each layer has a clear responsibility. The LLM can still be wrong; the state reducer and validation layer must therefore remain the final authority.

**Affected areas:** `application/orchestrator.py`, `application/state_reducer.py`, `application/clarification.py`, `domain/schema.py`, `infrastructure/llm/`, and `prompts/`.

**Revisit when:** Evaluation shows that the deterministic contract is rejecting too many valid user answers, or when the project adds a new interaction mode that needs a different state authority.

### D-002 — Schema and SQLite state are authoritative

**Status:** Accepted
**Decision:** Store slot values, statuses, evidence, turns, dataset columns, confirmation state, schema version, and provider conversation ID in `DialogueState`; persist it through `SQLiteDialogueRepository`. The provider’s context is supporting context only.

**Why this option:** The state must survive a process restart, be inspectable during debugging, and remain stable even if the provider loses context or returns a different interpretation. Explicit statuses such as `provided`, `inferred`, `ambiguous`, `invalid`, `conflicting`, and `confirmed` make uncertainty visible instead of hiding it in prose.

**Trade-off:** SQLite and Pydantic state create a local persistence dependency and require schema evolution discipline. That cost is justified for the current single-service FYP deployment. A later multi-instance deployment should move shared state to a managed database.

**Affected areas:** `domain/models.py`, `domain/schema.py`, `infrastructure/persistence/sqlite_repository.py`, and `application/orchestrator.py`.

### D-003 — Evidence-bound extraction

**Status:** Accepted
**Decision:** Every extracted slot update must include evidence that is a case-insensitive substring of the current user message, or a supported canonical form of that evidence. If every update in an extraction violates that contract, the state reducer raises `UnsupportedEvidenceError`; the orchestrator then attempts deterministic recovery for the slot it had asked about.

**Why this option:** It prevents the model from turning its own assumptions, an earlier assistant question, or an invented paraphrase into a user fact. It also explains why an extraction can appear correct in a provider response but still be rejected by application code: correctness of the value is not enough; the evidence must be attributable to the current turn.

**Trade-off:** Valid natural-language paraphrases can be rejected if the evidence cannot be mapped to the current message. The recovery path and normalization rules reduce that friction without removing the safety boundary.

**Affected areas:** `application/state_reducer.py`, `application/orchestrator.py`, `prompts/extractor.py`, and `tests/integration/test_elicitation_flow.py`.

### D-004 — Persistent provider context is a pilot, not the source of truth

**Status:** Accepted
**Decision:** `PersistentOpenAIResponsesClient` creates one provider conversation per dialogue and reuses it for extraction, question generation, and follow-up explanation calls. The normal client remains provider-stateless. SQLite still owns the actual state.

**Why this option:** The repeated-question problem showed that the model benefits from seeing prior conversation context. Persistent context lets the provider remember previous questions and answers, while the application can still enforce the selected slot, evidence contract, and readiness rules.

**Trade-offs:** Provider-side conversation retention introduces privacy and lifecycle considerations. It also cannot by itself solve state corruption: the model may remember a prior answer but still return an invalid extraction. The pilot therefore keeps `provider_conversation_id` as context metadata rather than treating the conversation as authoritative.

**Affected areas:** `infrastructure/llm/openai_responses.py`, `domain/models.py`, `application/orchestrator.py`, and `interfaces/cli.py` / `interfaces/web.py`.

**Revisit when:** Persistent context materially increases latency, creates unacceptable retention risk, or a later provider supports an equivalent short-lived session mechanism with the same quality.

### D-005 — Intermediate useful brief

**Status:** Accepted
**Decision:** The first interview prioritizes a bounded set of high-impact requirements: forecast intent, target, source mode, horizon, output grouping, target unit, and the minimum information needed for a useful brief. Advanced choices remain deferred rather than forcing a long interview.

**Why this option:** The system is for novice users. Asking about every quality policy, covariate, calendar, deployment mode, and model choice before finding data creates fatigue and encourages arbitrary answers. The intermediate boundary is sufficient to confirm the user’s goal and begin dataset discovery.

**How the AI chooses:** `rank_priority_slots()` combines slot status, schema priority, ontology relevance, requiredness, and validation issues. `select_next_slot()` gives source selection and unresolved intermediate-core requirements precedence. The provider receives the ranked slots so its wording follows the same priority.

**Trade-off:** Some advanced requirements are not collected before confirmation. They are preserved as deferred slot IDs in `ForecastingSpecification` so later pipeline stages can resume the process with the right context.

**Affected areas:** `application/clarification.py`, `application/interview_ontology.py`, `prompts/llmrei_long.py`, `domain/schema.py`, and `domain/models.py`.

### D-006 — Catalog facts are deferred until dataset selection

**Status:** Accepted
**Decision:** When `source_mode == "catalog"` and no catalog dataset schema has been attached, the interview does not ask the user for a file name, internal asset ID, target column, time column, frequency, provider, or privacy facts that the catalog should supply.

**Why this option:** A user who says “use your data catalog” has selected a source strategy, not a specific file. Asking for columns or an identifier at that point contradicts the intended pipeline. After a catalog item is selected and its columns are available through `set_dataset_columns()`, the deferred dataset questions can become active.

**Trade-off:** Dataset-specific clarification happens later, after recommendations and selection. That is intentional: the catalog can answer those questions more accurately than a novice can.

**Affected areas:** `application/clarification.py`, `application/orchestrator.py`, `domain/conditions.py`, `interfaces/web.py`, `application/dataset_query.py`, and registry integration.

### D-007 — Generated questions are bounded and have a deterministic fallback

**Status:** Accepted
**Decision:** The provider receives one selected slot and must return one bounded question with an example answer. The question is validated; invalid output is retried once, then the schema’s static question is used.

**Why this option:** The LLMREI-style interaction should feel conversational, but a provider response must not introduce multiple questions, fill a different slot, or use overly technical language. A fallback guarantees progress when the API fails or produces an invalid response.

**Trade-off:** The fallback wording is less adaptive than the LLM. The system favors a clear, safe question over a more creative but unreliable response.

**Affected areas:** `prompts/llmrei_long.py`, `application/orchestrator.py`, `domain/models.py`, and `tests/unit/test_question_policy.py`.

### D-008 — Explicit confirmation gates the handoff

**Status:** Accepted
**Decision:** A ready brief is summarized in plain language and requires explicit confirmation before producing `ForecastingSpecification`. Dataset discovery follows this confirmation, and a selected dataset requires a second explicit confirmation before fetching.

**Why this option:** Forecasting choices can have operational and governance consequences. A confirmation step gives the user a chance to correct a target, geography, horizon, source, or output interpretation before data is selected or downloaded.

**Trade-off:** The interaction has an extra turn, but it prevents silent handoff based on inferred values and makes the boundary between elicitation and data acquisition auditable.

**Affected areas:** `application/orchestrator.py`, `interfaces/cli.py`, `interfaces/web.py`, `application/dataset_discovery.py`, and `domain/models.py`.

### D-009 — Hosted registry is an API boundary

**Status:** Accepted
**Decision:** The FYP service calls the separately hosted registry through `RegistryClient` rather than connecting directly to the registry database. It uses `/healthz`, `/resolve`, and returned source metadata/endpoints.

**Why this option:** The registry pipeline and its database have a separate deployment lifecycle. An HTTP boundary keeps database credentials and schema details out of the FYP service, allows the registry to update independently, and gives the FYP a clear health check and failure behavior.

**Trade-off:** Discovery depends on network availability and a compatible registry API contract. `REGISTRY_REQUIRED=true` intentionally fails health and discovery rather than silently falling back to unrelated sources.

**Affected areas:** `infrastructure/datasets/registry_client.py`, `infrastructure/datasets/registry_adapter.py`, `infrastructure/datasets/registry.py`, `config.py`, `interfaces/web.py`, and `render.yaml`.

### D-010 — Deterministic eligibility and ranking

**Status:** Accepted
**Decision:** Catalog candidates are scored and filtered by deterministic rules covering semantic fit, authority/provenance, temporal fit, quality, license/reproducibility, freshness, and access cost. Ineligible candidates are kept as unavailable alternatives with reasons; only eligible candidates become recommendations.

**Why this option:** The best textual match is not necessarily safe or usable. A source can have excellent semantic similarity but unverified rights, weak provenance, too few observations, incompatible geography, or an unsafe acquisition path.

**Trade-off:** A strict ranker can return no recommendations when metadata is incomplete. That is a deliberate fail-closed behavior; the user can adjust the request or upload data instead of receiving an unjustified source.

**Affected areas:** `application/dataset_ranking.py`, `application/dataset_discovery.py`, `domain/datasets.py`, and source adapters.

### D-011 — Validate and content-address fetched data

**Status:** Accepted
**Decision:** After explicit selection, the adapter fetches the payload; the service rejects executable or unsafe archive content, validates the dataset payload, stores it under a SHA-256 content address, and persists an immutable `DatasetVersion` with source, license, quality, and lineage metadata.

**Why this option:** A trusted catalog record does not guarantee that an endpoint still returns the expected payload. Validation protects the pipeline from HTML error pages, malformed JSON/CSV, executable content, archive traversal, and insufficient training points. Hashing makes identical content reusable and auditable.

**Trade-off:** Some valid but unusual formats need adapter-specific validation and may be rejected until support is added. Shared data can use a shared namespace; private or non-redistributable data requires a user-scoped namespace.

**Affected areas:** `application/dataset_discovery.py`, `application/dataset_validation.py`, `infrastructure/datasets/http.py`, `infrastructure/datasets/object_store.py`, and dataset repositories.

### D-012 — Redacted, append-only observability

**Status:** Accepted
**Decision:** The pipeline writes sanitized trace events to JSONL and state/business events to SQLite. The trace includes API request features, structured responses, extraction application/recovery, validation, selected slots, question output, catalog query/ranking, and errors. API keys and credential values are redacted.

**Why this option:** The project needs to explain what was sent to the model, what came back, how state changed, and why a question or dataset was chosen. Without that path, repeated questions and rejected evidence are difficult to diagnose.

**Trade-off:** User messages may contain sensitive business data even after credentials are removed; the log remains sensitive and must be protected. The persistent terminal/web experience hides diagnostic traces from the end user, while developers can inspect the log when debugging.

**Affected areas:** `infrastructure/observability/pipeline_logger.py`, `prompts/extractor.py`, `application/orchestrator.py`, `infrastructure/persistence/sqlite_repository.py`, and CLI/web interfaces.

### D-013 — One application engine for CLI and web

**Status:** Accepted
**Decision:** CLI and web are interface adapters around the same `ElicitationEngine`, schema, repository, provider abstractions, and dataset discovery service.

**Why this option:** The earlier problems occurred in conversation behavior, not just in a particular UI. Sharing the engine means evidence recovery, catalog deferral, confirmation, and readiness behave the same in terminal and browser sessions.

**Trade-off:** The web server must translate HTTP requests and uploaded files into the same domain operations, and it currently uses a lightweight standard-library server rather than a full web framework.

**Affected areas:** `interfaces/cli.py`, `interfaces/web.py`, `application/orchestrator.py`, and `pyproject.toml`.

### D-014 — Current repository ends at dataset handoff

**Status:** Accepted for the current milestone
**Decision:** Do not add forecasting-model training to the current elicitation/catalog implementation. The confirmed specification and validated dataset version are the handoff contract for the next milestone.

**Why this option:** The FYP’s complete vision includes automated model selection, hierarchical forecasting, evaluation, artifacts, and an inference API, but mixing all of those into the current debugging target would make the requirement-to-data path harder to verify. The current repository proves the foundation first.

**Trade-off:** A user can reach “dataset ready” but not yet train and export a final forecasting model through this repository. The future model stage should consume `ForecastingSpecification` and `DatasetVersion` rather than bypassing them.

### D-015 — Separate Render deployments

**Status:** Accepted
**Decision:** Deploy the FYP web service separately from the registry service. The FYP receives the registry’s HTTPS URL and optional API key through environment variables.

**Why this option:** The user cannot rely on a paid Render database/Blueprint arrangement for both systems. Separate services match the actual ownership boundary and allow the registry pipeline to be maintained independently.

**Trade-off:** Both services must be healthy and their API contract must remain compatible. The FYP’s `/healthz` reports registry availability, and the Render configuration can fail closed when the registry is required.

**Affected areas:** `render.yaml`, `config.py`, `interfaces/web.py`, `infrastructure/datasets/registry_client.py`, and `README.md`.

### D-016 — Sequential live workflow scenarios

**Status:** Accepted
**Decision:** Keep a small, realistic live scenario set in `evaluation/live_workflow_scenarios.json` and run it sequentially through `scripts/run_live_workflows.py`. Each scenario uses a temporary SQLite/object-store workspace, persistent provider context for that dialogue, explicit confirmation, catalog discovery, top-candidate selection, and a fetch attempt.

**Why this option:** Unit and fake-client tests verify contracts, but they cannot show whether the real provider repeats a question, takes too long, loses a slot, builds a poor registry query, or reaches dataset fetching. Sequential execution preserves the conversational order and makes per-scenario latency visible.

**Trade-offs:** Live runs consume API time/cost and are nondeterministic. A bounded turn limit is intentional: reaching the limit is recorded as a workflow failure because a novice user should not need an unbounded number of repetitions. The runner uses only a synthetic user scope and never prints the API key.

**Affected areas:** `evaluation/live_workflow_scenarios.json`, `scripts/run_live_workflows.py`, and `evaluation/live_workflow_results.json`.

**Latest baseline result (2026-10-20):** Six scenarios were run sequentially with persistent provider context. One reached confirmation, catalog recommendation, selection, and validated fetch. Five hit the eight-turn cap before confirmation. The primary recurring failure was a horizon such as “5 years” being repeatedly treated as an invalid numeric value. One successful GDP path also produced a malformed target/prompt string and omitted frequency from the registry query, so successful fetch does not yet mean the query quality is correct.

### D-017 — Deterministic ownership of explicit answers

**Status:** Accepted in pilot; not merged to `main`
**Decision:** When the application has selected a pending slot and the user’s current answer can be normalized and validated for that slot, that answer replaces a conflicting provider proposal for the same slot. On the first user message only, unambiguous time phrases such as `annually` and `next 5 years` may fill unmentioned frequency and horizon slots. Provider context and prompts remain unchanged.

**Context:** The live baseline repeated `5 years` and `30 days` because the provider returned numeric values that failed duration validation. The provider could also return an update for the pending slot that disagreed with the user’s answer. Separately, a clear first message could leave frequency absent from the registry query when the provider omitted it.

**Options considered:**

- Continue trusting the provider’s candidate whenever it mentions the same slot.
- Replace the provider with a fully rule-based interview.
- Keep the provider for interpretation while making the application’s validated pending-slot answer authoritative.

**Why this option:** It fixes the observed boundary error without changing the LLMREI prompts or removing natural-language interpretation. It also preserves other valid provider updates from the same turn.

**Consequences:** The state layer becomes more predictable and the interview needs fewer repeated turns. The temporal inference is intentionally narrow and limited to the first message; it must not become a general-purpose natural-language parser. The pilot still does not infer every possible geography or domain fact deterministically.

**Affected areas:** `application/orchestrator.py`, `application/state_reducer.py`, `application/normalization.py`, `application/dataset_query.py`, and the live evaluation artifacts.

**Evidence:** Automated tests increased from 258 to 263 with all passing. The final live pilot completed 5/6 scenarios versus 1/6 baseline, removed repeated answer loops in all six scenarios, reduced average turns from 7.50 to 5.50, and produced valid frequency values for four scenarios where the provider had previously omitted them. One WHO fetch returned HTTP 502 and the uploaded-file scenario still exceeded the eight-turn cap; these are follow-up issues, not reasons to discard the state fixes.

**Revisit when:** The pilot causes incorrect slot overwrites, temporal phrases are misclassified in real user data, or the remaining upload/catalog matching failures show that the current intermediate schema is still too large.

### D-018 — Clean square SDG 9 asset in the report

**Status:** Superseded by D-019
**Iteration:** 2026-11-10
**Decision:** Use a separate, high-resolution square Goal 9 icon and render it at 0.40 of the text width. Keep the supplied committee class, chapter figure counter, and figure caption unchanged.

**Context:** Visual inspection of report page 7 showed a maroon strip from SDG 8 at the left edge and a blurred icon. The LaTeX source used a 98 x 96 pixel crop from the report's multi-goal contact sheet, then enlarged it to 0.75 of the text width.

**Options considered:**

- Adjust the crop coordinates within the low-resolution contact sheet.
- Redraw the icon manually.
- Use a standalone square high-resolution Goal 9 icon.

**Why this option:** The standalone tile removes neighboring goals, preserves the established SDG artwork and colors, and remains sharp at report size.

**Consequences:** Figure 2.1 occupies less vertical space and is now a square tile. Page 2 remains blank because the supplied template explicitly creates it; it is not required by LaTeX's one-sided book layout. The Author's Declaration remains at the class's normal 11 pt body size; its short single-sentence text and large unused page area make it appear small, but no `\small` setting is applied.

**Affected areas:** `tmp/build_f26_native_latex.py`, `output/latex/F26-012-native/Figures/sdg9.png`, `output/latex/F26-012-native/main.tex`, and the compiled report PDF.

**Revisit when:** The evaluator or supervisor asks to remove the template's intentionally inserted blank page or specifies a different declaration layout or font size.

### D-019 — Full SDG grid with relevant alignment in the caption

**Status:** Superseded by D-024
**Iteration:** 2026-11-10
**Decision:** Use the complete 17-goal grid supplied in the user's reference image. Caption it as the Sustainable Development Goals and identify SDG 9 and SDG 8 as the project's closest areas of alignment. Keep the chapter-wise label Figure 2.1.

**Context:** The user clarified that the intended page 7 illustration was the full SDG grid with a caption naming Goals 9 and 8. This supersedes the earlier single-icon choice. The evaluator's earlier instruction had asked for only relevant SDG icons; the current user request explicitly selects the complete grid shown in the supplied reference image.

**Options considered:**

- Keep the standalone SDG 9 tile.
- Use only separate icons for Goals 8 and 9.
- Reinsert the full grid and state the relevant alignment in the caption.

**Why this option:** It matches the exact figure the user supplied as the desired reference and preserves the context of the SDG section while the caption makes the project's relevance explicit.

**Consequences:** The image is wider than the previous single tile and the caption is longer. It is cropped from the supplied reference image without its baked-in caption; LaTeX adds the chapter-wise figure number and selectable caption text. This differs from the evaluator's earlier request to omit non-relevant SDG tiles.

D-019 supersedes D-018's figure-asset choice only; D-018's notes about the blank template page and declaration layout remain applicable.

**Affected areas:** `tmp/build_f26_native_latex.py`, `tmp/sdg_all_goals.png`, `output/latex/F26-012-native/Figures/sdg_all_goals.png`, `output/latex/F26-012-native/main.tex`, and the compiled report PDF.

**Revisit when:** The supervisor or evaluator changes the SDG figure requirement.

### D-020 — Code-grounded dataset/dependency context JSON

**Status:** Accepted
**Iteration:** 2026-11-17
**Decision:** Provide a standalone JSON context file for LLM use. Define dataset sources, target and companion variables, relationship metadata, min/max variable bounds, dependency thresholds, request/response shape, and implementation limitations based on the current repository.

**Context:** The user needs to provide an LLM with context about catalog datasets, variable min/max values, and dependency/correlation behavior. Similar field names can be confused: `min_companion_strength` is a registry relationship threshold, while `observed_min` is a data value statistic; `max_dependency_depth` limits graph traversal, not a variable's numeric maximum.

**Options considered:**

- Provide a short glossary only.
- Describe the intended registry API without checking current code.
- Create a structured JSON context that separates implemented behavior from design notes and unknown registry semantics.

**Why this option:** A reusable JSON document is easy to attach as LLM context and reduces the chance that the model presents planned fields as implemented or treats correlations as causation.

**Consequences:** This file documents behavior; it does not alter runtime prompts or API payloads. The context explicitly notes that the current adapter does not send `fields` or `domains` and does not calculate per-variable observed min/max values during resolve.

**Affected areas:** `docs/dataset_variable_dependency_context.json`, `src/forecasting_assistant/domain/datasets.py`, `src/forecasting_assistant/application/dataset_query.py`, `src/forecasting_assistant/infrastructure/datasets/registry_adapter.py`, and `src/forecasting_assistant/config.py`.

**Revisit when:** The registry's published schema or implementation changes, especially the definition of dependency scores, depth, source caps, or variable-level statistics.

### D-021 — Deliverable III report and FYP-I evidence

**Status** Accepted on 2026-11-17.

**Decision** Keep the university's FastFyp class and IEEE bibliography style, add Chapters 7, 9, and 10, and reserve the Chapter 8 number for the FYP-II User Manual. Carry forward the existing report content and the requested SDG figure.

**Reason** The committee's chapter numbers make the report easier to compare with the deliverable instructions. The experiment records distinguish confirmation, recommendation, and validated fetch. The source review also shows that uploaded column names and references can enter the provider context and that clarification text bypasses the outbound credential filter.

**Consequences** The report uses the recorded baseline and pilot runs and presents the local feature extractor and its approval flow as FYP-II work. The XeTeX build uses the template's pdfLaTeX font encoding so the Times face is embedded. The previous report remains available as a separate artifact.

**Revisit when** FYP-II adds the User Manual, changes provider data handling, or produces forecasting results.

### D-022 — Use the committee's LaTeX source layout for Deliverable III

**Status** Accepted on 2026-11-17.

**Decision** Base the revised report on the supplied `main.tex` and include all report chapters in that file. Use the original `FastFyp.cls`, cover and declaration blocks, chapter and section styles, table structures, figure assets supplied by the template, and `fypbib.bib` with the `ieeetr` stylesheet.

**Reason** The committee's format includes decisions made in `main.tex` about the front matter, section hierarchy, use cases, tests, and references. Loading the class alone leaves those choices to the report author.

**Consequences** The template's blank page follows the cover. Chapter 8 is reserved for the User Manual, so the FYP-I report goes from Chapter 7 to Chapter 9. A continued table presents all sixteen literature entries. The source archive and compiled PDF sit in separate locations for editing and submission.

**Revisit when** The committee issues a revised template or FYP-II adds the User Manual.

### D-023 — Match the declaration layout in the earlier LaTeX report

**Status** Superseded by D-026 on 2026-11-18.

**Decision** Match the declaration pages in `output/final_submission/F26-012-latex.pdf`. Use regular Latin Modern text and headings, the same anti-plagiarism wording, left-aligned names, and 7 cm signature rules. D-026 later adds the report date and author signature fields.

**Reason** The previous correction changed the positions of the declarations and signature rules, but retained the template's bold headings, Times-like font, and longer wording. The reference report uses regular headings and Latin Modern text throughout both declaration pages.

**Consequences** Both declarations have separate pages and retain the reference typography and spacing. Signature fields remain blank until the authors sign.

### D-024 — Show only the SDGs relevant to this project

**Status:** Accepted on 2026-11-18.

**Decision:** Replace the full 17-goal grid with an original, text-based figure showing SDG 8 and SDG 9. Cite the United Nations' goal descriptions and state that the alignment is the authors' interpretation. Do not reproduce the UN icon artwork in the report.

**Context:** The formatting checklist says to include only SDGs relevant to the FYP. The earlier D-019 selected the complete grid after the user supplied a reference picture, but this current checklist supersedes that figure choice. The report is a written publication, so an original diagram avoids implying endorsement or reproducing official icon artwork.

**Options considered:**

- Keep all 17 icons from the supplied picture.
- Use official SDG 8 and SDG 9 icons.
- Create a small original diagram naming only the two relevant goals and explaining the project connection.

**Why this option:** It follows the evaluator's instruction, makes the project's contribution clear, and does not rely on an altered or low-resolution goal grid.

**Consequences:** Figure 2.1 is a pair of labelled panels for SDG 8 and SDG 9. The caption is short enough for the List of Figures. A note explains that the alignment is the authors' interpretation and does not imply UN endorsement.

**Affected areas:** `tmp/pdfs/f26-deliverable-iii-template/build_report.py`, `output/latex/F26-012-deliverable-iii-template/main.tex`, `output/latex/F26-012-deliverable-iii-template/fypbib.bib`, and the final PDF.

**Revisit when:** The supervisor requests an official SDG icon or supplies permission and a preferred asset.

### D-025 — Apply the report checklist within the committee template

**Status:** Accepted on 2026-11-18.

**Decision:** Retain `FastFyp.cls`, its cover and page layout, chapter-wise figure/table numbering, and IEEE bibliography. Rewrite the scope as three plain paragraphs, explain requirement groups before presenting their bullet list, remove the API JSON code sample, define technical terms once, use Title Case headings, and preserve explicit chapter conclusions.

**Context:** The attached formatting checklist calls for clear paragraphs, readable figures, correctly captioned tables, title-case headings, chapter introductions and conclusions, and removal of template text. The user had also asked that Scope not contain nested headings and that the report cover the whole project rather than implementation files.

**Why this option:** It corrects the presentation issues while keeping the required university format and balancing implementation detail with the project's wider research scope.

**Consequences:** The functional requirements are now a numbered-ID bullet list with actors and observable acceptance conditions. The report contains 80 pages including front matter and references. Chapter 8 remains reserved for the FYP-II User Manual, so Chapters 7, 9, and 10 retain their required numbers.

**Affected areas:** `tmp/pdfs/f26-deliverable-iii-template/build_report.py`, the generated report source, and the final PDF.

**Revisit when:** The committee provides revised formatting rules or requests a different level of implementation detail.

### D-026 — Date author declarations and keep authentic signature fields

**Status:** Accepted on 2026-11-18.

**Decision:** Date both declaration pages 18 November 2026 and print the authors' names and roll numbers beside blank signature rules. Do not create or imitate signatures.

**Context:** The attached checklist asks for a date and signatures on the authors' declaration. The report can supply the date and correct author identification, but only the named students can provide authentic signatures.

**Why this option:** It makes the declaration page complete for signing while keeping the statement attributable to the actual authors.

**Consequences:** Both declaration pages now show the date and have three signature spaces. The group still needs to sign them before submission.

**Affected areas:** `tmp/pdfs/f26-deliverable-iii-template/build_report.py`, the generated front matter, and the final PDF.

**Revisit when:** The supervisor requires a different declaration date or signature placement.

## Runtime “why” checklist

When debugging a live session, read the events in this order:

1. `turn.user_message` — what the user actually sent.
2. `api.extract.request` / `api.extract.response` — what the provider was given and proposed.
3. `state.extraction_applied` or `state.recovery_applied` — what survived the state contract.
4. `validation_completed` — what was invalid or blocking.
5. `state.next_slot` — why the next slot was selected.
6. `api.question.request` / `api.question.response` / `question.rejected` — how the next wording was produced.
7. `turn.completed` — the final state and exact message shown to the user.
8. For catalog discovery, inspect the saved source plan: query, recommendations, score breakdown, limitations, unavailable alternatives, and source errors.

This sequence separates three different causes that can look similar in the UI: the provider misunderstood the message, the state contract rejected the provider’s evidence, or the priority policy selected a different unresolved requirement.

## Future decision record template

```markdown
### D-XXX — Short decision title

**Status:** Proposed / Accepted / Superseded
**Iteration:** YYYY-MM-DD or commit identifier
**Decision:** What the system will do.
**Context:** What problem, evidence, or user feedback prompted it.
**Options considered:** What realistic alternatives were rejected.
**Why this option:** The reasoning and evidence.
**Consequences:** Benefits, costs, and behavior users will observe.
**Affected areas:** Files, modules, APIs, data contracts, or deployment settings.
**Revisit when:** Evidence that would justify changing it.
```


### 2026-11-22 — Deliverable III author-voice edition

The user supplied a spoken writing sample and asked for the complete report in that voice. The revision uses the full Deliverable III source rather than the shorter personal-learning guide. Explanations use connected reasoning, concrete examples and natural first-person plural, while technical distinctions, evidence and citations are retained. The project uses a separate output folder so the user can compare versions. The university class and all seven original template files are preserved byte-for-byte; declarations and signature fields keep their formal wording. A point-forecast explanation is clarified to avoid incorrectly defining every point estimate as the most likely value.

Output: `output/latex/F26-012-deliverable-iii-voice/`.

### D-027 — Final Deliverable III source package

**Status:** Accepted on 2026-11-22.

**Decision:** Package the complete voice-revised report with the unchanged university class and an archive of all seven original template files. Remove the explicitly empty second page, restore the declaration headings to the class typography, retain blank signature rules, shorten only the list-of-figures entries for long captions, and keep research citations at their verified publication venues.

**Context:** The final ZIP needed to be editable, to follow the supplied LaTeX format, and to address earlier page and reference-format concerns. One figure-flow check also found a one-line page at the end of Chapter 5.

**Why this option:** It preserves the university class byte-for-byte and keeps the report's content and claims intact while fixing observable layout defects. The current research bibliography has no arXiv-only item; unpublished future work should be identified explicitly as an arXiv preprint rather than assigned a venue it lacks.

**Consequences:** The compiled report has 82 A4 pages, no blank second page or one-line Chapter 5 page, chapter-wise figure and table numbering, page-numbered lists, and visible declaration signature spaces. The students must sign before submission.

**Affected areas:** `output/latex/F26-012-deliverable-iii-final/` and the source ZIP in Downloads.

**Revisit when:** The committee supplies a revised template, a source's publication status changes, or the authors request another report revision.
