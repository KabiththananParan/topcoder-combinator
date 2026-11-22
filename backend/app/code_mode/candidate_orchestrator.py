from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import (
    ExecutionResult,
    TransplantExecution,
)
from .transplant_executor import TransplantExecutor
from .transplant_plan import TransplantPlan
from .transplant_rollback import (
    TransplantRollbackController,
    TransplantRollbackError,
)
from .verification_runner import (
    VerificationCommand,
    VerificationResult,
    VerificationRunner,
)


@dataclass(frozen=True)
class TransplantVerificationResult:
    requirement_id: str
    transplant: TransplantExecution
    verification: VerificationResult
    final_status: str

    def to_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "transplant": self.transplant.to_dict(),
            "verification": self.verification.to_dict(),
            "finalStatus": self.final_status,
        }


@dataclass(frozen=True)
class CandidateExecutionResult:
    challenge_id: str
    candidate_path: str
    status: str
    results: list[TransplantVerificationResult] = field(
        default_factory=list
    )
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "candidatePath": self.candidate_path,
            "status": self.status,
            "results": [
                result.to_dict()
                for result in self.results
            ],
            "errors": list(self.errors),
        }


class CandidateOrchestrator:
    """
    Applies approved transplants one at a time.

    Each successful transplant is verified immediately.

    If verification fails:
        - the transplant is rolled back
        - previous successful transplants remain intact
        - independent later transplants may continue
    """

    def __init__(
        self,
        executor: TransplantExecutor | None = None,
        verifier: VerificationRunner | None = None,
        rollback_controller: TransplantRollbackController | None = None,
    ):
        self.executor = executor or TransplantExecutor()
        self.verifier = verifier or VerificationRunner()
        self.rollback_controller = (
            rollback_controller
            or TransplantRollbackController()
        )

    def execute(
        self,
        challenge_id: str,
        plan: TransplantPlan,
        submissions_root: Path,
        candidate_root: Path,
        verification_commands: list[VerificationCommand],
    ) -> CandidateExecutionResult:

        if plan.challenge_id != challenge_id:
            raise ValueError(
                "Transplant plan challenge does not match execution challenge."
            )

        candidate_root = candidate_root.resolve()

        candidate_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        results: list[TransplantVerificationResult] = []
        errors: list[str] = []

        for item in plan.transplant_items():

            # Execute exactly one transplant at a time.
            single_item_plan = TransplantPlan(
                challenge_id=plan.challenge_id,
                base_submission_id=plan.base_submission_id,
                items=[item],
                risks=list(plan.risks),
            )

            execution_result: ExecutionResult = self.executor.execute(
                challenge_id=challenge_id,
                plan=single_item_plan,
                submissions_root=submissions_root,
                candidate_root=candidate_root,
            )

            if execution_result.status == "failed":
                errors.extend(execution_result.errors)

                for execution in execution_result.executions:
                    results.append(
                        TransplantVerificationResult(
                            requirement_id=item.requirement_id,
                            transplant=execution,
                            verification=VerificationResult(
                                candidate_path=str(candidate_root),
                                status="failed",
                                errors=[
                                    "Transplant failed before verification."
                                ],
                            ),
                            final_status="failed",
                        )
                    )

                # Do not run verification if the transplant itself failed.
                continue

            successful_executions = [
                execution
                for execution in execution_result.executions
                if execution.status == "success"
            ]

            if not successful_executions:
                continue

            # A TransplantItem should normally produce exactly one
            # file transplant execution. Keep the orchestration
            # deterministic if multiple mappings are introduced later.
            for execution in successful_executions:

                verification = self.verifier.run(
                    candidate_root=candidate_root,
                    commands=verification_commands,
                )

                if verification.status == "passed":
                    results.append(
                        TransplantVerificationResult(
                            requirement_id=item.requirement_id,
                            transplant=execution,
                            verification=verification,
                            final_status="kept",
                        )
                    )

                    continue

                # Verification failed.
                try:
                    rolled_back = self.rollback_controller.rollback(
                        execution,
                        candidate_root,
                    )

                    results.append(
                        TransplantVerificationResult(
                            requirement_id=item.requirement_id,
                            transplant=rolled_back,
                            verification=verification,
                            final_status="rolled_back",
                        )
                    )

                    errors.extend(verification.errors)

                except TransplantRollbackError as exc:
                    errors.append(
                        f"Rollback failed for "
                        f"{item.requirement_id}: {exc}"
                    )

                    results.append(
                        TransplantVerificationResult(
                            requirement_id=item.requirement_id,
                            transplant=execution,
                            verification=verification,
                            final_status="rollback_failed",
                        )
                    )

        has_rollback_failure = any(
            result.final_status == "rollback_failed"
            for result in results
        )

        has_failed_transplant = any(
            result.final_status == "failed"
            for result in results
        )

        has_rolled_back = any(
            result.final_status == "rolled_back"
            for result in results
        )

        if has_rollback_failure:
            status = "failed"

        elif has_failed_transplant:
            status = "failed"

        elif has_rolled_back:
            # Some approved changes were rejected by verification,
            # but the candidate remains in a valid previous state.
            status = "partial"

        else:
            status = "success"

        return CandidateExecutionResult(
            challenge_id=challenge_id,
            candidate_path=str(candidate_root),
            status=status,
            results=results,
            errors=errors,
        )