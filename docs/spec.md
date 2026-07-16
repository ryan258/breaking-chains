# Spec: First-Principles Discovery Forge

## Status

Phase 1 specification for human review. No application code should be written until this document is approved.

## Objective

Build a local-first discovery system that helps one user turn a question, observation, primary source, measurement, experiment, or earlier discovery into a traceable chain:

`evidence -> connections -> insight -> hypothesis -> practical action`

The system exists to produce deeper understanding, original theories, and practical experiments without confusing model fluency, web consensus, or unsupported interpretation with evidence.

The primary user has limited typing capacity. Every decision point must therefore support a single-letter response. Free-form input remains available as option `E`, but is never required when one of the supplied choices is sufficient.

### Core user stories

- As the user, I can begin an investigation from a short question, an observation, a local primary source, or a promising thread from prior work.
- As the user, I can control the forge using A-E choices in either a terminal or a basic local Streamlit interface.
- As the user, I can choose Quick, Standard, or Deep mode to control time and model cost.
- As the user, I can inspect and correct premises before the system builds on them.
- As the user, I can distinguish assumptions, observations, measurements, primary sources, deductions, hypotheses, and actions in every saved investigation.
- As the user, I can stop and later resume an investigation without losing its state.
- As the user, I can read the durable record without running the application.

## Product Principles

1. **First principles before consensus:** Start from explicit premises and inspectable evidence, not broad web summaries.
2. **Traceability before eloquence:** Every consequential claim must point to its premises, evidence, and derivation.
3. **Speculation with labels:** Novel possibilities are encouraged, but uncertainty and evidence type remain visible.
4. **Adversarial refinement:** Promising hypotheses must survive contradiction-seeking and skeptical review.
5. **Action closes the loop:** Investigations should end in a practical test, observation, decision, or explicitly documented reason not to act.
6. **Low-effort control:** The Lead absorbs orchestration complexity and presents clear, short choices.

## Scope

### Version-one capabilities

- Terminal interface with single-letter choices.
- Local Streamlit interface using large A-E buttons and the same application core.
- OpenRouter-backed model calls with one configurable model per role.
- A Lead coordinating five specialist roles.
- Quick, Standard, and Deep investigation modes.
- Three mandatory human checkpoints.
- Markdown investigation records with a SQLite search/index layer.
- Import of local text and Markdown primary materials.
- Resumable investigations.
- Explicit evidence typing, uncertainty labels, premise tracing, contradiction checks, and experiment/action design.

### Out of scope for version one

- General web search, search-provider adapters, autonomous crawling, or secondary-source aggregation.
- A hosted service, authentication, accounts, or multi-user collaboration.
- Mobile or native desktop applications.
- Automated execution of real-world experiments.
- Treating model output as evidence.
- Vector databases or opaque retrieval systems.
- A polished public-facing Streamlit product.

## Tech Stack

- Python 3.12 or newer.
- `uv` for environments, dependency management, locking, and command execution.
- OpenRouter through a small application-owned HTTP adapter; no orchestration framework is required for version one.
- `httpx` for HTTP transport.
- `pydantic` and `pydantic-settings` for domain validation and environment configuration.
- `typer` for CLI commands and `rich` for readable terminal output.
- `streamlit` for the basic local graphical interface.
- Python `sqlite3` for the index and workflow state.
- Markdown files as the canonical human-readable investigation record.
- `pytest` for testing and `ruff` for linting/formatting.

Dependencies must be locked in `uv.lock`. The project must not embed provider credentials or model names in source code.

## Configuration

`.env` is local and ignored by version control. `.env.example` documents all supported keys with safe placeholders.

Required configuration:

```dotenv
OPENROUTER_API_KEY=
FORGE_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

FORGE_MODEL_LEAD=
FORGE_MODEL_RESEARCHER=
FORGE_MODEL_CONNECTION_FINDER=
FORGE_MODEL_SYNTHESIZER=
FORGE_MODEL_SKEPTIC=
FORGE_MODEL_EXPERIMENT_DESIGNER=

FORGE_DEFAULT_DEPTH=standard
FORGE_DATA_DIR=./data
FORGE_OUTPUT_DIR=./outputs
FORGE_LOG_DIR=./logs
FORGE_QUICK_MAX_CALLS=6
FORGE_STANDARD_MAX_CALLS=10
FORGE_DEEP_MAX_CALLS=24
FORGE_QUICK_MAX_OUTPUT_TOKENS_PER_CALL=1200
FORGE_STANDARD_MAX_OUTPUT_TOKENS_PER_CALL=2400
FORGE_DEEP_MAX_OUTPUT_TOKENS_PER_CALL=4800
```

Each model value uses an OpenRouter model identifier. Startup validation must list every missing or invalid key in one response. Secrets must never appear in logs, Markdown records, SQLite, exceptions shown to the user, or Streamlit state persisted to disk.

## Specialist Roles

### Lead

- Converts an initial seed into A-E investigation-focus choices.
- Coordinates specialists without exposing orchestration burden to the user.
- Enforces evidence types, checkpoints, depth budgets, and completion rules.
- Produces the final traceable investigation record.
- May summarize specialist output but may not silently change its epistemic status.

### First-Principles Researcher

- Extracts explicit premises, definitions, observations, measurements, and claims from user input and supplied local materials.
- Separates what is observed from what is interpreted.
- Traces deductions and flags unsupported assumptions.
- Does not browse the general web.

### Connection Finder

- Searches the current investigation and indexed prior investigations for structural analogies, shared constraints, contradictions, and non-obvious relationships.
- Labels every proposed connection with its basis and confidence.

### Synthesizer

- Forms candidate insights and hypotheses from the evidence and connections.
- Preserves alternative explanations instead of prematurely collapsing them.

### Skeptic

- Seeks contradictions, counterexamples, hidden premises, circular reasoning, unfalsifiable claims, and overconfident language.
- Recommends retain, revise, or reject for every generated hypothesis.

### Experiment Designer

- Converts surviving hypotheses into the smallest informative test, observation, measurement, or practical next action.
- States the expected observation, disconfirming observation, cost, risk, and stopping condition.

## Epistemic Model

Every epistemic item has:

- a stable identifier;
- an epistemic category and, when applicable, a subtype;
- the exact claim or observation;
- provenance;
- uncertainty;
- links to supporting or conflicting items;
- optional notes from the user.

Epistemic items belong to distinct categories that must never be collapsed:

- `premise`: an explicitly adopted starting assumption, definition, or axiom; it is not evidence;
- `evidence`: an inspectable input with one of the allowed evidence types below;
- `derived_claim`: a deduction whose derivation names every premise, evidence item, and intermediate claim it depends on;
- `exploratory_item`: an interpretation, speculation, connection, hypothesis, or model suggestion.

Allowed `evidence` types are:

- `direct_observation`: something the user directly perceived or recorded;
- `primary_source`: a supplied original document or first-hand record;
- `measurement`: a value with method, unit, and conditions;
- `experiment_result`: an outcome with procedure and reproducibility notes.

Allowed `exploratory_item` types are:

- `interpretation`;
- `speculation`;
- `connection`;
- `hypothesis`;
- `model_suggestion`.

Confidence uses `low`, `medium`, or `high` plus a short rationale. Confidence is not a substitute for provenance, and high confidence does not promote a premise or exploratory item into evidence.

## Investigation Workflow

An investigation is a persisted state machine:

1. `seeded` — capture a question, observation, local source, or prior opportunity.
2. `source_consent` — when local material would be sent to OpenRouter, explain that it will leave the machine and require an explicit A-E decision before transmission.
3. `focus_checkpoint` — Lead offers A-E focus choices; user selects one.
4. `premises_extracted` — Researcher identifies premises, definitions, and evidence.
5. `evidence_checkpoint` — user accepts, rejects, edits, or requests another pass over the evidence and premises.
6. `connections_generated` — Connection Finder proposes traceable relationships.
7. `hypotheses_synthesized` — Synthesizer forms candidate insights and hypotheses.
8. `stress_tested` — Skeptic records challenges and retain/revise/reject outcomes.
9. `actions_designed` — Experiment Designer proposes tests or practical actions.
10. `action_checkpoint` — user chooses, modifies, defers, or rejects the proposed action.
11. `completed` — Lead writes the final Markdown record and updates the SQLite index.

The user can pause at any state. Resume must continue from the last completed state without repeating paid model work unless explicitly requested.

### Depth modes

| Mode | Intended use | Behavior |
| --- | --- | --- |
| Quick | Triage or early exploration | One pass per required role, smallest configured output limit, at most three candidate connections and hypotheses |
| Standard | Default investigation | Full workflow, moderate alternatives, one skeptical revision cycle |
| Deep | High-value or difficult questions | Broader prior-work retrieval, multiple independent candidate sets, up to three skeptical revision cycles |

Exact call limits and per-call maximum output tokens live in configuration with tested defaults. The orchestrator must enforce both. The interface must show the selected mode before work begins.

## Interaction Design

### Shared interaction contract

- Every user decision displays one focused question, including depth selection, source consent, checkpoints, pause/resume, and error recovery.
- Choices are labeled A, B, C, D, and E.
- `E` always means a custom answer and explains that the user may add only as much detail as desired.
- The recommended choice is identified with a one-sentence reason.
- Letter matching is case-insensitive and accepts surrounding whitespace.
- Invalid input repeats the same question without losing state or making another model call.
- Long specialist output is summarized first; full detail remains available on demand.
- Before any local source content is sent to OpenRouter, state what content will leave the machine and require explicit confirmation; declining keeps the investigation local and offers a manual premise/evidence path.
- Non-decision actions such as supplying seed text, opening details, and viewing saved records are exempt from A-E choice framing.

### Terminal interface

Primary command:

```bash
uv run forge investigate
```

The CLI supports:

```text
uv run forge investigate [--mode quick|standard|deep] [--seed TEXT] [--source PATH]
uv run forge resume INVESTIGATION_ID
uv run forge list [--status STATUS]
uv run forge config-check
```

Interactive choices accept a single letter followed by Enter. The interface must work without color and must not rely on pointer input.

### Streamlit interface

Primary command:

```bash
uv run streamlit run src/forge/ui/streamlit_app.py
```

The basic interface contains:

- a start/resume screen;
- seed text and local-file input;
- Quick, Standard, and Deep selectors;
- large A-E buttons for every user decision;
- visible current stage and completed-stage list;
- concise evidence, premise, challenge, and action review panels;
- a custom-answer field revealed only after selecting E;
- a link or control to open the saved Markdown record.

Streamlit must invoke the same application services as the CLI. Business rules, model orchestration, and persistence logic may not live in Streamlit callbacks.

Every A-E button must have a rendered target of at least 44 by 44 CSS pixels, an accessible name containing its letter and choice text, keyboard focus in logical order, activation with Enter and Space, and a visible focus indicator that is not clipped. The interface must not rely on color alone to communicate selection, stage, uncertainty, or failure.

## Persistence

### Canonical Markdown

Each investigation has a working Markdown file under `outputs/investigations/<id>.md` from its first persisted stage onward. Active, paused, and completed states share the same record so every finished stage is restart-safe. It includes:

1. seed and selected focus;
2. depth mode and timestamps;
3. explicit premises;
4. typed evidence and provenance;
5. proposed connections;
6. candidate insights and hypotheses;
7. skeptical challenges and dispositions;
8. selected experiment or action;
9. unresolved questions;
10. a machine-readable metadata block sufficient to rebuild the SQLite index.

### SQLite index

`data/forge.sqlite3` stores investigation identity, workflow state, searchable summaries, item identifiers, relationships, timestamps, and model-call receipts needed for resumption and cost inspection. It is an index and state store, not the only copy of the intellectual record.

The index must be rebuildable from Markdown records. Rebuilding may omit transient UI state but must preserve completed intellectual content and cross-investigation links.

### Local execution trace

`logs/forge.jsonl` records compact structured events for each model-call start, attempt, retry, cancellation, failure, and success. Events include investigation ID, call ID, role, model, timing, attempts, sanitized failure class, usage/cost, prompt-contract version, and the related artifact path. Prompt and response bodies never appear in this operational log.

`outputs/model-calls/<investigation-id>/<call-id>.json` stores the complete sanitized provider request and response for local inspection. Credentials are stripped, paths are constrained beneath the configured output root, and trace directories/files use private owner-only permissions. `outputs/smoke/openrouter-smoke.md` is the human-readable result of an explicitly invoked live gateway check.

## Model and Provider Boundary

Define an application-owned `ModelGateway` interface with structured request and response models. The OpenRouter implementation is the only version-one provider implementation, but orchestration code depends only on the interface.

Each call records:

- investigation and role;
- configured model identifier;
- depth mode;
- start/end timestamps;
- success or sanitized failure;
- provider-reported token usage and cost when available;
- a hash or stable identifier for the prompt contract version.

The gateway must use timeouts, bounded retries for transient failures, and cancellation-safe persistence. A failed specialist call leaves the investigation resumable.

## Project Structure

```text
pyproject.toml                 Project metadata, dependencies, and tool configuration
uv.lock                        Locked dependency graph
.env.example                   Safe configuration template
README.md                      Setup and user workflow
docs/spec.md                   This living specification
src/forge/
  cli.py                       Typer command adapter
  config.py                    Validated environment configuration
  domain/                      Evidence, investigation, role, and workflow models
  application/                 Use cases and orchestration services
  roles/                       Versioned role prompt contracts and parsers
  gateways/                    ModelGateway and OpenRouter implementation
  persistence/                 Markdown repository and SQLite index
  ui/streamlit_app.py          Thin Streamlit adapter
tests/
  unit/                        Pure domain and service tests
  integration/                 Persistence and mocked-provider tests
  contract/                    Role-output and gateway contract tests
  e2e/                         Scripted CLI and Streamlit smoke tests
data/                          Runtime data; ignored except documented examples
logs/                          Metadata-only JSONL event trace; ignored
outputs/                       Markdown records and sanitized call artifacts; ignored
```

## Code Style

- Use type hints for public and internal interfaces.
- Prefer small immutable domain models and explicit return types.
- Keep side effects behind gateways and repositories.
- Use descriptive domain names; avoid generic `manager`, `helper`, or `utils` modules.
- Format and lint with Ruff.
- Role output is parsed into validated structures before entering the domain layer.

Example:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InvestigationSeed:
    text: str
    source_path: str | None = None


class ModelGateway(Protocol):
    async def run_role(self, request: "RoleRequest") -> "RoleResult": ...
```

## Commands

Project bootstrap:

```bash
uv init --package
uv add httpx pydantic pydantic-settings typer rich streamlit
uv add --dev pytest pytest-asyncio pytest-cov pytest-playwright ruff
uv run playwright install chromium
```

Development and verification:

```bash
uv sync
uv run forge config-check
uv run forge investigate
uv run streamlit run src/forge/ui/streamlit_app.py
uv run pytest
uv run pytest --cov=forge --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
```

## Testing Strategy

### Unit tests

- Evidence-type and provenance validation.
- Legal and illegal workflow transitions.
- A-E input normalization, including lowercase and whitespace.
- A-E decision framing for mode selection, source consent, checkpoints, pause/resume, and all recovery paths.
- Depth-mode budgets and role selection.
- Premise/deduction trace completeness.
- Secret redaction.

### Contract tests

- Every specialist response validates against its structured schema.
- Prompt-contract fixtures preserve evidence/interpretation separation.
- The gateway maps OpenRouter successes, usage, timeouts, rate limits, and malformed responses into application results without leaking secrets.

### Integration tests

- Pause/resume across every workflow state.
- Markdown and SQLite remain consistent after successful and failed calls.
- SQLite can be rebuilt from Markdown records.
- Prior investigations can be retrieved for the Connection Finder.
- CLI and Streamlit adapters invoke the same application use cases.

### End-to-end smoke tests

- Complete a Quick investigation through the CLI using a deterministic fake model gateway.
- Complete the same fixture through Streamlit's testing interface.
- Resume a deliberately interrupted Standard investigation.
- Use Playwright to verify every rendered A-E control is at least 44 by 44 CSS pixels, is reachable in logical keyboard order, has a programmatic name, visibly receives focus, and activates with Enter and Space.

Domain and application modules should reach at least 90% line coverage. UI rendering and provider transport are judged primarily through focused integration and smoke tests rather than a global coverage target.

## Failure and Recovery

- Validate configuration before starting paid work.
- Treat imported material as untrusted data, never as instructions that can alter role behavior or system policy.
- Persist the workflow state before and after each model call.
- Retry only transient transport and rate-limit failures, with bounded exponential backoff.
- Never automatically retry invalid structured role output more than the configured role-repair allowance.
- Show a short, actionable A-E recovery question offering Resume, Retry, Change model, Stop, and Custom where applicable.
- Preserve successfully completed role results when a later role fails.
- Record sanitized diagnostic details locally without API keys or full sensitive source content.

## Boundaries

### Always

- Preserve a visible distinction between evidence, assumption, interpretation, and hypothesis.
- Cite local source paths and locations when a claim depends on supplied material.
- Validate model output before persistence.
- Make every paid step resumable.
- Use the shared application layer from both interfaces.
- Run tests, lint, and formatting checks before considering a change complete.

### Ask first

- Add a new external service or model provider.
- Enable any general internet or web-search capability.
- Change the evidence taxonomy or canonical Markdown schema.
- Add database migrations that cannot be rebuilt from Markdown.
- Execute an experiment or external action on the user's behalf.
- Send newly supplied local source content to OpenRouter without explicit confirmation.
- Add authentication, hosting, telemetry, or multi-user behavior.

### Never

- Commit `.env`, API keys, or private source material.
- Present model output, popularity, or consensus as evidence.
- Hide a failed skeptical review or unsupported premise.
- Make network calls outside the configured model gateway.
- Require free-form typing when an A-E choice can express the decision.
- Destroy an investigation record to recover from an error.

## Success Criteria

Version one is complete when all of the following are demonstrably true:

1. A fresh clone can be prepared with `uv sync` after the user creates `.env` from `.env.example`.
2. `uv run forge config-check` identifies all missing configuration without revealing secrets.
3. The user can complete and resume an investigation through single-letter terminal choices.
4. The user can complete the same workflow through large A-E controls in local Streamlit.
5. Question, observation, local text/Markdown source, and prior investigation can each seed a new investigation.
6. Quick, Standard, and Deep modes visibly alter bounded orchestration budgets.
7. The three human checkpoints cannot be bypassed during normal interactive operation.
8. Every final claim can be traced to typed evidence and explicit premises, or is visibly labeled as interpretation, speculation, connection, hypothesis, or model suggestion.
9. The Skeptic records a retain, revise, or reject disposition for every generated hypothesis.
10. The Experiment Designer produces a test/action with expected and disconfirming observations, or records why no responsible test is available.
11. A paused or provider-failed investigation resumes without repeating completed model calls.
12. Markdown remains readable on its own, while SQLite search can locate prior premises, evidence, connections, and hypotheses.
13. Deleting and rebuilding the SQLite index from Markdown preserves completed investigation content and relationships.
14. Automated tests pass without live provider credentials; live OpenRouter checks are optional and explicitly invoked.
15. No general web search exists in the application, and secrets are absent from records, logs, and displayed errors.
16. Local source content is never sent to OpenRouter before the interface explains the boundary and records an explicit confirmation; declining still permits a local/manual workflow.
17. Mode selection, consent, all three checkpoints, pause/resume, and every recovery decision use the A-E contract; supplying text and viewing information are the only explicit exemptions.
18. Automated browser checks verify Streamlit A-E controls meet the defined 44-by-44-pixel, accessible-name, keyboard-order, keyboard-activation, and visible-focus requirements.

## Assumptions Requiring Approval

- CLI and Streamlit are equal adapters over one shared application core.
- Streamlit is local-only in version one and has no authentication or deployment work.
- Local primary-source import initially supports UTF-8 text and Markdown; PDF and office-document extraction can be added later.
- SQLite full-text search is sufficient initially; semantic/vector search is deferred.
- OpenRouter is the only provider implementation, but an application-owned gateway prevents orchestration lock-in.
- The specific OpenRouter model assigned to each role is chosen by the user in `.env`, not prescribed by the application.

## Open Questions

None are blocking specification review. Any change to the assumptions above should be made in this document before implementation planning begins.
