# Implementation Plan: First-Principles Discovery Forge

## Status

Phase 2 implementation plan for human review. It is derived from the approved [technical specification](./spec.md). No application code should be written until this plan is approved.

## Overview

Build the forge through a sequence of small, verifiable slices. The first milestone proves the epistemic model and persistence without paid model calls. The second proves a complete resumable investigation using deterministic fake specialists. The third replaces those fakes with validated OpenRouter role contracts. The final milestones add the two user interfaces, measurable accessibility, and production hardening.

## Architecture Decisions

- **One application core, two adapters:** CLI and Streamlit invoke the same use cases so investigations can move between interfaces without behavioral drift.
- **Markdown is canonical:** SQLite is a rebuildable workflow/search projection, preventing intellectual work from being trapped in an opaque database.
- **Explicit epistemic categories:** Premises, evidence, derived claims, and exploratory items have distinct validated models.
- **State-machine orchestration:** Every stage is persisted and idempotent enough to resume without repeating completed paid work.
- **Application-owned provider boundary:** OpenRouter sits behind `ModelGateway`; orchestration never depends directly on provider response shapes.
- **Structured specialist contracts:** Every model response is validated before it can affect an investigation record.
- **No general web research:** The only version-one network path is the configured model gateway.
- **Accessibility is behavioral:** The A-E contract applies to every decision, and Streamlit controls have automated size, naming, focus, and keyboard checks.

## Dependency Graph

```text
Package bootstrap and configuration
  -> Epistemic domain model
    -> Investigation state machine and A-E decisions
      -> Markdown canonical repository -> SQLite projection and rebuild ----┐
      -> Model gateway contract and OpenRouter adapter --------------------┤
                                                                           v
                                                           Fake-gateway walking skeleton
                                                             -> CLI end-to-end slice
                                                               -> Source-consent gate
                                                                 -> Specialist role contracts
                                                                   -> Full orchestration, budgets, and recovery
                                                                     -> Streamlit end-to-end slice
                                                                       -> Accessibility verification
                                                                         -> Documentation and release verification
```

The graph is intentionally foundation-heavy only until Task 6. Tasks 7 onward are vertical slices that keep a runnable workflow at every checkpoint.

## Phase 1: Trusted Foundation

### Task 1A: Bootstrap the package

**Description:** Create the `uv` package, locked dependency graph, and repository exclusions before any local secrets or runtime data exist.

**Acceptance criteria:**

- [x] `uv sync` creates a working environment from committed metadata and lockfile.
- [x] `.gitignore` excludes `.env`, runtime investigations, SQLite files, caches, and private source material.

**Verification:**

- [x] `uv sync`
- [x] `uv run ruff check .`

**Dependencies:** None.

**Files likely touched:**

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `src/forge/__init__.py`

**Estimated scope:** Small, 4 files.

### Task 1B: Add validated environment configuration

**Description:** Add the safe environment template and fail-fast settings loader with the exact defaults approved in the specification.

**Acceptance criteria:**

- [x] Settings validate every required role model, data path, and OpenRouter credential while redacting secrets.
- [x] Depth defaults are exactly 6/10/24 calls and 1200/2400/4800 maximum output tokens per call for Quick/Standard/Deep.
- [x] Missing or invalid settings are reported together, and `.env.example` contains placeholders but no credential.

**Verification:**

- [x] `uv run pytest tests/unit/test_config.py`
- [x] Manual check: omit several keys and confirm one sanitized error lists all configuration problems.

**Dependencies:** Task 1A.

**Files likely touched:**

- `.env.example`
- `src/forge/config.py`
- `tests/unit/test_config.py`

**Estimated scope:** Small, 3 files.

## Checkpoint 0: Reproducible and secret-safe setup

- [x] `uv sync`
- [x] `uv run pytest tests/unit/test_config.py`
- [x] `uv run ruff check .`
- [x] Confirm `.env` and runtime data paths are ignored before adding any local credential.

### Task 2: Implement epistemic items and traceability invariants

**Description:** Add immutable validated models for premises, typed evidence, derived claims, exploratory items, provenance, confidence, and relationships. Enforce category separation at construction time.

**Acceptance criteria:**

- [x] Premises cannot be stored as evidence, and derived claims must name their complete dependency set.
- [x] Evidence subtypes enforce their required provenance fields, including method/unit/conditions for measurements.
- [x] High confidence cannot change an item's epistemic category.

**Verification:**

- [x] `uv run pytest tests/unit/test_epistemics.py`
- [x] `uv run ruff check src/forge/domain tests/unit/test_epistemics.py`

**Dependencies:** Task 1B.

**Files likely touched:**

- `src/forge/domain/__init__.py`
- `src/forge/domain/epistemics.py`
- `src/forge/domain/identifiers.py`
- `tests/unit/test_epistemics.py`

**Estimated scope:** Medium, 4 files.

### Task 3: Implement the investigation state machine and A-E contract

**Description:** Model investigation stages, legal transitions, checkpoint decisions, depth modes, pause/resume, and the shared A-E choice contract independently of either UI.

**Acceptance criteria:**

- [x] Illegal transitions fail without mutating state; legal transitions preserve a timestamped history.
- [x] Every decision type—mode, consent, checkpoint, pause/resume, and recovery—uses A-E with E reserved for custom input.
- [x] Letter normalization accepts lowercase and whitespace while invalid input preserves the active question.

**Verification:**

- [x] `uv run pytest tests/unit/test_investigation.py tests/unit/test_decisions.py`
- [x] `uv run ruff check src/forge/domain src/forge/application tests/unit`

**Dependencies:** Task 2.

**Files likely touched:**

- `src/forge/domain/investigation.py`
- `src/forge/application/decisions.py`
- `tests/unit/test_investigation.py`
- `tests/unit/test_decisions.py`

**Estimated scope:** Medium, 4 files.

## Checkpoint 1: Domain foundation

- [x] `uv run pytest tests/unit`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] Review a serialized fixture and confirm premises, evidence, claims, and hypotheses remain visibly distinct.

## Phase 2: Durable and Resumable Records

### Task 4: Add the canonical Markdown investigation repository

**Description:** Persist paused and completed investigations as readable Markdown with a versioned metadata block and atomic writes.

**Acceptance criteria:**

- [x] A domain investigation round-trips through Markdown without losing epistemic items, relationships, decisions, or workflow history.
- [x] Interrupted writes cannot replace a valid record with a partial file.
- [x] Local source references include paths, hashes, and locations without embedding secrets.

**Verification:**

- [x] `uv run pytest tests/integration/test_markdown_repository.py`
- [x] Manual check: open a generated fixture and understand the investigation without the application.

**Dependencies:** Task 3.

**Files likely touched:**

- `src/forge/persistence/markdown.py`
- `src/forge/persistence/metadata.py`
- `tests/integration/test_markdown_repository.py`
- `tests/fixtures/investigation_record.md`

**Estimated scope:** Medium, 4 files.

### Task 5: Add the rebuildable SQLite workflow and search projection

**Description:** Store resumable state, searchable summaries, item relationships, and model-call receipts in SQLite while keeping Markdown canonical.

**Acceptance criteria:**

- [x] Saving an investigation updates Markdown and SQLite consistently or leaves the previous valid state intact.
- [x] Deleting SQLite and rebuilding from Markdown preserves completed intellectual content and relationships.
- [x] Search locates prior premises, evidence, connections, and hypotheses by text and category.

**Verification:**

- [x] `uv run pytest tests/integration/test_sqlite_projection.py`
- [x] `uv run pytest tests/integration/test_rebuild_index.py`

**Dependencies:** Task 4.

**Files likely touched:**

- `src/forge/persistence/sqlite.py`
- `src/forge/persistence/unit_of_work.py`
- `tests/integration/test_sqlite_projection.py`
- `tests/integration/test_rebuild_index.py`

**Estimated scope:** Medium, 4 files.

### Task 6: Define the model gateway and validate OpenRouter transport

**Description:** Create provider-independent request/result contracts and an OpenRouter implementation with timeouts, bounded transient retries, structured-output parsing, usage capture, and secret-safe failures.

**Acceptance criteria:**

- [ ] Orchestration-facing models contain no OpenRouter-specific response shapes.
- [ ] Success, malformed output, timeout, rate limit, cancellation, and provider error fixtures map to explicit application results.
- [ ] Recorded receipts include role, model, timing, usage/cost when available, and prompt-contract version without secrets.

**Verification:**

- [ ] `uv run pytest tests/contract/test_model_gateway.py tests/contract/test_openrouter.py`
- [ ] `uv run ruff check src/forge/gateways tests/contract`
- [ ] Optional manual check: run the explicitly marked live smoke test with a low-cost configured model.

**Dependencies:** Tasks 1B and 3. Model-call receipts remain persistence-neutral until orchestration integrates them.

**Files likely touched:**

- `src/forge/gateways/model.py`
- `src/forge/gateways/openrouter.py`
- `tests/contract/test_model_gateway.py`
- `tests/contract/test_openrouter.py`

**Estimated scope:** Medium, 4 files.

## Checkpoint 2: Persistence and provider boundary

- [ ] `uv run pytest tests/unit tests/integration tests/contract`
- [ ] Rebuild a test SQLite index from Markdown and compare every canonical relationship.
- [ ] Confirm timeout, rate-limit, malformed-output, and provider-error fixtures map to sanitized application results.
- [ ] Scan generated records and captured logs for configured secret values.

## Phase 3: Walking Skeleton and Terminal Workflow

### Task 7: Build a deterministic full-workflow orchestrator

**Description:** Implement the Lead-controlled state progression using deterministic fake specialist results. Prove the complete evidence-to-action chain and all three checkpoints before writing production prompts.

**Acceptance criteria:**

- [ ] A fake-gateway Quick investigation reaches completion through focus, evidence, and action checkpoints.
- [ ] Every completed stage is persisted before the next stage begins.
- [ ] Pause, restart, and resume do not repeat completed fake role runs.

**Verification:**

- [ ] `uv run pytest tests/integration/test_orchestration_walking_skeleton.py`
- [ ] `uv run pytest tests/integration/test_resume.py`

**Dependencies:** Tasks 3, 5, and 6.

**Files likely touched:**

- `src/forge/application/orchestrator.py`
- `src/forge/gateways/fake.py`
- `tests/integration/test_orchestration_walking_skeleton.py`
- `tests/integration/test_resume.py`

**Estimated scope:** Medium, 4 files.

### Task 8: Deliver the CLI investigation slice

**Description:** Add commands to validate configuration, start/list/show/pause/resume investigations, and drive the walking skeleton through case-insensitive single-letter decisions.

**Acceptance criteria:**

- [ ] A user can complete a deterministic Quick investigation using only seed text and single-letter decisions.
- [ ] Invalid answers repeat the same decision without triggering another role call.
- [ ] An interrupted terminal session resumes from the last persisted stage.

**Verification:**

- [ ] `uv run pytest tests/e2e/test_cli.py`
- [ ] Manual check: `uv run forge investigate --mode quick --seed "What follows from this observation?"`

**Dependencies:** Task 7.

**Files likely touched:**

- `src/forge/cli.py`
- `src/forge/application/presenter.py`
- `tests/e2e/test_cli.py`
- `pyproject.toml`

**Estimated scope:** Medium, 4 files.

## Checkpoint 3: First runnable forge

- [ ] `uv run forge config-check`
- [ ] Complete, interrupt, and resume the fake-model CLI workflow.
- [ ] Inspect both Markdown and SQLite outputs.
- [ ] Confirm every decision can be made without free-form typing unless E is chosen.

## Phase 4: Production Specialist Contracts

### Task 9: Enforce local-source consent and privacy boundaries

**Description:** Establish the pre-transmission consent gate, source preview, declined-consent local/manual path, and a gateway guard before any production role can receive local source content.

**Acceptance criteria:**

- [ ] No local source content reaches `ModelGateway` before an explicit recorded A-E confirmation.
- [ ] UTF-8 text and Markdown import successfully; unsupported or binary formats fail clearly, while declined transmission preserves a manual premise/evidence path.
- [ ] Imported content is delimited as untrusted data and cannot change system or role instructions.

**Verification:**

- [ ] `uv run pytest tests/integration/test_source_consent.py tests/integration/test_source_isolation.py`
- [ ] `uv run pytest tests/integration/test_source_consent.py -k "text or markdown or unsupported"`
- [ ] Inspect fake-gateway calls and confirm zero source bytes before consent.

**Dependencies:** Tasks 3, 6, and 7.

**Files likely touched:**

- `src/forge/application/source_ingestion.py`
- `src/forge/application/orchestrator.py`
- `tests/integration/test_source_consent.py`
- `tests/integration/test_source_isolation.py`

**Estimated scope:** Medium, 4 files.

### Task 10: Implement Lead and First-Principles Researcher contracts

**Description:** Add versioned structured schemas and prompts for focus framing, premise extraction, evidence classification, provenance, derivations, and source-instruction isolation.

**Acceptance criteria:**

- [ ] Lead output always produces one focused A-E decision with E custom and a reasoned recommendation.
- [ ] Researcher output cannot classify premises or deductions as evidence and must identify unsupported assumptions.
- [ ] Supplied source content is delimited as untrusted data and cannot override role instructions.

**Verification:**

- [ ] `uv run pytest tests/contract/test_lead_role.py tests/contract/test_researcher_role.py`
- [ ] Run prompt-injection fixtures and confirm they remain quoted source material.

**Dependencies:** Tasks 2, 6, 7, and 9.

**Files likely touched:**

- `src/forge/roles/lead.py`
- `src/forge/roles/researcher.py`
- `tests/contract/test_lead_role.py`
- `tests/contract/test_researcher_role.py`

**Estimated scope:** Medium, 4 files.

### Task 11: Implement Connection Finder and Synthesizer contracts

**Description:** Add validated relationship proposals, cross-investigation retrieval inputs, alternative explanations, traceable insights, and hypotheses.

**Acceptance criteria:**

- [ ] Connections name their basis and uncertainty and are never promoted to evidence by analogy alone.
- [ ] Each derived claim and hypothesis references its complete dependency set.
- [ ] Synthesizer output preserves competing explanations when the evidence does not distinguish them.

**Verification:**

- [ ] `uv run pytest tests/contract/test_connection_role.py tests/contract/test_synthesizer_role.py`
- [ ] Verify a fixture with a tempting analogy remains labeled exploratory.

**Dependencies:** Tasks 2, 5, 6, 7, and 9.

**Files likely touched:**

- `src/forge/roles/connection_finder.py`
- `src/forge/roles/synthesizer.py`
- `tests/contract/test_connection_role.py`
- `tests/contract/test_synthesizer_role.py`

**Estimated scope:** Medium, 4 files.

## Checkpoint 4: Evidence and synthesis safety gate

- [ ] `uv run pytest tests/contract tests/integration/test_source_consent.py tests/integration/test_source_isolation.py`
- [ ] Confirm denied source consent produces zero source-bearing gateway calls.
- [ ] Confirm each implemented prompt contract has a recorded version identifier.
- [ ] Review adversarial fixtures for injection, false foundations, analogy-as-proof, and unsupported certainty.

## Phase 5: Full Orchestration and Cost Control

### Task 12: Implement Skeptic and Experiment Designer contracts

**Description:** Add contradiction-seeking, hypothesis disposition, falsifiers, and smallest-informative-test/action structures.

**Acceptance criteria:**

- [ ] Every generated hypothesis receives a retain, revise, or reject disposition with reasons.
- [ ] Surviving hypotheses include expected and disconfirming observations.
- [ ] Proposed tests state procedure, cost, risk, stopping condition, and reproducibility needs—or explain why no responsible test exists.

**Verification:**

- [ ] `uv run pytest tests/contract/test_skeptic_role.py tests/contract/test_experiment_role.py`
- [ ] Verify contradiction fixtures cause revision or rejection rather than silent omission.

**Dependencies:** Tasks 2, 6, 7, and 9.

**Files likely touched:**

- `src/forge/roles/skeptic.py`
- `src/forge/roles/experiment_designer.py`
- `tests/contract/test_skeptic_role.py`
- `tests/contract/test_experiment_role.py`

**Estimated scope:** Medium, 4 files.

### Task 13: Connect real roles, depth modes, skeptical loops, and recovery

**Description:** Replace fake results with configured role calls while retaining the fake gateway for tests. Enforce mode budgets, skeptical revision cycles, stage idempotency, and A-E recovery choices.

**Acceptance criteria:**

- [ ] Quick, Standard, and Deep enforce configured call and per-call output-token limits and visibly change orchestration behavior.
- [ ] Skeptical rejection can return the workflow to evidence review or synthesis without corrupting history.
- [ ] Timeout, rate limit, malformed output, and cancellation preserve completed work and offer A-E recovery.

**Verification:**

- [ ] `uv run pytest tests/integration/test_full_orchestration.py tests/integration/test_failure_recovery.py`
- [ ] `uv run pytest tests/integration/test_depth_budgets.py`
- [ ] Optional live Standard-mode smoke test with explicit cost observation.

**Dependencies:** Tasks 9, 10, 11, and 12.

**Files likely touched:**

- `src/forge/application/orchestrator.py`
- `src/forge/application/budgets.py`
- `tests/integration/test_full_orchestration.py`
- `tests/integration/test_failure_recovery.py`
- `tests/integration/test_depth_budgets.py`

**Estimated scope:** Medium, 5 files.

## Checkpoint 5: Complete headless system

- [ ] `uv run pytest tests/unit tests/contract tests/integration`
- [ ] Complete one fake and one optional live investigation through the CLI.
- [ ] Confirm source decline, provider failure, and process interruption all resume safely.
- [ ] Confirm no application code contains general web-search behavior.

## Phase 6: Streamlit Interface and Accessibility

### Task 14: Deliver the shared Streamlit investigation slice

**Description:** Build a thin local Streamlit adapter for start/resume, seed/source input, mode selection, stage progress, A-E decisions, evidence review, and saved-record access.

**Acceptance criteria:**

- [ ] An investigation started in CLI resumes in Streamlit and vice versa.
- [ ] All user decisions render A-E controls, with custom input appearing only after E.
- [ ] Streamlit remains a thin local-only adapter: it invokes shared services, binds to loopback, persists no secrets in session state, and adds no authentication, deployment, or multi-user behavior.

**Verification:**

- [ ] `uv run pytest tests/e2e/test_streamlit.py`
- [ ] Manual check: `uv run streamlit run src/forge/ui/streamlit_app.py --server.address 127.0.0.1`

**Dependencies:** Tasks 8, 9, and 13.

**Files likely touched:**

- `src/forge/ui/streamlit_app.py`
- `src/forge/ui/view_models.py`
- `tests/e2e/test_streamlit.py`

**Estimated scope:** Medium, 3 files.

### Task 15A: Add browser-accessibility tooling and baseline styles

**Description:** Add the Playwright test dependency, browser installation workflow, and centralized Streamlit styles needed for measurable target size and visible focus.

**Acceptance criteria:**

- [ ] `pytest-playwright` and its locked dependencies install reproducibly through `uv`.
- [ ] The documented browser setup installs Chromium for local accessibility tests.
- [ ] Streamlit loads a centralized style that provides 44-by-44-pixel minimum targets and an unclipped visible focus baseline.

**Verification:**

- [ ] `uv sync`
- [ ] `uv run playwright install chromium`
- [ ] `uv run pytest tests/e2e/test_streamlit.py`

**Dependencies:** Task 14.

**Files likely touched:**

- `pyproject.toml`
- `uv.lock`
- `src/forge/ui/streamlit_app.py`
- `src/forge/ui/assets/style.css`

**Estimated scope:** Medium, 4 files.

### Task 15B: Verify measurable Streamlit accessibility

**Description:** Add browser tests and minimal styling necessary to meet the specification's target-size, naming, focus-order, keyboard-activation, visible-focus, and non-color-only requirements.

**Acceptance criteria:**

- [ ] Every A-E target measures at least 44 by 44 CSS pixels and has an accessible name containing its letter and choice text.
- [ ] Controls receive visible, unclipped focus in logical order and activate with Enter and Space.
- [ ] Stage, uncertainty, selection, and failure remain understandable without color.

**Verification:**

- [ ] `uv run pytest tests/e2e/test_streamlit_accessibility.py`
- [ ] Manual keyboard-only smoke test of start, checkpoint, custom E, pause, resume, and recovery paths.

**Dependencies:** Task 15A.

**Files likely touched:**

- `src/forge/ui/streamlit_app.py`
- `src/forge/ui/accessibility.py`
- `tests/e2e/test_streamlit_accessibility.py`

**Estimated scope:** Medium, 3 files.

## Checkpoint 6: User-interface parity

- [ ] Complete the same deterministic investigation in CLI and Streamlit.
- [ ] Start in each interface and resume in the other.
- [ ] Pass automated browser accessibility checks.
- [ ] Verify all decisions—including consent and recovery—use A-E.

## Phase 7: Release Hardening

### Task 16A: Add operator documentation

**Description:** Document reproducible setup, safe configuration, everyday workflows, privacy boundaries, and recovery operations before final acceptance automation.

**Acceptance criteria:**

- [ ] README covers `uv` setup, `.env`, model-role assignment, CLI, Streamlit, privacy boundary, depth/cost modes, backup, and index rebuilding.
- [ ] Launch documentation binds Streamlit to `127.0.0.1` and describes the implications of sending approved local content to OpenRouter.
- [ ] The acceptance checklist maps all 18 specification criteria to a planned automated test or explicit human review.

**Verification:**

- [ ] Follow the README from a clean local environment through `forge config-check` without using live credentials.
- [ ] Review every checklist row for a concrete evidence location.

**Dependencies:** Tasks 13, 14, and 15B.

**Files likely touched:**

- `README.md`
- `docs/acceptance-checklist.md`
- `.env.example`

**Estimated scope:** Medium, 3 files.

### Task 16B: Add final deterministic acceptance gate

**Description:** Add a complete no-credential acceptance scenario and a verification runner that proves every automatable version-one criterion.

**Acceptance criteria:**

- [ ] One deterministic test exercises seed through completed Markdown and SQLite, including all three checkpoints and skeptical disposition.
- [ ] The verification runner reports evidence for all 18 specification criteria and fails when any automatable criterion is unmet.
- [ ] Domain and application packages each meet the 90% coverage threshold independently.

**Verification:**

- [ ] `uv run pytest tests/unit tests/integration tests/e2e --cov=forge.domain --cov-fail-under=90`
- [ ] `uv run pytest tests/unit tests/integration tests/e2e --cov=forge.application --cov-fail-under=90`
- [ ] `uv run pytest tests/e2e/test_acceptance.py`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`

**Dependencies:** Task 16A.

**Files likely touched:**

- `tests/e2e/test_acceptance.py`
- `scripts/verify_acceptance.py`
- `pyproject.toml`

**Estimated scope:** Medium, 3 files.

## Checkpoint 7: Version-one completion

- [ ] All automated tests pass without live provider credentials.
- [ ] Domain coverage and application coverage each independently meet at least 90%.
- [ ] Ruff lint and format checks pass.
- [ ] The acceptance checklist contains evidence for all 18 specification criteria.
- [ ] Optional live OpenRouter smoke tests are explicitly invoked and cost-bounded.
- [ ] Human review confirms the terminal and Streamlit experiences are physically usable.

## Parallelization Opportunities

- Tasks 4-5 persistence work and Task 6 gateway work may proceed in parallel only after Tasks 1B-3 freeze the domain interfaces.
- Tasks 10, 11, and 12 are safe to parallelize after Task 9 establishes the source-consent boundary; shared schemas must be agreed before work begins.
- Streamlit work must wait for the shared application use cases and A-E contract, but accessibility test scaffolding can begin once Task 14 fixes the DOM structure.
- Task 16A documentation can begin after CLI behavior stabilizes, but final acceptance evidence waits for Task 15B.
- Tasks that modify `orchestrator.py`—7, 9, and 13—must remain sequential.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Weak premises produce confidently wrong deductions | High | Enforce category separation, premise status, skeptical challenges, and revision history from Tasks 2 and 12 |
| Markdown and SQLite diverge | High | Atomic unit of work, canonical Markdown, rebuild tests, and failure injection in Tasks 4-5 |
| OpenRouter structured output varies by model | High | Application-owned schemas, bounded repair, per-role contract fixtures, and model-independent fake gateway |
| Paid calls repeat after interruption | High | Persist before/after every call and key runs by investigation, stage, role, and prompt version |
| Local primary material is disclosed unexpectedly | High | Explicit source-consent state and zero-byte-before-consent tests in Task 9 |
| Analogy is treated as proof | Medium | Exploratory category, connection basis, uncertainty, and adversarial contract fixtures |
| Streamlit reruns corrupt workflow state | High | Keep state in the application/persistence layers, not UI session state |
| A-E accessibility erodes in secondary flows | High | Shared decision model plus browser coverage for consent, pause/resume, and recovery |
| Deep mode creates runaway cost | Medium | Hard call/output limits, visible selected mode, recorded usage, and cost-bounded live smoke tests |
| Source text attempts prompt injection | High | Treat imports as delimited untrusted data and test hostile fixtures |

## Implementation Boundaries

- Update `docs/spec.md` before implementing any requirement that changes the approved product behavior.
- Implement one task at a time with tests written before behavior changes.
- Do not add new providers, internet search, hosting, authentication, telemetry, vector search, or document formats without approval.
- Do not commit credentials, runtime investigations, private source material, or live-model response fixtures containing user data.
- Do not begin the next checkpoint group while the current checkpoint is failing.

## Open Questions

None are blocking plan approval. Model identifiers remain user-configured in `.env`; Task 1B must use the approved 6/10/24 call limits and 1200/2400/4800 per-call output-token limits.
