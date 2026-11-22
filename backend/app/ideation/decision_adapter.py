from app.decisions.models import Decision, DecisionSet
from app.ideation.recommendation_models import IdeationRecommendationSet


class IdeationDecisionAdapter:
    """Maps Ideation recommendations into the shared Copilot decision model."""

    def create_pending_decisions(
        self,
        recommendations: IdeationRecommendationSet,
    ) -> DecisionSet:
        decisions: list[Decision] = []

        for recommendation in recommendations.recommendations:
            decisions.append(
                Decision(
                    requirement_id=recommendation.criterion,
                    requirement_title=recommendation.criterion,
                    state="pending",
                    recommended_submission_id=(
                        recommendation.recommended_submission_id
                    ),
                    recommendation_score=recommendation.score,
                    recommendation_confidence=recommendation.confidence,
                    reason=recommendation.reasoning,
                    evidence_refs=list(
                        recommendation.evidence_refs
                    ),
                )
            )

        return DecisionSet(
            challenge_id=recommendations.challenge_id,
            decisions=decisions,
        )
