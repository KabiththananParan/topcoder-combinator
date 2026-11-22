from pathlib import Path
import shutil
from dataclasses import replace

from .models import TransplantExecution
from .safe_workspace import (
    WorkspaceSecurityError,
    resolve_safe_path,
)


class TransplantRollbackError(RuntimeError):
    """Raised when a transplant cannot be safely rolled back."""


class TransplantRollbackController:
    """
    Rolls back completed file transplant operations.

    Rollback only modifies the candidate workspace.
    Source submissions are never touched.
    """

    def rollback(
        self,
        execution: TransplantExecution,
        candidate_root: Path,
    ) -> TransplantExecution:
        """
        Roll back one successful transplant.

        If snapshot_path exists:
            restore the previous target contents.

        If snapshot_path is None:
            the target was newly created, so remove it.
        """

        if execution.status != "success":
            raise TransplantRollbackError(
                "Only successful transplant executions can be rolled back."
            )

        candidate_root = candidate_root.resolve()

        try:
            target_path = resolve_safe_path(
                candidate_root,
                execution.target_path or "",
            )
        except WorkspaceSecurityError as exc:
            raise TransplantRollbackError(str(exc)) from exc

        try:
            if execution.snapshot_path is not None:
                snapshot_path = resolve_safe_path(
                    candidate_root,
                    self._relative_to_candidate(
                        candidate_root,
                        execution.snapshot_path,
                    ),
                )

                if not snapshot_path.exists():
                    raise TransplantRollbackError(
                        f"Rollback snapshot does not exist: "
                        f"{execution.snapshot_path}"
                    )

                if snapshot_path.is_symlink():
                    raise TransplantRollbackError(
                        "Rollback snapshot is a symlink."
                    )

                if not snapshot_path.is_file():
                    raise TransplantRollbackError(
                        "Rollback snapshot is not a regular file."
                    )

                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.copy2(
                    snapshot_path,
                    target_path,
                )

                snapshot_path.unlink()

                message = "Previous target restored from snapshot."

            else:
                if target_path.exists():
                    if target_path.is_symlink():
                        raise TransplantRollbackError(
                            "Target file is a symlink."
                        )

                    if not target_path.is_file():
                        raise TransplantRollbackError(
                            "Target path is not a regular file."
                        )

                    target_path.unlink()

                message = "Newly transplanted file removed."

        except (OSError, shutil.Error) as exc:
            raise TransplantRollbackError(
                f"Rollback failed: {exc}"
            ) from exc

        return replace(
            execution,
            status="rolled_back",
            message=message,
        )

    def rollback_all(
        self,
        executions: list[TransplantExecution],
        candidate_root: Path,
    ) -> list[TransplantExecution]:
        """
        Roll back successful executions in reverse order.

        Non-successful executions are returned unchanged.
        """

        results = list(executions)

        for index in range(len(results) - 1, -1, -1):
            execution = results[index]

            if execution.status != "success":
                continue

            results[index] = self.rollback(
                execution,
                candidate_root,
            )

        return results

    @staticmethod
    def _relative_to_candidate(
        candidate_root: Path,
        path: str,
    ) -> str:
        """
        Convert an absolute snapshot path into a candidate-relative path.
        """

        path_obj = Path(path)

        try:
            return str(path_obj.resolve().relative_to(candidate_root.resolve()))
        except ValueError as exc:
            raise TransplantRollbackError(
                f"Snapshot escapes candidate workspace: {path}"
            ) from exc