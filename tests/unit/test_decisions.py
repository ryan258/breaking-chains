import pytest
from pydantic import ValidationError

from forge.application.decisions import (
    ChoiceLetter,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
    normalize_choice,
    submit_decision,
)


def decision_prompt(kind: DecisionKind = DecisionKind.MODE) -> DecisionPrompt:
    return DecisionPrompt(
        id="choose-depth",
        kind=kind,
        question="How deeply should we investigate?",
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Standard",
                description="Balanced depth and speed.",
                is_recommended=True,
            ),
            DecisionOption(letter=ChoiceLetter.B, label="Quick", description="Fast triage."),
            DecisionOption(letter=ChoiceLetter.C, label="Deep", description="Broader analysis."),
            DecisionOption(letter=ChoiceLetter.D, label="Pause", description="Decide later."),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add only as much detail as you want.",
                accepts_custom_input=True,
            ),
        ),
    )


@pytest.mark.parametrize("raw", ["a", " A ", "\ta\n"])
def test_normalize_choice_accepts_case_and_surrounding_whitespace(raw: str) -> None:
    assert normalize_choice(raw) is ChoiceLetter.A


@pytest.mark.parametrize("raw", ["", "F", "AA", "A please"])
def test_invalid_input_preserves_the_active_question(raw: str) -> None:
    prompt = decision_prompt()

    result = submit_decision(prompt, raw)

    assert result.prompt is prompt
    assert result.selection is None
    assert result.error == "Choose A, B, C, D, or E."


def test_valid_input_returns_the_matching_option() -> None:
    prompt = decision_prompt()

    result = submit_decision(prompt, " b ")

    assert result.prompt is prompt
    assert result.selection is not None
    assert result.selection.letter is ChoiceLetter.B
    assert result.error is None


def test_every_required_decision_kind_uses_the_same_a_to_e_contract() -> None:
    required_kinds = {
        DecisionKind.MODE,
        DecisionKind.SOURCE_CONSENT,
        DecisionKind.FOCUS_CHECKPOINT,
        DecisionKind.EVIDENCE_CHECKPOINT,
        DecisionKind.ACTION_CHECKPOINT,
        DecisionKind.PAUSE_RESUME,
        DecisionKind.RECOVERY,
    }

    for kind in required_kinds:
        prompt = decision_prompt(kind)
        assert prompt.kind is kind
        assert tuple(option.letter for option in prompt.options) == tuple(ChoiceLetter)


def test_prompt_rejects_missing_or_reordered_letters() -> None:
    prompt_data = decision_prompt().model_dump()
    prompt_data["options"] = tuple(reversed(prompt_data["options"]))

    with pytest.raises(ValidationError, match="exactly A, B, C, D, and E in order"):
        DecisionPrompt.model_validate(prompt_data)


def test_only_e_can_accept_custom_input_and_e_must_accept_it() -> None:
    prompt_data = decision_prompt().model_dump()
    prompt_data["options"][0]["accepts_custom_input"] = True

    with pytest.raises(ValidationError, match="only option E"):
        DecisionPrompt.model_validate(prompt_data)

    prompt_data = decision_prompt().model_dump()
    prompt_data["options"][-1]["accepts_custom_input"] = False

    with pytest.raises(ValidationError, match="option E must accept custom input"):
        DecisionPrompt.model_validate(prompt_data)


def test_prompt_requires_one_recommended_choice() -> None:
    prompt_data = decision_prompt().model_dump()
    prompt_data["options"][0]["is_recommended"] = False

    with pytest.raises(ValidationError, match="exactly one recommended option"):
        DecisionPrompt.model_validate(prompt_data)
