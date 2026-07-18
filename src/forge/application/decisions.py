"""Shared A-E decision contract for every user interface."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.domain.epistemics import NonEmptyText, OptionalText


class DecisionModel(BaseModel):
    """Immutable decision value validated at construction boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ChoiceLetter(StrEnum):
    """The complete low-effort input alphabet."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class DecisionKind(StrEnum):
    """Every workflow decision that must use the A-E contract."""

    MODE = "mode"
    LIVE_CONFIRMATION = "live_confirmation"
    BUDGET_EXHAUSTED = "budget_exhausted"
    SOURCE_CONSENT = "source_consent"
    FOCUS_CHECKPOINT = "focus_checkpoint"
    EVIDENCE_CHECKPOINT = "evidence_checkpoint"
    ACTION_CHECKPOINT = "action_checkpoint"
    PAUSE_RESUME = "pause_resume"
    RECOVERY = "recovery"


class DecisionOption(DecisionModel):
    """One accessible lettered response."""

    letter: ChoiceLetter
    label: NonEmptyText
    description: NonEmptyText
    is_recommended: bool = False
    accepts_custom_input: bool = False


class DecisionPrompt(DecisionModel):
    """One focused question with an invariant A-E option set."""

    id: NonEmptyText
    kind: DecisionKind
    question: NonEmptyText
    options: tuple[DecisionOption, ...] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_option_contract(self) -> "DecisionPrompt":
        if tuple(option.letter for option in self.options) != tuple(ChoiceLetter):
            raise ValueError("decision options must be exactly A, B, C, D, and E in order")
        if any(option.accepts_custom_input for option in self.options[:-1]):
            raise ValueError("only option E may accept custom input")
        if not self.options[-1].accepts_custom_input:
            raise ValueError("option E must accept custom input")
        if sum(option.is_recommended for option in self.options) > 1:
            raise ValueError("a decision may have at most one recommended option")
        return self


class DecisionAttempt(DecisionModel):
    """A selection result that retains its active prompt on every outcome."""

    prompt: DecisionPrompt
    selection: DecisionOption | None = None
    custom_answer: OptionalText = None
    error: OptionalText = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "DecisionAttempt":
        if (self.selection is None) == (self.error is None):
            raise ValueError("a decision attempt must contain exactly one outcome")
        if self.selection is None:
            if self.custom_answer is not None:
                raise ValueError("a failed decision attempt cannot contain a custom answer")
            return self
        if self.selection not in self.prompt.options:
            raise ValueError("a decision selection must belong to its prompt")
        if self.selection.letter is ChoiceLetter.E and self.custom_answer is None:
            raise ValueError("an E selection must include a custom answer")
        if self.selection.letter is not ChoiceLetter.E and self.custom_answer is not None:
            raise ValueError("custom input is only available with option E")
        return self


def normalize_choice(raw: str) -> ChoiceLetter:
    """Normalize case and surrounding whitespace into one A-E letter."""

    return ChoiceLetter(raw.strip().upper())


def submit_decision(
    prompt: DecisionPrompt,
    raw: str,
    *,
    custom_answer: str | None = None,
) -> DecisionAttempt:
    """Apply input without replacing or discarding the active question."""

    try:
        letter = normalize_choice(raw)
    except ValueError:
        return DecisionAttempt(prompt=prompt, error="Choose A, B, C, D, or E.")

    selection = next(option for option in prompt.options if option.letter is letter)
    normalized_custom = custom_answer.strip() if custom_answer is not None else None
    normalized_custom = normalized_custom or None
    if letter is ChoiceLetter.E and normalized_custom is None:
        return DecisionAttempt(prompt=prompt, error="Option E needs a custom answer.")
    if letter is not ChoiceLetter.E and normalized_custom is not None:
        return DecisionAttempt(
            prompt=prompt,
            error="Custom input is only available with option E.",
        )
    return DecisionAttempt(
        prompt=prompt,
        selection=selection,
        custom_answer=normalized_custom,
    )


def depth_mode_prompt(*, default_depth: str) -> DecisionPrompt:
    """Offer low-effort depth selection before an interactive investigation starts."""

    modes = ((ChoiceLetter.A, "Quick"), (ChoiceLetter.B, "Standard"), (ChoiceLetter.C, "Deep"))
    return DecisionPrompt(
        id="new-investigation-mode-v1",
        kind=DecisionKind.MODE,
        question="How deep should this investigation go?",
        options=(
            *(
                DecisionOption(
                    letter=letter,
                    label=label,
                    description=f"Use the configured {label.lower()} call and token limits.",
                    is_recommended=label.lower() == default_depth,
                )
                for letter, label in modes
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Stop before starting",
                description="Return without creating an investigation.",
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Name Quick, Standard, or Deep and add any desired detail.",
                accepts_custom_input=True,
            ),
        ),
    )


def pause_resume_prompt(*, investigation_id: str) -> DecisionPrompt:
    """Require an A-E choice before a deterministic saved run resumes."""

    return DecisionPrompt(
        id=f"{investigation_id}-pause-resume-v1",
        kind=DecisionKind.PAUSE_RESUME,
        question="Resume this saved investigation?",
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Resume from saved work",
                description="Continue from the first unfinished stage.",
                is_recommended=True,
            ),
            DecisionOption(
                letter=ChoiceLetter.B,
                label="Keep paused",
                description="Leave the canonical record unchanged.",
            ),
            DecisionOption(
                letter=ChoiceLetter.C,
                label="Review saved record",
                description="Stop so the Markdown record can be reviewed first.",
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Return without resuming",
                description="Make no workflow changes.",
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add detail without resuming automatically.",
                accepts_custom_input=True,
            ),
        ),
    )


def local_continuation_prompt(*, investigation_id: str) -> DecisionPrompt:
    """Offer a visible no-provider path for paused, unfinished work."""

    return DecisionPrompt(
        id=f"{investigation_id}-local-continuation-v1",
        kind=DecisionKind.PAUSE_RESUME,
        question="This investigation is paused before completion. How should it proceed?",
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Continue live with configured models",
                description="Request a fresh bounded live batch from the saved stage.",
                is_recommended=True,
            ),
            DecisionOption(
                letter=ChoiceLetter.B,
                label="Continue locally without model calls",
                description="Use deterministic local specialists from the saved stage.",
            ),
            DecisionOption(
                letter=ChoiceLetter.C,
                label="Keep paused",
                description="Leave the saved investigation unchanged.",
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Return to saved records",
                description="Return without changing the investigation.",
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add only as much detail as desired and remain paused.",
                accepts_custom_input=True,
            ),
        ),
    )


__all__ = [
    "ChoiceLetter",
    "DecisionAttempt",
    "DecisionKind",
    "DecisionOption",
    "DecisionPrompt",
    "depth_mode_prompt",
    "local_continuation_prompt",
    "normalize_choice",
    "pause_resume_prompt",
    "submit_decision",
]
