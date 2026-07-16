from pydantic import ValidationError

from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    Evidence,
    MeasurementDetails,
    Premise,
    Provenance,
    new_epistemic_item_id,
    parse_epistemic_item,
)


def medium_confidence() -> Confidence:
    return Confidence(level=ConfidenceLevel.MEDIUM, rationale="Plausible but not yet tested.")


def test_generates_unique_stable_epistemic_item_identifiers() -> None:
    first = new_epistemic_item_id()
    second = new_epistemic_item_id()

    assert first.startswith("epi_")
    assert second.startswith("epi_")
    assert first != second


def test_premise_stays_distinct_from_evidence_at_high_confidence() -> None:
    premise = Premise(
        id="epi_gravity_assumption",
        statement="  Objects with mass attract one another.  ",
        uncertainty=Confidence(
            level=ConfidenceLevel.HIGH,
            rationale="Repeated direct measurement supports adopting this premise.",
        ),
        origin="Adopted for this investigation.",
    )

    assert premise.category == "premise"
    assert premise.statement == "Objects with mass attract one another."
    assert not isinstance(premise, Evidence)


def test_measurement_requires_method_unit_and_conditions() -> None:
    valid = {
        "evidence_type": "measurement",
        "method": "Calibrated digital scale",
        "unit": "kilogram",
        "conditions": "Scale level on a stable indoor surface",
    }

    for required_field in ("method", "unit", "conditions"):
        invalid = valid | {required_field: "   "}

        try:
            MeasurementDetails.model_validate(invalid)
        except ValidationError as error:
            assert required_field in str(error)
        else:
            raise AssertionError(f"blank {required_field} should be rejected")


def test_evidence_requires_typed_details_and_provenance() -> None:
    evidence = Evidence.model_validate(
        {
            "id": "epi_mass_measurement",
            "category": "evidence",
            "statement": "The sample mass was 2.4 kilograms.",
            "uncertainty": {
                "level": "medium",
                "rationale": "One calibrated measurement has been recorded.",
            },
            "provenance": {
                "origin": "Laboratory notebook 7",
                "locator": "page 12",
            },
            "details": {
                "evidence_type": "measurement",
                "method": "Calibrated digital scale",
                "unit": "kilogram",
                "conditions": "Scale level on a stable indoor surface",
            },
        }
    )

    assert evidence.category == "evidence"
    assert evidence.details.evidence_type == "measurement"
    assert evidence.provenance == Provenance(origin="Laboratory notebook 7", locator="page 12")


def test_boundary_parser_returns_the_category_specific_model() -> None:
    item = parse_epistemic_item(
        {
            "id": "epi_explicit_premise",
            "category": "premise",
            "statement": "The system is closed during the experiment.",
            "uncertainty": {
                "level": "low",
                "rationale": "The boundary has not yet been physically verified.",
            },
            "origin": "Experimental setup assumption",
        }
    )

    assert isinstance(item, Premise)


def test_boundary_parser_rejects_category_confusion() -> None:
    confused_payload = {
        "id": "epi_confused_item",
        "category": "evidence",
        "statement": "This is actually only an assumption.",
        "uncertainty": medium_confidence().model_dump(mode="json"),
        "origin": "Unsupported assumption",
    }

    try:
        parse_epistemic_item(confused_payload)
    except ValidationError as error:
        assert "evidence" in str(error)
    else:
        raise AssertionError("a premise-shaped payload must not validate as evidence")
