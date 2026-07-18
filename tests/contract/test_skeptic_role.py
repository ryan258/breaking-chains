from datetime import UTC, datetime

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from forge.domain.epistemics import Confidence, ConfidenceLevel, ExploratoryItem, ExploratoryType
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import ModelRole
from forge.persistence.metadata import InvestigationRecord
from forge.roles.skeptic import (
    SKEPTIC_PROMPT_VERSION,
    build_skeptic_request,
    parse_skeptic_output,
)


def record() -> InvestigationRecord:
    hypothesis = ExploratoryItem(
        id="epi_variance_hypothesis",
        statement="Reducing arrival variance delays saturation.",
        uncertainty=Confidence(
            level=ConfidenceLevel.LOW,
            rationale="The causal structure has not been tested.",
        ),
        provenance={"origin": "Synthesizer"},
        exploratory_type=ExploratoryType.HYPOTHESIS,
    )
    return InvestigationRecord(
        id="inv_skeptic_contract",
        seed="Does variance drive saturation?",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.STANDARD,
            at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        ),
        epistemic_items=(hypothesis,),
    )


def payload(disposition: str = "revise") -> dict[str, object]:
    return {
        "challenges": [
            {
                "target_id": "epi_variance_hypothesis",
                "challenge": "Capacity may explain the same saturation pattern.",
                "disposition": disposition,
                "rationale": "The current observations do not isolate variance.",
            }
        ]
    }


@pytest.mark.parametrize("disposition", ["retain", "revise", "reject"])
def test_skeptic_assigns_every_allowed_disposition(disposition: str) -> None:
    output = parse_skeptic_output(payload(disposition), record=record())

    assert output.challenges[0].disposition.value == disposition


def test_skeptic_rejects_output_that_omits_a_hypothesis() -> None:
    with pytest.raises(ValueError, match="exactly one disposition"):
        parse_skeptic_output({"challenges": []}, record=record())


def test_skeptic_request_is_versioned_and_contradiction_seeking() -> None:
    request = build_skeptic_request(
        record(),
        model="vendor/skeptic-model",
        call_id="call_skeptic_contract",
        max_output_tokens=1200,
    )

    assert request.role is ModelRole.SKEPTIC
    assert request.prompt_contract_version == SKEPTIC_PROMPT_VERSION
    assert "counterexample" in request.messages[0].content.lower()


def test_skeptic_schema_limits_challenges_to_every_hypothesis() -> None:
    request = build_skeptic_request(
        record(),
        model="vendor/skeptic-model",
        call_id="call_skeptic_contract",
        max_output_tokens=1200,
    )
    validator = Draft202012Validator(request.output_schema)
    validator.validate(payload())

    invalid_target = payload()
    invalid_target["challenges"][0]["target_id"] = "epi_not_a_hypothesis"
    with pytest.raises(JsonSchemaValidationError):
        validator.validate(invalid_target)
    with pytest.raises(JsonSchemaValidationError):
        validator.validate({"challenges": []})
