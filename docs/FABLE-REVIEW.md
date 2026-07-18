# Fable Review — First-Principles Forge

Reviewed 2026-07-17 at commit `b72ed22`. Scope: all of `src/`, `scripts/`, `tests/`, config, and build metadata. Baseline: 117 tests pass, `ruff check` clean.

> **Status update, 2026-07-17 (release pass):** Findings 1-4 are fixed, including live depth-budget enforcement and A-E recovery. The shared-text and environment-name simplifications are complete. CLI and Streamlit adapters, README/operator guidance, deterministic acceptance reporting, browser accessibility checks, and CI are now built. A subsequent whole-project audit also closed dangling local epistemic references, compound secret-key redaction, declined-consent isolation, and the source-consent prompt copy. The remaining review follow-ups are the smoke-script private-write helper and lock backoff optimization; neither blocks version-one acceptance.

## Verdict

This is an unusually disciplined codebase for its age: frozen validated models everywhere, atomic writes with fsync, secret redaction, monotonic clock guards, restart-safe orchestration, and a rebuildable projection. The foundations are trustworthy. The findings below are one confirmed behavioral bug, a handful of design corrections worth making before the CLI/UI phases build on top of them, and some simplifications where the code carries more weight than the problem requires.

---

## 1. Confirmed bug: deferring an action silently completes the investigation

**Where:** `src/forge/application/orchestrator.py` — `_submit_decision_locked` (pause handling) + `_advance_one_stage` (`ACTION_CHECKPOINT` → `COMPLETED`).

Choosing **B — Defer action** (or **D — Pause here**) at the action checkpoint clears `pending_decision`, then pauses. On `resume()`, the run loop sees stage `ACTION_CHECKPOINT` with no pending decision and falls through `_advance_one_stage`, which transitions straight to `COMPLETED`. The deferred question is never re-asked, and `selected_action` is retained — so the final record reads as if the action was **accepted**.

Reproduced with the deterministic runner:

```text
after defer:  action_checkpoint paused
after resume: completed active
prompt re-asked? None
selected_action kept? True
```

**Fix options** (either works; the first is smaller):

- Don't clear `pending_decision` when the chosen letter pauses — persist the attempt, keep the prompt, pause. Resume then re-presents the same question.
- Or: in `_run_until_checkpoint_locked`, when the stage is a checkpoint stage and `pending_decision is None`, regenerate the prompt instead of advancing.

Also decide what "defer" means for `selected_action`: if B is not acceptance, completing with the action still attached is misleading regardless of the re-ask fix.

**Test gap:** `tests/integration/test_resume.py` covers evidence-checkpoint pause/resume but has no action-checkpoint case — exactly the path that's broken. Add one.

## 2. Design: the unit of work sacrifices canonical truth for a disposable index

**Where:** `src/forge/persistence/unit_of_work.py`.

`save()` writes canonical Markdown, then the SQLite projection; if the projection fails it **rolls back the canonical record** (deleting it entirely when the record was new). The architecture doc says the projection is "a rebuildable workflow/search projection" — disposable by design. Rolling back the source of truth because the throwaway index hiccuped inverts that priority, and the rollback itself has an unrecoverable window (`PersistenceConsistencyError` when the compensating write also fails).

**Simpler and safer:** keep the canonical save, and on projection failure log it and rebuild the projection from Markdown (the `rebuild()` path already exists and is tested). The whole class shrinks to ~10 lines and `PersistenceConsistencyError` disappears.

## 3. Gap: cost budgets exist in config but nothing enforces them

**Where:** `src/forge/config.py` (`*_max_calls`, `*_max_output_tokens_per_call`) vs. `orchestrator.py`.

The Quick/Standard/Deep call and token ceilings are the project's core cost-control promise, and the orchestrator currently loops over specialists with no call counting at all. Today the fake runner makes this harmless; the moment `SpecialistRunner` is backed by OpenRouter it's an unbounded spend path. This is scheduled in the implementation plan ("Full orchestration, budgets, and recovery") — the review point is sequencing: **enforce budgets in the same change that wires the real gateway into orchestration, not after.** A counter on `InvestigationRecord` plus one check in `_advance_one_stage` is enough for v1.

## 4. Optimization: the statement index can never serve the search query

**Where:** `src/forge/persistence/sqlite.py` — `idx_items_statement` vs. `search()`.

Search uses `statement LIKE '%query%'`, which a B-tree index on `statement` cannot accelerate (leading wildcard). The index is pure write overhead. Either:

- delete the index (one line, right answer today), or
- if search matters soon, switch to SQLite FTS5 — it ships in the stdlib build, and the projection is rebuildable so the migration is just a schema-version bump and `rebuild()`.

## 5. Simplifications

- **`config.py` `_ENVIRONMENT_NAMES`** duplicates every settings field by hand (19 entries, and it already drifted once when `output_dir`/`log_dir` were added). Derive it: `f"FORGE_{field_name.upper()}"` covers every field except `openrouter_api_key` — one special case instead of a parallel dict to maintain.
- **`NonEmptyText` / `OptionalText`** are defined three times (`domain/epistemics.py`, `application/decisions.py`, `persistence/metadata.py`). Define once, import twice.
- **Triple validation per save:** records are frozen models validated at construction, yet `MarkdownInvestigationRepository.save` and `SQLiteProjection.save` each do a full `model_dump` → `model_validate` round-trip, replaying the entire workflow-history validator both times. The re-validation is defensible (`model_copy(update=...)` skips validation), but do it **once** — the orchestrator or unit of work validates after mutation; the stores trust their input. At current record sizes this is cheap, so this is about clarity of responsibility more than speed.
- **`scripts/smoke_openrouter.py`** hand-rolls the atomic-write/fsync/chmod dance that `TraceWriter._write_json_atomically` already implements. Extract a small `write_private_file()` helper and use it in both.
- **Lock acquisition busy-waits** (`orchestrator._investigation_lock`, 10 ms poll loop). `await asyncio.to_thread(fcntl.flock, fd, fcntl.LOCK_EX)` blocks properly with less code. Low stakes for a single-user local tool — take it when you're next in the file.

## 6. Placeholder surfaces to revisit before the UI phases

- **Decision prompt copy** (`orchestrator._decision_prompt`): every description is `"{label} for the next step."` and A is always recommended. Fine for the walking skeleton; not fine once the CLI renders it, since the A–E contract is the product's main interaction. The prompt content should probably live in data, not inline in the orchestrator, once the CLI lands.
- **Persisted-but-unreachable decision states:** invalid `DecisionAttempt`s (with `error`) are never persisted by the orchestrator, yet `markdown._decision_lines` renders them; `DecisionKind.MODE / PAUSE_RESUME / RECOVERY` and the `SOURCE_CONSENT` stage have no producers yet. All planned — just don't let the dead branches accrete tests and rendering logic before their features exist.

## 7. Valuable enhancements (ranked)

1. **A CLI entry point.** The system currently has no user interface at all — the smoke script is the only executable. Typer is already installed; a minimal `forge start / forge resume / forge choose` wired to the orchestrator + unit of work would make every subsequent slice demonstrable end-to-end. This is also the plan's own next milestone.
2. **Budget enforcement** (finding 3) — in the same change that connects real specialists.
3. **CI.** One GitHub Actions workflow: `uv sync`, `ruff check`, `pytest`. The test suite is this project's biggest asset; make it run on every push. ~20 lines.
4. **A README.** The repo has a 23 KB spec and a 28 KB plan but nothing that says what the forge is, how to configure `.env`, or how to run the smoke test. Ten lines fixes onboarding (including your own, three months from now).
5. **`[project.scripts]` entry** for the smoke script (`forge-smoke = ...`) so it's `uv run forge-smoke` instead of a path.
6. **FTS5 search** (finding 4) — only when search becomes a real feature.

## What's already good (keep doing it)

Fail-fast aggregated config errors with secret redaction; timezone-required timestamps with monotonic-clock guards; atomic replace + fsync on every durable write; symlink and path-escape rejection; parameterized SQL with LIKE-escaping; the schema-versioned canonical Markdown block with the projection as a pure derivative; per-investigation file locks; and a test suite that exercises real integration seams (resume, rebuild, crash-ordering) rather than mocks. The Phase 1–2 acceptance criteria in the implementation plan are genuinely met, with the single exception of the defer/resume path in finding 1.
