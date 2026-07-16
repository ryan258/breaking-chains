"""Traceable epistemic categories and their validation rules."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

from forge.domain.identifiers import EpistemicItemId, InvestigationId, new_epistemic_item_id

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None


class DomainModel(BaseModel):
    """Shared safe defaults for immutable domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class ConfidenceLevel(StrEnum):
    """Coarse uncertainty level paired with a required rationale."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(DomainModel):
    """An uncertainty label that never changes epistemic category."""

    level: ConfidenceLevel
    rationale: NonEmptyText


class Provenance(DomainModel):
    """Where an evidence item came from and where it can be inspected."""

    origin: NonEmptyText
    locator: OptionalText = None


class LinkKind(StrEnum):
    """Traceable relationships between epistemic items."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    CONNECTS = "connects"


class EpistemicLink(DomainModel):
    """A typed relationship to another epistemic item."""

    kind: LinkKind
    target_id: EpistemicItemId
    target_investigation_id: InvestigationId | None = None


class DirectObservationDetails(DomainModel):
    """Required context for something directly perceived or recorded."""

    evidence_type: Literal["direct_observation"] = "direct_observation"
    observer: NonEmptyText
    conditions: NonEmptyText


class PrimarySourceDetails(DomainModel):
    """Required context for an original document or first-hand record."""

    evidence_type: Literal["primary_source"] = "primary_source"
    source_reference: NonEmptyText
    content_hash: OptionalText = None


class MeasurementDetails(DomainModel):
    """Required context for a reproducible measurement."""

    evidence_type: Literal["measurement"] = "measurement"
    method: NonEmptyText
    unit: NonEmptyText
    conditions: NonEmptyText


class ExperimentResultDetails(DomainModel):
    """Required context for the outcome of an experiment."""

    evidence_type: Literal["experiment_result"] = "experiment_result"
    procedure: NonEmptyText
    reproducibility_notes: NonEmptyText


EvidenceDetails = Annotated[
    DirectObservationDetails | PrimarySourceDetails | MeasurementDetails | ExperimentResultDetails,
    Field(discriminator="evidence_type"),
]


class BaseEpistemicItem(DomainModel):
    """Fields shared by all epistemic categories."""

    id: EpistemicItemId = Field(default_factory=new_epistemic_item_id)
    statement: NonEmptyText
    uncertainty: Confidence
    links: tuple[EpistemicLink, ...] = ()
    notes: OptionalText = None

    @model_validator(mode="after")
    def validate_links(self) -> "BaseEpistemicItem":
        link_keys = tuple(
            (link.kind, link.target_investigation_id, link.target_id) for link in self.links
        )
        if any(
            link.target_id == self.id and link.target_investigation_id is None
            for link in self.links
        ):
            raise ValueError("epistemic items cannot link to themselves")
        if len(link_keys) != len(set(link_keys)):
            raise ValueError("epistemic links must be unique")
        return self


class Premise(BaseEpistemicItem):
    """An explicitly adopted assumption, definition, or axiom—not evidence."""

    category: Literal["premise"] = "premise"
    origin: NonEmptyText


class Evidence(BaseEpistemicItem):
    """An inspectable input with subtype-specific provenance requirements."""

    category: Literal["evidence"] = "evidence"
    provenance: Provenance
    details: EvidenceDetails


class DerivedClaim(BaseEpistemicItem):
    """A conclusion with an explicit derivation and dependency set."""

    category: Literal["derived_claim"] = "derived_claim"
    provenance: Provenance
    dependencies: tuple[EpistemicItemId, ...] = Field(min_length=1)
    derivation: NonEmptyText

    @model_validator(mode="after")
    def validate_dependencies(self) -> "DerivedClaim":
        if self.id in self.dependencies:
            raise ValueError("derived claims cannot depend on themselves")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("derived claim dependencies must be unique")
        return self


class ExploratoryType(StrEnum):
    """Kinds of ideas that must remain visibly non-evidentiary."""

    INTERPRETATION = "interpretation"
    SPECULATION = "speculation"
    CONNECTION = "connection"
    HYPOTHESIS = "hypothesis"
    MODEL_SUGGESTION = "model_suggestion"


class ExploratoryItem(BaseEpistemicItem):
    """An interpretation or possibility that has not become evidence."""

    category: Literal["exploratory_item"] = "exploratory_item"
    provenance: Provenance
    exploratory_type: ExploratoryType
    based_on: tuple[EpistemicItemId, ...] = ()


EpistemicItem = Annotated[
    Premise | Evidence | DerivedClaim | ExploratoryItem,
    Field(discriminator="category"),
]
_EPISTEMIC_ITEM_ADAPTER = TypeAdapter(EpistemicItem)


def parse_epistemic_item(value: object) -> EpistemicItem:
    """Validate untrusted input at the domain boundary."""

    return _EPISTEMIC_ITEM_ADAPTER.validate_python(value)


__all__ = [
    "Confidence",
    "ConfidenceLevel",
    "DerivedClaim",
    "DirectObservationDetails",
    "EpistemicLink",
    "EpistemicItem",
    "Evidence",
    "ExperimentResultDetails",
    "ExploratoryItem",
    "ExploratoryType",
    "LinkKind",
    "MeasurementDetails",
    "Premise",
    "PrimarySourceDetails",
    "Provenance",
    "new_epistemic_item_id",
    "parse_epistemic_item",
]
