from dataclasses import dataclass, field
from typing import Literal

from app.ideation.evaluation_models import IdeationCriterion


IdeationRecommendationStatus = Literal[
    "recommended",
    "tie",
    "manual_review_required",
    "no_suitable_source",
]


@dataclass(frozen=True)
class IdeationRecommendation:
    criterion: IdeationCriterion
    recommended_idea_id: str | None
    recommended_submission_id: str | None
    status: IdeationRecommendationStatus
    score: float
    confidence: float
    reasoning: str
    evidence_refs: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion,
            "recommendedIdeaId": self.recommended_idea_id,
            "recommendedSubmissionId": self.recommended_submission_id,
            "status": self.status,
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidenceRefs": self.evidence_refs,
            "alternatives": self.alternatives,
            "unresolvedConflicts": self.unresolved_conflicts,
        }


@dataclass(frozen=True)
class IdeationRecommendationSet:
    challenge_id: str
    recommendations: list[IdeationRecommendation] = field(default_factory=list)

    def for_criterion(
        self,
        criterion: IdeationCriterion,
    ) -> IdeationRecommendation | None:
        for recommendation in self.recommendations:
            if recommendation.criterion == criterion:
                return recommendation
        return None

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "recommendations": [
                recommendation.to_dict()
                for recommendation in self.recommendations
            ],
        }
