from dataclasses import dataclass, field
from typing import Literal


EvaluationStatus = Literal[
    "complete",
    "partial",
    "missing",
    "not_verifiable",
    "manual_review_required",
]


IdeationCriterion = Literal[
    "Originality",
    "Feasibility",
    "Scalability",
    "Impact Potential",
    "Alignment with Scope",
]


@dataclass(frozen=True)
class CriterionEvaluation:
    idea_id: str
    submission_id: str
    criterion: IdeationCriterion

    status: EvaluationStatus

    score: float = 0.0
    confidence: float = 0.0

    reasoning: str = ""

    evidence_refs: list[str] = field(default_factory=list)

    unresolved_conflicts: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict:
        return {
            "ideaId": self.idea_id,
            "submissionId": self.submission_id,
            "criterion": self.criterion,
            "status": self.status,
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidenceRefs": self.evidence_refs,
            "unresolvedConflicts": self.unresolved_conflicts,
        }


@dataclass(frozen=True)
class IdeationEvaluation:
    challenge_id: str
    evaluations: list[CriterionEvaluation] = field(
        default_factory=list
    )

    def for_idea(
        self,
        idea_id: str,
    ) -> list[CriterionEvaluation]:
        return [
            evaluation
            for evaluation in self.evaluations
            if evaluation.idea_id == idea_id
        ]

    def for_criterion(
        self,
        criterion: IdeationCriterion,
    ) -> list[CriterionEvaluation]:
        return [
            evaluation
            for evaluation in self.evaluations
            if evaluation.criterion == criterion
        ]

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "evaluations": [
                evaluation.to_dict()
                for evaluation in self.evaluations
            ],
        }
