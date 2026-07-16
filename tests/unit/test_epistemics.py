import pytest
from pydantic import ValidationError

from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    DerivedClaim,
    DirectObservationDetails,
    EpistemicLink,
    Evidence,
    ExperimentResultDetails,
    LinkKind,
    MeasurementDetails,
    Premise,
    PrimarySourceDetails,
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


@pytest.mark.parametrize(
    "details_type,payload",
    [
        (
            DirectObservationDetails,
            {
                "evidence_type": "direct_observation",
                "observer": "",
                "conditions": "Observed in daylight",
            },
        ),
        (
            PrimarySourceDetails,
            {
                "evidence_type": "primary_source",
                "source_reference": "",
            },
        ),
        (
            ExperimentResultDetails,
            {
                "evidence_type": "experiment_result",
                "procedure": "Repeat the trial three times",
                "reproducibility_notes": "",
            },
        ),
    ],
)
def test_each_evidence_subtype_requires_its_inspection_context(
    details_type: type[DirectObservationDetails]
    | type[PrimarySourceDetails]
    | type[ExperimentResultDetails],
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        details_type.model_validate(payload)


def test_derived_claim_names_unique_nonself_dependencies() -> None:
    claim = DerivedClaim(
        id="epi_claim_mass",
        statement="The sample has nonzero mass.",
        uncertainty=medium_confidence(),
        dependencies=("epi_mass_measurement", "epi_scale_premise"),
        derivation="The calibrated reading is positive under the adopted scale premise.",
    )

    assert claim.dependencies == ("epi_mass_measurement", "epi_scale_premise")


@pytest.mark.parametrize(
    "dependencies",
    [
        (),
        ("epi_claim_mass",),
        ("epi_mass_measurement", "epi_mass_measurement"),
    ],
)
def test_derived_claim_rejects_empty_self_or_duplicate_dependencies(
    dependencies: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        DerivedClaim(
            id="epi_claim_mass",
            statement="The sample has nonzero mass.",
            uncertainty=medium_confidence(),
            dependencies=dependencies,
            derivation="The calibrated reading is positive.",
        )


def test_relationships_reject_self_links_and_duplicate_links() -> None:
    self_link = EpistemicLink(kind=LinkKind.SUPPORTS, target_id="epi_source_item")

    with pytest.raises(ValidationError):
        Premise(
            id="epi_source_item",
            statement="The system is closed.",
            uncertainty=medium_confidence(),
            origin="Experiment setup",
            links=(self_link,),
        )

    duplicate_link = EpistemicLink(kind=LinkKind.CONTRADICTS, target_id="epi_other_item")
    with pytest.raises(ValidationError):
        Premise(
            id="epi_source_item",
            statement="The system is closed.",
            uncertainty=medium_confidence(),
            origin="Experiment setup",
            links=(duplicate_link, duplicate_link),
        )


def test_epistemic_items_are_immutable_and_reject_unknown_fields() -> None:
    premise = Premise(
        id="epi_closed_system",
        statement="The system is closed.",
        uncertainty=medium_confidence(),
        origin="Experiment setup",
    )

    with pytest.raises(ValidationError):
        premise.statement = "Changed after validation."

    with pytest.raises(ValidationError):
        Premise.model_validate(premise.model_dump() | {"promoted_to_evidence": True})
