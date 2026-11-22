from pathlib import Path
import shutil

from .models import (
    ExecutionResult,
    TransplantExecution,
)
from .safe_workspace import (
    WorkspaceSecurityError,
    resolve_safe_path,
)
from .transplant_plan import TransplantPlan


class TransplantExecutor:
    """
    Executes approved file-level transplant operations.

    Source submissions are treated as immutable.
    All writes happen inside the candidate workspace.
    """

    def execute(
        self,
        challenge_id: str,
        plan: TransplantPlan,
        submissions_root: Path,
        candidate_root: Path,
    ) -> ExecutionResult:

        if plan.challenge_id != challenge_id:
            raise ValueError(
                "Transplant plan challenge does not match execution challenge."
            )

        submissions_root = submissions_root.resolve()
        candidate_root = candidate_root.resolve()

        candidate_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        executions: list[TransplantExecution] = []
        errors: list[str] = []

        for item in plan.items:

            if item.action != "transplant":
                executions.append(
                    TransplantExecution(
                        requirement_id=item.requirement_id,
                        source_submission_id=item.source_submission_id,
                        target_submission_id=item.target_submission_id,
                        source_path=None,
                        target_path=None,
                        status="skipped",
                        message=(
                            f"Action '{item.action}' does not require "
                            "file transplantation."
                        ),
                    )
                )
                continue

            for file_mapping in item.file_transplants:
                execution = self._execute_file_transplant(
                    requirement_id=item.requirement_id,
                    source_submission_id=item.source_submission_id,
                    target_submission_id=item.target_submission_id,
                    source_path=file_mapping.source_path,
                    target_path=file_mapping.target_path,
                    submissions_root=submissions_root,
                    candidate_root=candidate_root,
                )

                executions.append(execution)

                if execution.status == "failed":
                    errors.append(execution.message)

        status = "failed" if errors else "success"

        return ExecutionResult(
            challenge_id=challenge_id,
            candidate_path=str(candidate_root),
            status=status,
            executions=executions,
            errors=errors,
        )

    def _execute_file_transplant(
        self,
        requirement_id: str,
        source_submission_id: str | None,
        target_submission_id: str,
        source_path: str,
        target_path: str,
        submissions_root: Path,
        candidate_root: Path,
    ) -> TransplantExecution:

        if source_submission_id is None:
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                "Transplant has no source submission.",
            )

        try:
            source_submission_root = resolve_safe_path(
                submissions_root,
                source_submission_id,
            )

            if not source_submission_root.is_dir():
                return self._failed(
                    requirement_id,
                    source_submission_id,
                    target_submission_id,
                    source_path,
                    target_path,
                    "Source submission directory does not exist.",
                )

            source_file = resolve_safe_path(
                source_submission_root,
                source_path,
            )

            target_file = resolve_safe_path(
                candidate_root,
                target_path,
            )

        except WorkspaceSecurityError as exc:
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                str(exc),
            )

        if not source_file.exists():
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                f"Source file does not exist: {source_path}",
            )

        if not source_file.is_file():
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                f"Source path is not a file: {source_path}",
            )

        # Reject symlink sources. This prevents a source repository from
        # redirecting the executor outside the submission boundary.
        if source_file.is_symlink():
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                f"Source file is a symlink: {source_path}",
            )

        snapshot_path: Path | None = None

        try:
            if target_file.exists():

                if target_file.is_symlink():
                    return self._failed(
                        requirement_id,
                        source_submission_id,
                        target_submission_id,
                        source_path,
                        target_path,
                        f"Target file is a symlink: {target_path}",
                    )

                if not target_file.is_file():
                    return self._failed(
                        requirement_id,
                        source_submission_id,
                        target_submission_id,
                        source_path,
                        target_path,
                        f"Target path is not a file: {target_path}",
                    )

                snapshot_dir = candidate_root / ".transplant-snapshots"

                snapshot_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                snapshot_name = (
                    f"{requirement_id}__"
                    f"{target_file.name}"
                )

                snapshot_path = resolve_safe_path(
                    candidate_root,
                    f".transplant-snapshots/{snapshot_name}",
                )

                shutil.copy2(
                    target_file,
                    snapshot_path,
                )

            target_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source_file,
                target_file,
            )

        except (OSError, shutil.Error) as exc:
            return self._failed(
                requirement_id,
                source_submission_id,
                target_submission_id,
                source_path,
                target_path,
                f"Transplant failed: {exc}",
                snapshot_path=snapshot_path,
            )

        return TransplantExecution(
            requirement_id=requirement_id,
            source_submission_id=source_submission_id,
            target_submission_id=target_submission_id,
            source_path=source_path,
            target_path=target_path,
            status="success",
            message="File transplanted successfully.",
            snapshot_path=(
                str(snapshot_path)
                if snapshot_path is not None
                else None
            ),
        )

    @staticmethod
    def _failed(
        requirement_id: str,
        source_submission_id: str | None,
        target_submission_id: str,
        source_path: str,
        target_path: str,
        message: str,
        snapshot_path: Path | None = None,
    ) -> TransplantExecution:

        return TransplantExecution(
            requirement_id=requirement_id,
            source_submission_id=source_submission_id,
            target_submission_id=target_submission_id,
            source_path=source_path,
            target_path=target_path,
            status="failed",
            message=message,
            snapshot_path=(
                str(snapshot_path)
                if snapshot_path is not None
                else None
            ),
        )