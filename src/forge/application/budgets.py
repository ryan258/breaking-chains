"""Hard depth budgets and the explicit live-execution confirmation contract."""

from dataclasses import dataclass

from forge.application.decisions import (
    ChoiceLetter,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
)
from forge.domain.investigation import DepthMode


class BudgetExceeded(RuntimeError):
    """A model call would exceed an approved hard budget."""


@dataclass(frozen=True, slots=True)
class DepthBudget:
    """Hard call-count and per-call output-token limits for one depth mode."""

    max_calls: int
    max_output_tokens_per_call: int

    def __post_init__(self) -> None:
        if self.max_calls < 1 or self.max_output_tokens_per_call < 1:
            raise ValueError("depth budget limits must be positive")

    def assert_call_allowed(self, *, calls_used: int, requested_output_tokens: int) -> None:
        """Reject work before a provider call can cross either hard limit."""

        if calls_used < 0:
            raise ValueError("calls_used cannot be negative")
        if calls_used >= self.max_calls:
            raise BudgetExceeded("investigation model-call limit has been reached")
        if not 1 <= requested_output_tokens <= self.max_output_tokens_per_call:
            raise BudgetExceeded("requested output-token limit exceeds the approved depth budget")


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    """Configured immutable budgets for every supported depth mode."""

    quick: DepthBudget
    standard: DepthBudget
    deep: DepthBudget

    def for_depth(self, depth: DepthMode) -> DepthBudget:
        return {
            DepthMode.QUICK: self.quick,
            DepthMode.STANDARD: self.standard,
            DepthMode.DEEP: self.deep,
        }[depth]


def live_run_confirmation_prompt(
    *,
    investigation_id: str,
    depth: DepthMode,
    budget: DepthBudget,
    source_attached: bool,
    resuming: bool = False,
) -> DecisionPrompt:
    """Present cost and source boundaries before any live provider work starts."""

    source_summary = (
        "A local source is attached but is not approved yet; a separate consent question "
        "will control whether its content may leave the machine."
        if source_attached
        else "No local source is attached, so no local source content may leave the machine."
    )
    action = "Continue" if resuming else "Start"
    question = (
        f"{action} a live {depth.value.title()} investigation with at most "
        f"{budget.max_calls} model calls and {budget.max_output_tokens_per_call:,} output tokens "
        f"per call? {source_summary}"
    )
    return DecisionPrompt(
        id=f"{investigation_id}-live-confirmation-v1",
        kind=DecisionKind.LIVE_CONFIRMATION,
        question=question,
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Approve live execution",
                description="Begin only within the displayed hard limits.",
                is_recommended=True,
            ),
            DecisionOption(
                letter=ChoiceLetter.B,
                label="Stop before starting",
                description="Make no provider calls and create no investigation.",
            ),
            DecisionOption(
                letter=ChoiceLetter.C,
                label="Review configuration",
                description="Stop so model assignments or limits can be reviewed.",
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Stop without resuming" if resuming else "Use deterministic preview",
                description=(
                    "Leave the saved investigation unchanged."
                    if resuming
                    else "Run the local fake specialists without provider calls."
                ),
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description=(
                    "Add only as much detail as desired; no live call starts automatically."
                ),
                accepts_custom_input=True,
            ),
        ),
    )


__all__ = [
    "BudgetExceeded",
    "BudgetPolicy",
    "DepthBudget",
    "live_run_confirmation_prompt",
]
