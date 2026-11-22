from app.ideation.evaluation_models import IdeationCriterion, IdeationEvaluation
from app.ideation.recommendation_models import (
    IdeationRecommendation,
    IdeationRecommendationSet,
)


class IdeationRecommendationEngine:
    """
    Deterministic recommendation engine for Ideation Mode.

    The challenge specification provides five evaluation criteria but
    does not provide criterion weights. Recommendations therefore use
    the criterion score directly and do not invent weighted scoring.
    """

    CRITERIA: tuple[IdeationCriterion, ...] = (
        "Originality",
        "Feasibility",
        "Scalability",
        "Impact Potential",
        "Alignment with Scope",
    )

    def recommend(
        self,
        challenge_id: str,
        evaluation: IdeationEvaluation,
    ) -> IdeationRecommendationSet:
        recommendations = []

        for criterion in self.CRITERIA:
            evaluations = evaluation.for_criterion(criterion)

            eligible = [
                item
                for item in evaluations
                if item.status in {"complete", "partial"}
            ]

            if not eligible:
                recommendations.append(
                    IdeationRecommendation(
                        criterion=criterion,
                        recommended_idea_id=None,
                        recommended_submission_id=None,
                        status="no_suitable_source",
                        score=0.0,
                        confidence=0.0,
                        reasoning="No suitable evaluated idea is available for this criterion.",
                    )
                )
                continue

            best_score = max(item.score for item in eligible)
            best = [item for item in eligible if item.score == best_score]

            if len(best) > 1:
                recommendations.append(
                    IdeationRecommendation(
                        criterion=criterion,
                        recommended_idea_id=None,
                        recommended_submission_id=None,
                        status="tie",
                        score=best_score,
                        confidence=min(item.confidence for item in best),
                        reasoning=(
                            "Multiple ideas have the same highest criterion score; "
                            "Copilot selection is required."
                        ),
                        evidence_refs=[
                            ref
                            for item in best
                            for ref in item.evidence_refs
                        ],
                        alternatives=[item.idea_id for item in best],
                    )
                )
                continue

            winner = best[0]
            alternatives = [
                item.idea_id
                for item in eligible
                if item.idea_id != winner.idea_id
            ]

            recommendations.append(
                IdeationRecommendation(
                    criterion=criterion,
                    recommended_idea_id=winner.idea_id,
                    recommended_submission_id=winner.submission_id,
                    status="recommended",
                    score=winner.score,
                    confidence=winner.confidence,
                    reasoning=winner.reasoning,
                    evidence_refs=winner.evidence_refs,
                    alternatives=alternatives,
                    unresolved_conflicts=winner.unresolved_conflicts,
                )
            )

        return IdeationRecommendationSet(
            challenge_id=challenge_id,
            recommendations=recommendations,
        )
