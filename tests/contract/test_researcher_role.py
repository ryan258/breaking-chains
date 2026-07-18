from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.domain.epistemics import DerivedClaim, Evidence, Premise
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import ModelRole
from forge.persistence.metadata import InvestigationRecord
from forge.roles.researcher import (
    RESEARCHER_PROMPT_VERSION,
    build_researcher_request,
    parse_researcher_output,
)


def record() -> InvestigationRecord:
    return InvestigationRecord(
        id="inv_researcher_contract",
        seed="A sample weighed 2.4 kilograms on a calibrated scale.",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.QUICK,
            at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        ),
    )


def valid_output() -> dict[str, object]:
    confidence = {"level": "medium", "rationale": "The setup needs independent review."}
    return {
        "epistemic_items": [
            {
                "id": "epi_scale_calibrated",
                "category": "premise",
                "statement": "The scale calibration is valid.",
                "uncertainty": confidence,
                "origin": "User-described setup",
            },
            {
                "id": "epi_mass_measurement",
                "category": "evidence",
                "statement": "The sample measured 2.4 kilograms.",
                "uncertainty": confidence,
                "provenance": {"origin": "User observation"},
                "details": {
                    "evidence_type": "measurement",
                    "method": "Calibrated scale",
                    "unit": "kilogram",
                    "conditions": "Single indoor reading",
                },
            },
            {
                "id": "epi_sample_nonzero_mass",
                "category": "derived_claim",
                "statement": "The sample has nonzero mass.",
                "uncertainty": confidence,
                "provenance": {"origin": "Researcher deduction"},
                "dependencies": ["epi_scale_calibrated", "epi_mass_measurement"],
                "derivation": "A valid positive mass measurement implies nonzero mass.",
            },
        ],
        "unsupported_assumptions": ["The indoor conditions did not bias the reading."],
    }


def test_researcher_output_preserves_epistemic_categories_and_assumptions() -> None:
    output = parse_researcher_output(valid_output(), record=record())

    assert isinstance(output.epistemic_items[0], Premise)
    assert isinstance(output.epistemic_items[1], Evidence)
    assert isinstance(output.epistemic_items[2], DerivedClaim)
    assert output.unsupported_assumptions == ("The indoor conditions did not bias the reading.",)


def test_researcher_rejects_dangling_derived_claim_dependencies() -> None:
    payload = valid_output()
    payload["epistemic_items"][2]["dependencies"] = ["epi_missing_evidence"]

    with pytest.raises(ValidationError, match="unknown local epistemic item"):
        parse_researcher_output(payload, record=record())


def test_researcher_schema_rejects_exploratory_items_as_evidence() -> None:
    payload = valid_output()
    payload["epistemic_items"][1] = {
        "id": "epi_guess",
        "category": "exploratory_item",
        "statement": "The sample may be unusually dense.",
        "uncertainty": {"level": "low", "rationale": "This is only a guess."},
        "provenance": {"origin": "Model suggestion"},
        "exploratory_type": "speculation",
    }

    with pytest.raises(ValidationError):
        parse_researcher_output(payload, record=record())


def test_researcher_request_is_versioned_and_requires_unsupported_assumptions() -> None:
    request = build_researcher_request(
        record(),
        model="vendor/researcher-model",
        call_id="call_researcher_contract",
        max_output_tokens=1200,
    )

    assert request.role is ModelRole.RESEARCHER
    assert request.prompt_contract_version == RESEARCHER_PROMPT_VERSION
    assert request.output_schema_name == "researcher_epistemics_v1"
    assert "unsupported assumptions" in request.messages[0].content.lower()
