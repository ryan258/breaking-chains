import pytest

from forge.application.budgets import (
    BudgetExceeded,
    BudgetPolicy,
    DepthBudget,
    live_run_confirmation_prompt,
)
from forge.application.decisions import ChoiceLetter, DecisionKind
from forge.domain.investigation import DepthMode


def policy() -> BudgetPolicy:
    return BudgetPolicy(
        quick=DepthBudget(max_calls=6, max_output_tokens_per_call=1200),
        standard=DepthBudget(max_calls=10, max_output_tokens_per_call=2400),
        deep=DepthBudget(max_calls=24, max_output_tokens_per_call=4800),
    )


@pytest.mark.parametrize(
    ("depth", "expected_calls", "expected_tokens"),
    [
        (DepthMode.QUICK, 6, 1200),
        (DepthMode.STANDARD, 10, 2400),
        (DepthMode.DEEP, 24, 4800),
    ],
)
def test_depth_policy_returns_the_configured_hard_limits(
    depth: DepthMode,
    expected_calls: int,
    expected_tokens: int,
) -> None:
    budget = policy().for_depth(depth)

    assert budget.max_calls == expected_calls
    assert budget.max_output_tokens_per_call == expected_tokens


def test_budget_rejects_calls_at_limit_and_oversized_output_requests() -> None:
    budget = policy().for_depth(DepthMode.QUICK)

    budget.assert_call_allowed(calls_used=5, requested_output_tokens=1200)
    with pytest.raises(BudgetExceeded, match="call limit"):
        budget.assert_call_allowed(calls_used=6, requested_output_tokens=1200)
    with pytest.raises(BudgetExceeded, match="output-token limit"):
        budget.assert_call_allowed(calls_used=0, requested_output_tokens=1201)


@pytest.mark.parametrize(
    ("source_attached", "source_summary"),
    [
        (False, "No local source is attached"),
        (True, "A local source is attached but is not approved yet"),
    ],
)
def test_live_confirmation_is_one_ae_question_with_visible_cost_and_privacy_bounds(
    source_attached: bool,
    source_summary: str,
) -> None:
    prompt = live_run_confirmation_prompt(
        investigation_id="inv_live_confirmation",
        depth=DepthMode.STANDARD,
        budget=policy().for_depth(DepthMode.STANDARD),
        source_attached=source_attached,
    )

    assert prompt.kind is DecisionKind.LIVE_CONFIRMATION
    assert tuple(option.letter for option in prompt.options) == tuple(ChoiceLetter)
    assert prompt.options[0].is_recommended is True
    assert prompt.options[-1].accepts_custom_input is True
    assert "Standard" in prompt.question
    assert "10 model calls" in prompt.question
    assert "2,400 output tokens per call" in prompt.question
    assert source_summary in prompt.question


def test_resume_confirmation_explicitly_says_continue() -> None:
    prompt = live_run_confirmation_prompt(
        investigation_id="inv_live_confirmation",
        depth=DepthMode.QUICK,
        budget=policy().for_depth(DepthMode.QUICK),
        source_attached=False,
        resuming=True,
    )

    assert prompt.question.startswith("Continue a live Quick investigation")
