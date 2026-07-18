"""Deterministic typed specialist contributions for orchestration tests."""

from forge.application.orchestrator import SpecialistContribution, _decision_prompt
from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    DirectObservationDetails,
    Evidence,
    ExploratoryItem,
    ExploratoryType,
    Premise,
    Provenance,
)
from forge.domain.investigation import WorkflowStage
from forge.gateways.model import ModelRole
from forge.persistence.metadata import (
    ActionProposal,
    ChallengeDisposition,
    InvestigationRecord,
    SkepticalChallenge,
)


class DeterministicSpecialistRunner:
    def __init__(self) -> None:
        self.calls: list[ModelRole] = []

    async def run(
        self,
        role: ModelRole,
        record: InvestigationRecord,
    ) -> SpecialistContribution:
        self.calls.append(role)
        confidence = Confidence(
            level=ConfidenceLevel.MEDIUM,
            rationale="Deterministic walking-skeleton output requiring later verification.",
        )
        if role is ModelRole.LEAD:
            return SpecialistContribution(
                decision_prompt=_decision_prompt(record.id, WorkflowStage.FOCUS_CHECKPOINT)
            )
        if role is ModelRole.RESEARCHER:
            return SpecialistContribution(
                epistemic_items=(
                    Premise(
                        id="epi_constraint_premise",
                        statement=(
                            "The relevant system operates under at least one binding constraint."
                        ),
                        uncertainty=confidence,
                        origin="First-principles decomposition",
                    ),
                    Evidence(
                        id="epi_seed_observation",
                        statement=record.seed,
                        uncertainty=confidence,
                        provenance=Provenance(origin="User-provided seed"),
                        details=DirectObservationDetails(
                            observer="User",
                            conditions="Initial investigation statement",
                        ),
                    ),
                )
            )
        if role is ModelRole.CONNECTION_FINDER:
            return SpecialistContribution(
                epistemic_items=(
                    ExploratoryItem(
                        id="epi_constraint_connection",
                        statement=(
                            "Binding constraints may reveal analogous behavior across domains."
                        ),
                        uncertainty=confidence,
                        provenance=Provenance(origin="Deterministic Connection Finder"),
                        exploratory_type=ExploratoryType.CONNECTION,
                        based_on=("epi_constraint_premise", "epi_seed_observation"),
                    ),
                )
            )
        if role is ModelRole.SYNTHESIZER:
            connection = next(
                (
                    item
                    for item in reversed(record.epistemic_items)
                    if isinstance(item, ExploratoryItem)
                    and item.exploratory_type is ExploratoryType.CONNECTION
                ),
                None,
            )
            if connection is None:
                raise ValueError("deterministic synthesis requires a saved connection")
            return SpecialistContribution(
                epistemic_items=(
                    ExploratoryItem(
                        id="epi_constraint_hypothesis",
                        statement=(
                            "The same constraint pattern predicts a testable cross-domain effect."
                        ),
                        uncertainty=confidence,
                        provenance=Provenance(origin="Deterministic Synthesizer"),
                        exploratory_type=ExploratoryType.HYPOTHESIS,
                        based_on=(connection.id,),
                    ),
                )
            )
        if role is ModelRole.SKEPTIC:
            hypothesis = next(
                (
                    item
                    for item in reversed(record.epistemic_items)
                    if isinstance(item, ExploratoryItem)
                    and item.exploratory_type is ExploratoryType.HYPOTHESIS
                ),
                None,
            )
            if hypothesis is None:
                raise ValueError("deterministic skepticism requires a saved hypothesis")
            return SpecialistContribution(
                skeptical_challenges=(
                    SkepticalChallenge(
                        target_id=hypothesis.id,
                        challenge=(
                            "The proposed analogy may preserve language but not causal structure."
                        ),
                        disposition=ChallengeDisposition.REVISE,
                        rationale="Retain only predictions that can be independently tested.",
                    ),
                )
            )
        if role is ModelRole.EXPERIMENT_DESIGNER:
            return SpecialistContribution(
                selected_action=ActionProposal(
                    statement="Compare the predicted effect in two constrained systems.",
                    expected_observation=(
                        "Both systems change in the predicted direction near the limit."
                    ),
                    disconfirming_observation="The systems diverge despite equivalent constraints.",
                    cost="One bounded comparison.",
                    risk="Low; conceptual overreach is the primary risk.",
                    stopping_condition=(
                        "Stop after one disconfirming comparison or two consistent results."
                    ),
                )
            )
        raise ValueError(f"unsupported deterministic specialist role: {role}")


__all__ = ["DeterministicSpecialistRunner"]
