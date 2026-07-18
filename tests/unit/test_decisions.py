import pytest
from pydantic import ValidationError

from forge.application.decisions import (
    ChoiceLetter,
    DecisionAttempt,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
    depth_mode_prompt,
    local_continuation_prompt,
    normalize_choice,
    pause_resume_prompt,
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


def test_e_records_a_trimmed_custom_answer() -> None:
    prompt = decision_prompt()

    result = submit_decision(prompt, " e ", custom_answer="  Follow the energy constraint.  ")

    assert result.selection is not None
    assert result.selection.letter is ChoiceLetter.E
    assert result.custom_answer == "Follow the energy constraint."
    assert result.error is None


def test_e_without_detail_and_custom_detail_with_other_letters_preserve_prompt() -> None:
    prompt = decision_prompt()

    missing_detail = submit_decision(prompt, "E")
    misplaced_detail = submit_decision(prompt, "A", custom_answer="Something else")

    assert missing_detail.prompt is prompt
    assert missing_detail.selection is None
    assert missing_detail.error == "Option E needs a custom answer."
    assert misplaced_detail.prompt is prompt
    assert misplaced_detail.selection is None
    assert misplaced_detail.error == "Custom input is only available with option E."


def test_decision_attempt_requires_one_valid_prompt_owned_outcome() -> None:
    prompt = decision_prompt()
    foreign_option = DecisionOption(
        letter=ChoiceLetter.A,
        label="Different A",
        description="Not one of this prompt's choices.",
    )

    with pytest.raises(ValidationError, match="exactly one outcome"):
        DecisionAttempt(prompt=prompt)
    with pytest.raises(ValidationError, match="exactly one outcome"):
        DecisionAttempt(prompt=prompt, selection=prompt.options[0], error="Also failed")
    with pytest.raises(ValidationError, match="selection must belong to its prompt"):
        DecisionAttempt(prompt=prompt, selection=foreign_option)


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


def test_prompt_allows_at_most_one_recommended_choice() -> None:
    prompt_data = decision_prompt().model_dump()
    prompt_data["options"][0]["is_recommended"] = False

    unrecommended = DecisionPrompt.model_validate(prompt_data)
    assert not any(option.is_recommended for option in unrecommended.options)

    prompt_data["options"][0]["is_recommended"] = True
    prompt_data["options"][1]["is_recommended"] = True

    with pytest.raises(ValidationError, match="at most one recommended option"):
        DecisionPrompt.model_validate(prompt_data)


def test_mode_and_resume_prompts_preserve_the_ae_contract() -> None:
    mode = depth_mode_prompt(default_depth="standard")
    resume = pause_resume_prompt(investigation_id="inv_resume")
    continuation = local_continuation_prompt(investigation_id="inv_resume")

    assert mode.kind is DecisionKind.MODE
    assert [option.letter for option in mode.options] == list(ChoiceLetter)
    assert mode.options[1].is_recommended is True
    assert resume.kind is DecisionKind.PAUSE_RESUME
    assert resume.options[0].is_recommended is True
    assert [option.letter for option in continuation.options] == list(ChoiceLetter)
    assert continuation.options[0].label == "Continue live with configured models"
    assert continuation.options[1].label == "Continue locally without model calls"
