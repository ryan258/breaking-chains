from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.domain.epistemics import Confidence, ConfidenceLevel, Premise
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import ModelRole
from forge.persistence.metadata import InvestigationRecord
from forge.roles.connection_finder import (
    CONNECTION_PROMPT_VERSION,
    build_connection_request,
    parse_connection_output,
)


def record() -> InvestigationRecord:
    premise = Premise(
        id="epi_binding_constraint",
        statement="The system has a binding resource constraint.",
        uncertainty=Confidence(level=ConfidenceLevel.MEDIUM, rationale="User premise."),
        origin="User",
    )
    return InvestigationRecord(
        id="inv_connection_contract",
        seed="What shares this constraint pattern?",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.STANDARD,
            at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        ),
        epistemic_items=(premise,),
    )


def connection_payload() -> dict[str, object]:
    return {
        "connections": [
            {
                "id": "epi_queue_connection",
                "category": "exploratory_item",
                "statement": "Queues and supply chains may share saturation behavior.",
                "uncertainty": {
                    "level": "medium",
                    "rationale": "The constraint structures appear similar but causality differs.",
                },
                "provenance": {"origin": "Connection Finder"},
                "exploratory_type": "connection",
                "based_on": ["epi_binding_constraint"],
            }
        ]
    }


def test_connection_output_stays_exploratory_and_names_its_basis() -> None:
    output = parse_connection_output(connection_payload(), record=record())

    assert output.connections[0].exploratory_type.value == "connection"
    assert output.connections[0].based_on == ("epi_binding_constraint",)


def test_connection_output_rejects_analogy_presented_as_evidence() -> None:
    payload = connection_payload()
    payload["connections"][0]["category"] = "evidence"

    with pytest.raises(ValidationError):
        parse_connection_output(payload, record=record())


def test_connection_request_is_versioned() -> None:
    request = build_connection_request(
        record(),
        model="vendor/connection-model",
        call_id="call_connection_contract",
        max_output_tokens=1200,
    )

    assert request.role is ModelRole.CONNECTION_FINDER
    assert request.prompt_contract_version == CONNECTION_PROMPT_VERSION
    assert "analogy is not evidence" in request.messages[0].content.lower()


def test_connection_request_schema_requires_traceable_connection_fields() -> None:
    request = build_connection_request(
        record(),
        model="vendor/connection-model",
        call_id="call_connection_schema",
        max_output_tokens=1200,
    )

    proposal = request.output_schema["$defs"]["ConnectionProposal"]

    assert proposal["properties"]["exploratory_type"]["const"] == "connection"
    assert proposal["properties"]["based_on"]["minItems"] == 1
