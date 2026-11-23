from dataclasses import replace

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
                    alternatives=list(
                        recommendation.alternatives
                    ),
                )
            )

        return DecisionSet(
            challenge_id=recommendations.challenge_id,
            decisions=decisions,
        )

    def reconcile_persisted_decisions(
        self,
        recommendations: IdeationRecommendationSet,
        persisted: DecisionSet,
    ) -> DecisionSet:
        """Refresh stale recommendation metadata without overwriting Copilot decisions."""
        if persisted.challenge_id != recommendations.challenge_id:
            raise ValueError(
                "Persisted decisions belong to a different challenge."
            )

        fresh = self.create_pending_decisions(recommendations)
        fresh_by_id = {
            decision.requirement_id: decision
            for decision in fresh.decisions
        }
        reconciled: list[Decision] = []

        for decision in persisted.decisions:
            recommendation = fresh_by_id.get(decision.requirement_id)
            if recommendation is None:
                reconciled.append(decision)
                continue

            # Explicit Copilot outcomes remain authoritative. Pending
            # decisions are safe to enrich from the current recommendation.
            stale_auto_review = (
                decision.state == "manual_review"
                and decision.reason
                == "Requires human review because no recommended source was identified."
            )
            if decision.state != "pending" and not stale_auto_review:
                reconciled.append(decision)
                continue

            reconciled.append(
                replace(
                    decision,
                    requirement_title=recommendation.requirement_title,
                    state="pending",
                    recommended_submission_id=(
                        recommendation.recommended_submission_id
                    ),
                    recommendation_score=recommendation.recommendation_score,
                    recommendation_confidence=(
                        recommendation.recommendation_confidence
                    ),
                    evidence_refs=list(recommendation.evidence_refs),
                    alternatives=list(recommendation.alternatives),
                    reason=recommendation.reason,
                )
            )

        known_ids = {decision.requirement_id for decision in reconciled}
        reconciled.extend(
            decision
            for decision in fresh.decisions
            if decision.requirement_id not in known_ids
        )

        return DecisionSet(
            challenge_id=persisted.challenge_id,
            decisions=reconciled,
        )
