from __future__ import annotations

from app.decisions.models import DecisionSet
from app.ideation.evaluation_models import IdeationEvaluation
from app.ideation.idea_models import IdeaComponent
from app.ideation.recommendation_models import IdeationRecommendationSet
from app.provenance.models import ProvenanceLedger
from app.provenance.provenance_ledger import ProvenanceLedgerBuilder


class IdeationProvenanceBuilder:
    """Records Ideation evidence, evaluations, recommendations, and decisions."""

    def build(
        self,
        *,
        challenge_id: str,
        ideas: list[IdeaComponent],
        evaluation: IdeationEvaluation,
        recommendations: IdeationRecommendationSet,
        decisions: DecisionSet,
    ) -> ProvenanceLedger:
        builder = ProvenanceLedgerBuilder(challenge_id)

        evidence_ids_by_ref: dict[str, str] = {}

        for idea in ideas:
            for evidence_ref in idea.evidence_refs:
                evidence_id = builder.add_evidence(
                    submission_id=idea.submission_id,
                    requirement_id=idea.idea_id,
                    path=evidence_ref.split(":")[1],
                    evidence_type="document",
                    description=f"Evidence for {idea.title}",
                )
                evidence_ids_by_ref[evidence_ref] = evidence_id

        for item in evaluation.evaluations:
            builder.record_event(
                event_type="assessment_created",
                requirement_id=item.criterion,
                submission_id=item.submission_id,
                evidence_ids=[
                    evidence_ids_by_ref[ref]
                    for ref in item.evidence_refs
                    if ref in evidence_ids_by_ref
                ],
                reason=item.reasoning,
                metadata={
                    "ideaId": item.idea_id,
                    "criterion": item.criterion,
                    "status": item.status,
                    "score": item.score,
                    "confidence": item.confidence,
                    "unresolvedConflicts": list(
                        item.unresolved_conflicts
                    ),
                },
            )

        for recommendation in recommendations.recommendations:
            builder.record_event(
                event_type="recommendation_created",
                requirement_id=recommendation.criterion,
                submission_id=recommendation.recommended_submission_id,
                evidence_ids=[
                    evidence_ids_by_ref[ref]
                    for ref in recommendation.evidence_refs
                    if ref in evidence_ids_by_ref
                ],
                reason=recommendation.reasoning,
                metadata={
                    "recommendedIdeaId": recommendation.recommended_idea_id,
                    "recommendedSubmissionId": (
                        recommendation.recommended_submission_id
                    ),
                    "status": recommendation.status,
                    "score": recommendation.score,
                    "confidence": recommendation.confidence,
                    "alternatives": list(recommendation.alternatives),
                    "unresolvedConflicts": list(
                        recommendation.unresolved_conflicts
                    ),
                },
            )

        for decision in decisions.decisions:
            builder.record_event(
                event_type="decision_created",
                requirement_id=decision.requirement_id,
                submission_id=decision.selected_submission_id,
                evidence_ids=list(decision.evidence_refs),
                actor=decision.reviewer or "copilot",
                reason=decision.reason,
                metadata={
                    "state": decision.state,
                    "recommendedSubmissionId": (
                        decision.recommended_submission_id
                    ),
                    "selectedSubmissionId": (
                        decision.selected_submission_id
                    ),
                    "alternativeSubmissionId": (
                        decision.alternative_submission_id
                    ),
                    "recommendationScore": (
                        decision.recommendation_score
                    ),
                    "recommendationConfidence": (
                        decision.recommendation_confidence
                    ),
                },
            )

        builder.record_event(
            event_type="source_selected",
            reason="Ideation synthesis provenance recorded from Copilot decisions.",
            metadata={
                "decisionCount": len(decisions.decisions),
                "ideaCount": len(ideas),
                "evaluationCount": len(evaluation.evaluations),
                "recommendationCount": len(
                    recommendations.recommendations
                ),
            },
        )

        return builder.ledger
