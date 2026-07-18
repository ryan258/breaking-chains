# First-Principles Forge

First-Principles Forge is a local, resumable workspace for investigating a question from explicit
premises and typed evidence. It uses A-E decisions in both the terminal and Streamlit, keeps a
human-readable Markdown record as the source of truth, and treats SQLite as a rebuildable search
index. General web search is intentionally absent.

## Quick start

Requirements: Python 3.12 or newer and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
uv run forge config-check
```

The example configuration contains non-secret placeholders, so deterministic preview works without
a live credential. Before choosing live execution, replace `OPENROUTER_API_KEY` and all six
`FORGE_MODEL_*` values with intentional OpenRouter settings. Never commit `.env`.

For browser accessibility tests, install the locked Chromium runtime once:

```bash
uv run playwright install chromium
```

## Everyday commands

Start an investigation and answer each prompt with one letter. Choose **D — Use deterministic
preview** at the live-execution question to make no provider calls.

```bash
uv run forge investigate --seed "Why does this system oscillate?"
uv run forge investigate --seed "What follows from these notes?" --source ./notes.md
uv run forge investigate --seed "What should we test next?" --prior inv_example
uv run forge resume inv_example
uv run forge list
```

Supplying `--mode quick`, `--mode standard`, or `--mode deep` is available for scripted use. When
the flag is omitted, the interactive A-E mode question is used. `--source` accepts a regular UTF-8
`.txt`, `.md`, or `.markdown` file up to 1 MB. `--prior` creates a traceable follow-up from a saved
investigation.

Launch the graphical adapter:

```bash
uv run streamlit run src/forge/ui/streamlit_app.py
```

The checked-in Streamlit configuration binds to `127.0.0.1`, enables XSRF protection, and limits
uploads to 1 MB. Do not expose this version-one interface on a LAN or public host: it deliberately
has no authentication, deployment, or multi-user behavior.

## Live execution and cost bounds

Every live start and live resume asks for fresh A-E confirmation before a provider call. The prompt
shows the chosen mode, call ceiling, per-call output-token ceiling, and source boundary.

| Mode | Maximum calls | Maximum output tokens per call |
| --- | ---: | ---: |
| Quick | 6 | 1,200 |
| Standard | 10 | 2,400 |
| Deep | 24 | 4,800 |

These are hard defaults and may be lowered in `.env`. Each role has a separate model assignment:
Lead, Researcher, Connection Finder, Synthesizer, Skeptic, and Experiment Designer. A failed call
stores a sanitized receipt and offers A-E recovery without discarding completed stages.

## Privacy boundary

- Seed text and approved role prompts are sent to OpenRouter only after **A — Approve live
  execution**.
- An attached local source has a second, separate A-E consent checkpoint. Before **A**, its content
  is never included in a provider request. Declining still permits a local/manual investigation.
- Streamlit uploads are copied to `data/sources/` with owner-only permissions so consent and resume
  remain reliable; delete that local copy when it is no longer needed.
- API keys are loaded from `.env` and are excluded from session state, Markdown, SQLite, trace
  artifacts, logs, and displayed errors.
- Local source and model output are untrusted data. Model output is schema-validated before it can
  enter a canonical record.

## Storage, backup, and recovery

Canonical records live in `outputs/investigations/*.md`. Back up that directory first; it contains
the readable report and the complete versioned metadata needed to resume and rebuild. Back up
`outputs/model-calls/` and `logs/` only if you also want local diagnostic history. Protect any
backup containing `.env` or private sources separately.

SQLite is disposable. Rebuild it from Markdown after deletion, corruption, or restore:

```bash
uv run forge rebuild-index
```

If a run is paused or interrupted, use `uv run forge resume <id>` or select the saved record in
Streamlit. The application reopens the first unfinished checkpoint and does not repeat completed
deterministic stages. Provider failure and exhausted-budget prompts preserve the same record.

## Verification

The deterministic gate requires no valid provider credential:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/verify_acceptance.py
```

`pytest-playwright` is locked for reproducible browser installation. Its global pytest plugin is
disabled because its soft-assertion event-loop hook conflicts with the async orchestration suite;
the accessibility tests create the same isolated Chromium browser directly through Playwright.

The optional OpenRouter smoke test performs exactly one synthetic Lead call with a 500-output-token
ceiling. It costs real provider usage and must be invoked separately:

```bash
uv run python scripts/smoke_openrouter.py
```

Do not run the optional smoke command until `.env` contains the intended credential and model.

## Architecture

Both interfaces call the same application orchestrator. The orchestrator owns stage transitions,
budgets, skeptical revision loops, consent, and recovery. Role modules own versioned structured
prompt contracts. Markdown is canonical; SQLite is only a projection. See [the specification](docs/spec.md),
[implementation plan](docs/implementation-plan.md), and
[acceptance evidence](docs/acceptance-checklist.md) for the rationale and detailed contracts.
