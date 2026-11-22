from dataclasses import replace

from app.matrix.models import RequirementMatrix

from .models import Recommendation, RecommendationSet


class RecommendationEvidenceEnricher:
    """
    Attaches stable provenance evidence IDs to recommendations.

    This class does not create evidence IDs.
    Evidence IDs must already have been registered by
    EvidenceRegistrationService.
    """

    def enrich(
        self,
        recommendations: RecommendationSet,
        evidence_refs: dict[tuple[str, str], list[str]],
    ) -> RecommendationSet:
        enriched: list[Recommendation] = []

        for recommendation in recommendations.recommendations:
            submission_id = (
                recommendation.recommended_submission_id
            )

            if submission_id is None:
                enriched.append(recommendation)
                continue

            refs = evidence_refs.get(
                (
                    recommendation.requirement_id,
                    submission_id,
                ),
                [],
            )

            enriched.append(
                replace(
                    recommendation,
                    evidence_refs=list(refs),
                )
            )

        return RecommendationSet(
            challenge_id=recommendations.challenge_id,
            recommendations=enriched,
        )