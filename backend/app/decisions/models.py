from dataclasses import dataclass, field
from typing import Literal


DecisionState = Literal[
    "pending",
    "accepted",
    "rejected",
    "alternative_selected",
    "blocked",
    "manual_review",
    "unresolved",
]


@dataclass(frozen=True)
class Decision:
    requirement_id: str
    requirement_title: str

    state: DecisionState

    selected_submission_id: str | None = None

    recommended_submission_id: str | None = None

    reason: str = ""

    recommendation_score: float | None = None
    recommendation_confidence: float | None = None

    evidence_refs: list[str] = field(default_factory=list)

    alternatives: list[str] = field(default_factory=list)

    alternative_submission_id: str | None = None

    reviewer: str | None = None

    def to_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "requirementTitle": self.requirement_title,
            "state": self.state,
            "selectedSubmissionId": self.selected_submission_id,
            "recommendedSubmissionId": self.recommended_submission_id,
            "reason": self.reason,
            "recommendationScore": self.recommendation_score,
            "recommendationConfidence": self.recommendation_confidence,
            "evidenceRefs": self.evidence_refs,
            "alternatives": self.alternatives,
            "alternativeSubmissionId": (
                self.alternative_submission_id
            ),
            "reviewer": self.reviewer,
        }


@dataclass(frozen=True)
class DecisionSet:
    challenge_id: str
    decisions: list[Decision] = field(default_factory=list)

    def for_requirement(
        self,
        requirement_id: str,
    ) -> Decision | None:
        for decision in self.decisions:
            if decision.requirement_id == requirement_id:
                return decision

        return None

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "decisions": [
                decision.to_dict()
                for decision in self.decisions
            ],
        }