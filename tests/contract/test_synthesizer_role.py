from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.domain.epistemics import Confidence, ConfidenceLevel, ExploratoryItem, ExploratoryType
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import ModelRole
from forge.persistence.metadata import InvestigationRecord
from forge.roles.synthesizer import (
    SYNTHESIZER_PROMPT_VERSION,
    build_synthesizer_request,
    parse_synthesizer_output,
)


def record() -> InvestigationRecord:
    connection = ExploratoryItem(
        id="epi_queue_connection",
        statement="Queues and supply chains may share saturation behavior.",
        uncertainty=Confidence(
            level=ConfidenceLevel.MEDIUM,
            rationale="The structural analogy is plausible but unproven.",
        ),
        provenance={"origin": "Connection Finder"},
        exploratory_type=ExploratoryType.CONNECTION,
    )
    return InvestigationRecord(
        id="inv_synthesizer_contract",
        seed="What follows from the saturation analogy?",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.STANDARD,
            at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        ),
        epistemic_items=(connection,),
    )


def payload() -> dict[str, object]:
    confidence = {
        "level": "low",
        "rationale": "The available evidence does not distinguish the explanations.",
    }
    return {
        "hypotheses": [
            {
                "id": "epi_saturation_hypothesis",
                "category": "exploratory_item",
                "statement": "Reducing arrival variance may delay saturation.",
                "uncertainty": confidence,
                "provenance": {"origin": "Synthesizer"},
                "exploratory_type": "hypothesis",
                "based_on": ["epi_queue_connection"],
            }
        ],
        "alternative_explanations": [
            {
                "id": "epi_capacity_alternative",
                "category": "exploratory_item",
                "statement": "Absolute capacity rather than variance may dominate.",
                "uncertainty": confidence,
                "provenance": {"origin": "Synthesizer"},
                "exploratory_type": "interpretation",
                "based_on": ["epi_queue_connection"],
            }
        ],
    }


def test_synthesizer_preserves_hypotheses_and_competing_explanations() -> None:
    output = parse_synthesizer_output(payload(), record=record())

    assert output.hypotheses[0].exploratory_type is ExploratoryType.HYPOTHESIS
    assert output.alternative_explanations[0].exploratory_type is ExploratoryType.INTERPRETATION


def test_synthesizer_rejects_hypothesis_without_a_local_basis() -> None:
    output = payload()
    output["hypotheses"][0]["based_on"] = ["epi_missing_basis"]

    with pytest.raises(ValidationError, match="unknown local epistemic item"):
        parse_synthesizer_output(output, record=record())


def test_synthesizer_request_is_versioned() -> None:
    request = build_synthesizer_request(
        record(),
        model="vendor/synthesizer-model",
        call_id="call_synthesizer_contract",
        max_output_tokens=1600,
    )

    assert request.role is ModelRole.SYNTHESIZER
    assert request.prompt_contract_version == SYNTHESIZER_PROMPT_VERSION
    assert "competing explanations" in request.messages[0].content.lower()
