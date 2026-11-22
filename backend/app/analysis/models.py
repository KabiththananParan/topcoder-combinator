from dataclasses import dataclass, field
from typing import Literal


AssessmentStatus = Literal[
    "complete",
    "partial",
    "missing",
    "not_verifiable",
    "manual_review_required",
]


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    title: str
    priority: str
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RequirementAssessment:
    requirement_id: str
    submission_id: str
    assessment: AssessmentStatus
    evidence: list[dict] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    compatibility_risk: str = "unknown"
    unresolved_conflicts: list[str] = field(default_factory=list)