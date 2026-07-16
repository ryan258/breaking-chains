"""Shared A-E decision contract for every user interface."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
        if sum(option.is_recommended for option in self.options) != 1:
            raise ValueError("a decision must have exactly one recommended option")
        return self


class DecisionAttempt(DecisionModel):
    """A selection result that retains its active prompt on every outcome."""

    prompt: DecisionPrompt
    selection: DecisionOption | None = None
    error: str | None = None


def normalize_choice(raw: str) -> ChoiceLetter:
    """Normalize case and surrounding whitespace into one A-E letter."""

    return ChoiceLetter(raw.strip().upper())


def submit_decision(prompt: DecisionPrompt, raw: str) -> DecisionAttempt:
    """Apply input without replacing or discarding the active question."""

    try:
        letter = normalize_choice(raw)
    except ValueError:
        return DecisionAttempt(prompt=prompt, error="Choose A, B, C, D, or E.")

    selection = next(option for option in prompt.options if option.letter is letter)
    return DecisionAttempt(prompt=prompt, selection=selection)


__all__ = [
    "ChoiceLetter",
    "DecisionAttempt",
    "DecisionKind",
    "DecisionOption",
    "DecisionPrompt",
    "normalize_choice",
    "submit_decision",
]
