from __future__ import annotations

from dataclasses import dataclass, field

from app.decisions.models import DecisionSet
from app.ideation.idea_models import IdeaComponent
from app.ideation.evaluation_models import IdeationEvaluation
from app.ideation.synthesis import SynthesizedConcept


@dataclass(frozen=True)
class IdeationVerificationResult:
    status: str
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": dict(self.checks),
            "errors": list(self.errors),
        }


class IdeationVerifier:
    """Deterministic verification of Ideation Mode planning state."""

    def verify(
        self,
        ideas: list[IdeaComponent],
        evaluation: IdeationEvaluation,
        decisions: DecisionSet,
        synthesized_concept: SynthesizedConcept | None = None,
    ) -> IdeationVerificationResult:
        checks: dict[str, bool] = {}
        errors: list[str] = []

        checks["ideas_present"] = bool(ideas)
        if not ideas:
            errors.append("No ideas were analyzed.")

        checks["all_ideas_have_evidence"] = all(
            bool(idea.evidence_refs) for idea in ideas
        )
        if not checks["all_ideas_have_evidence"]:
            errors.append("One or more ideas have no evidence references.")

        checks["all_criteria_evaluated"] = len(evaluation.evaluations) >= (
            len(ideas) * 5
        )
        if not checks["all_criteria_evaluated"]:
            errors.append("Not all ideation criteria were evaluated.")

        checks["all_criteria_decisions_present"] = len(decisions.decisions) == 5
        if not checks["all_criteria_decisions_present"]:
            errors.append("Expected one Copilot decision for each criterion.")

        checks["decisions_are_pending_or_resolved"] = all(
            decision.state in {
                "pending",
                "accepted",
                "rejected",
                "alternative_selected",
                "blocked",
                "manual_review",
                "unresolved",
            }
            for decision in decisions.decisions
        )
        if not checks["decisions_are_pending_or_resolved"]:
            errors.append("Invalid decision state detected.")

        checks["synthesis_is_consistent"] = synthesized_concept is not None
        if synthesized_concept is None:
            errors.append("Synthesized concept was not provided for verification.")
        else:
            selected_ids = set(synthesized_concept.source_idea_ids)
            known_ids = {idea.idea_id for idea in ideas}
            checks["synthesis_sources_are_known"] = selected_ids <= known_ids
            if not checks["synthesis_sources_are_known"]:
                errors.append("Synthesized concept references unknown source ideas.")

            checks["synthesis_evidence_present"] = bool(
                synthesized_concept.evidence_refs
            ) if selected_ids else True
            if selected_ids and not checks["synthesis_evidence_present"]:
                errors.append("Synthesized concept has selected sources but no evidence.")

        checks["evidence_refs_are_unique"] = len(
            {
                evidence_ref
                for idea in ideas
                for evidence_ref in idea.evidence_refs
            }
        ) == sum(len(idea.evidence_refs) for idea in ideas)
        if not checks["evidence_refs_are_unique"]:
            errors.append("Duplicate evidence references detected.")

        return IdeationVerificationResult(
            status="passed" if not errors else "failed",
            checks=checks,
            errors=errors,
        )
