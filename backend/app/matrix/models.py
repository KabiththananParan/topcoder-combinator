from dataclasses import dataclass, field

from app.analysis.models import RequirementAssessment


@dataclass(frozen=True)
class MatrixEntry:
    requirement_id: str
    requirement_title: str
    submission_id: str
    assessment: RequirementAssessment


@dataclass(frozen=True)
class RequirementMatrix:
    challenge_id: str
    entries: list[MatrixEntry] = field(default_factory=list)

    def for_requirement(
        self,
        requirement_id: str,
    ) -> list[MatrixEntry]:
        return [
            entry
            for entry in self.entries
            if entry.requirement_id == requirement_id
        ]

    def for_submission(
        self,
        submission_id: str,
    ) -> list[MatrixEntry]:
        return [
            entry
            for entry in self.entries
            if entry.submission_id == submission_id
        ]

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "entries": [
                {
                    "requirementId": entry.requirement_id,
                    "requirementTitle": entry.requirement_title,
                    "submissionId": entry.submission_id,
                    "assessment": {
                        "status": entry.assessment.assessment,
                        "evidence": entry.assessment.evidence,
                        "reasoning": entry.assessment.reasoning,
                        "confidence": entry.assessment.confidence,
                        "compatibilityRisk": (
                            entry.assessment.compatibility_risk
                        ),
                        "unresolvedConflicts": (
                            entry.assessment.unresolved_conflicts
                        ),
                    },
                }
                for entry in self.entries
            ],
        }