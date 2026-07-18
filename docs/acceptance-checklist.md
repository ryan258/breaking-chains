# Version-one acceptance checklist

This checklist maps each numbered success criterion in `docs/spec.md` to executable evidence. A
criterion is marked automated only when the cited test or verification command fails if the claimed
behavior regresses. Optional paid checks are separated from the no-credential gate.

| # | Criterion | Evidence | Review type |
| ---: | --- | --- | --- |
| 1 | A fresh clone prepares with `uv sync` and `.env.example`. | `uv sync`; `tests/unit/test_config.py`; README Quick start | Automated + operator review |
| 2 | `forge config-check` aggregates missing settings without secrets. | `tests/e2e/test_cli.py::test_config_check_reports_missing_settings_without_secrets`; `tests/unit/test_config.py` | Automated |
| 3 | CLI investigations complete and resume through single-letter choices. | `tests/e2e/test_cli.py::test_quick_investigation_completes_with_single_letter_choices`; `::test_deferred_action_pauses_and_resume_reasks_the_question` | Automated |
| 4 | Streamlit completes the same A-E workflow. | `tests/e2e/test_streamlit.py::test_streamlit_completes_deterministic_investigation_with_ae_controls` | Automated |
| 5 | Questions, observations, local text/Markdown, and prior investigations can seed work. | `tests/e2e/test_cli.py::test_local_source_requires_consent_and_can_stay_local`; `::test_prior_investigation_can_seed_a_traceable_follow_up`; seed coverage in `tests/e2e/test_acceptance.py` | Automated |
| 6 | Quick, Standard, and Deep visibly enforce bounded budgets. | `tests/unit/test_budgets.py`; `tests/integration/test_real_specialist_runner.py`; live-confirmation assertions in CLI and Streamlit e2e tests | Automated |
| 7 | Focus, evidence, and action checkpoints cannot be bypassed. | `tests/e2e/test_acceptance.py`; `tests/integration/test_orchestration_walking_skeleton.py` | Automated |
| 8 | Claims remain traceable or visibly labeled by epistemic category. | `tests/unit/test_epistemics.py`; role contract tests; `tests/integration/test_markdown_repository.py` | Automated |
| 9 | Every hypothesis receives a skeptical disposition. | `tests/contract/test_skeptic_role.py`; `tests/e2e/test_acceptance.py` | Automated |
| 10 | Tests/actions include expected and disconfirming observations or a responsible no-test reason. | `tests/contract/test_experiment_role.py`; `tests/e2e/test_acceptance.py` | Automated |
| 11 | Paused and failed work resumes without repeating completed calls. | `tests/integration/test_resume.py`; `tests/integration/test_real_specialist_runner.py::test_live_failure_persists_receipt_and_retries_from_an_ae_recovery_prompt` | Automated |
| 12 | Markdown is readable and SQLite can locate epistemic content. | `tests/integration/test_markdown_repository.py`; `tests/integration/test_sqlite_projection.py`; `tests/e2e/test_acceptance.py` | Automated |
| 13 | SQLite rebuild from Markdown preserves content and relationships. | `tests/integration/test_rebuild_index.py`; `tests/e2e/test_cli.py::test_rebuild_index_command_restores_projection_from_markdown` | Automated |
| 14 | Automated tests need no live credential; live checks are separate. | `tests/e2e/test_acceptance.py`; `scripts/verify_acceptance.py`; optional `scripts/smoke_openrouter.py` | Automated; paid smoke optional |
| 15 | No general web search exists and secrets stay out of artifacts/errors. | source scan in `scripts/verify_acceptance.py`; `tests/unit/test_trace.py`; `tests/unit/test_config.py`; `tests/contract/test_openrouter.py` | Automated |
| 16 | Local source bytes require explicit transmission consent. | `tests/integration/test_source_consent.py`; `tests/integration/test_source_isolation.py`; `tests/e2e/test_cli.py::test_local_source_requires_consent_and_can_stay_local` | Automated |
| 17 | Mode, consent, checkpoints, pause/resume, and recovery use A-E. | `tests/unit/test_decisions.py`; recorded decision kinds in `tests/e2e/test_acceptance.py`; Streamlit A-E tests | Automated |
| 18 | Browser checks prove target size, names, keyboard order/activation, and visible focus. | `tests/e2e/test_streamlit_accessibility.py` at 320, 768, 1024, and 1440 CSS pixels | Automated + human physical review |

## Human acceptance still required

- Complete the keyboard-only start, consent, checkpoint, custom E, pause/resume, and recovery paths
  with the user's actual assistive setup.
- Confirm the terminal and Streamlit experiences are physically comfortable for sustained use.
- Run the optional paid smoke only after reviewing its one-call, 500-output-token bound and the
  intended OpenRouter model in `.env`.
