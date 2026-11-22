from dataclasses import dataclass, field
from typing import Literal


BaseSelectionStatus = Literal[
    "selected",
    "tie",
    "manual_review_required",
    "no_suitable_base",
]


@dataclass(frozen=True)
class BaseSelection:
    challenge_id: str
    selected_submission_id: str | None
    status: BaseSelectionStatus
    score: float
    confidence: float
    reasoning: str
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "selectedSubmissionId": self.selected_submission_id,
            "status": self.status,
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": list(self.alternatives),
            "risks": list(self.risks),
        }


TransplantExecutionStatus = Literal[
    "success",
    "failed",
    "rolled_back",
    "skipped",
]


@dataclass(frozen=True)
class FileTransplant:
    """
    Explicit source-to-target file mapping for a transplant operation.

    Paths are relative to their respective submission/candidate roots.
    """

    source_path: str
    target_path: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "sourcePath": self.source_path,
            "targetPath": self.target_path,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TransplantExecution:
    requirement_id: str
    source_submission_id: str | None
    target_submission_id: str
    source_path: str | None
    target_path: str | None
    status: TransplantExecutionStatus
    message: str
    snapshot_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "sourceSubmissionId": self.source_submission_id,
            "targetSubmissionId": self.target_submission_id,
            "sourcePath": self.source_path,
            "targetPath": self.target_path,
            "status": self.status,
            "message": self.message,
            "snapshotPath": self.snapshot_path,
        }


@dataclass(frozen=True)
class ExecutionResult:
    challenge_id: str
    candidate_path: str
    status: Literal["success", "failed", "rolled_back"]
    executions: list[TransplantExecution] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "candidatePath": self.candidate_path,
            "status": self.status,
            "executions": [
                execution.to_dict()
                for execution in self.executions
            ],
            "errors": list(self.errors),
        }