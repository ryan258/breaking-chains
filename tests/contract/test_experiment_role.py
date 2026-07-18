from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.domain.epistemics import Confidence, ConfidenceLevel, ExploratoryItem, ExploratoryType
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import ModelRole
from forge.persistence.metadata import InvestigationRecord
from forge.roles.experiment_designer import (
    EXPERIMENT_PROMPT_VERSION,
    build_experiment_request,
    parse_experiment_output,
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
        id="inv_experiment_contract",
        seed="How can the variance hypothesis be tested?",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.STANDARD,
            at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        ),
        epistemic_items=(hypothesis,),
    )


def proposal_payload() -> dict[str, object]:
    return {
        "proposal": {
            "statement": (
                "Compare two simulated queues with equal mean load and different variance."
            ),
            "procedure": "Run each queue for 1000 arrivals using the same capacity.",
            "expected_observation": "The lower-variance queue saturates later.",
            "disconfirming_observation": "Both queues saturate at the same point.",
            "cost": "Two bounded simulations.",
            "risk": "Simulation assumptions may not transfer to physical systems.",
            "stopping_condition": "Stop after three seeds produce a stable direction.",
            "reproducibility_needs": "Record code, parameters, random seeds, and outputs.",
        },
        "no_responsible_test_reason": None,
    }


def test_experiment_proposal_requires_falsifier_and_reproducibility_details() -> None:
    output = parse_experiment_output(proposal_payload())

    assert output.proposal is not None
    assert output.proposal.disconfirming_observation
    assert output.proposal.reproducibility_needs


def test_experiment_output_can_explain_why_no_responsible_test_exists() -> None:
    output = parse_experiment_output(
        {
            "proposal": None,
            "no_responsible_test_reason": "Testing would expose participants to unjustified harm.",
        }
    )

    assert output.proposal is None
    assert "harm" in output.no_responsible_test_reason


def test_experiment_output_rejects_missing_action_and_reason() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        parse_experiment_output({"proposal": None, "no_responsible_test_reason": None})


def test_experiment_request_is_versioned() -> None:
    request = build_experiment_request(
        record(),
        model="vendor/experiment-model",
        call_id="call_experiment_contract",
        max_output_tokens=1200,
    )

    assert request.role is ModelRole.EXPERIMENT_DESIGNER
    assert request.prompt_contract_version == EXPERIMENT_PROMPT_VERSION
    assert "smallest informative" in request.messages[0].content.lower()
