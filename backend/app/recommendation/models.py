from dataclasses import dataclass, field
from typing import Literal


CompatibilityRisk = Literal[
    "low",
    "medium",
    "high",
    "unknown",
]

RecommendationStatus = Literal[
    "recommended",
    "tie",
    "manual_review_required",
    "no_suitable_source",
]


@dataclass(frozen=True)
class Recommendation:
    requirement_id: str
    requirement_title: str

    recommended_submission_id: str | None

    status: RecommendationStatus

    score: float
    confidence: float

    reasoning: str

    compatibility_risk: CompatibilityRisk

    unresolved_conflicts: list[str] = field(default_factory=list)

    evidence_refs: list[str] = field(default_factory=list)

    evidence_summary: list[str] = field(default_factory=list)

    alternatives: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecommendationSet:
    challenge_id: str
    recommendations: list[Recommendation] = field(default_factory=list)

    def for_requirement(
        self,
        requirement_id: str,
    ) -> Recommendation | None:
        for recommendation in self.recommendations:
            if recommendation.requirement_id == requirement_id:
                return recommendation

        return None

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "recommendations": [
                {
                    "requirementId": item.requirement_id,
                    "requirementTitle": item.requirement_title,
                    "recommendedSubmissionId": (
                        item.recommended_submission_id
                    ),
                    "status": item.status,
                    "score": item.score,
                    "confidence": item.confidence,
                    "reasoning": item.reasoning,
                    "compatibilityRisk": item.compatibility_risk,
                    "unresolvedConflicts": item.unresolved_conflicts,
                    "evidenceRefs": item.evidence_refs,
                    "evidenceSummary": item.evidence_summary,
                    "alternatives": item.alternatives,
                }
                for item in self.recommendations
            ],
        }