from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .safe_workspace import (
    WorkspaceSecurityError,
    resolve_safe_path,
)


VerificationStage = Literal[
    "install",
    "build",
    "unit_test",
    "integration_test",
    "smoke_test",
]


@dataclass(frozen=True)
class VerificationCommand:
    stage: VerificationStage
    command: str
    timeout_seconds: int = 300

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "command": self.command,
            "timeoutSeconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class CommandResult:
    stage: VerificationStage
    command: str
    status: Literal["passed", "failed", "timed_out"]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "command": self.command,
            "status": self.status,
            "exitCode": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "durationSeconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class VerificationResult:
    candidate_path: str
    status: Literal["passed", "failed"]
    commands: list[CommandResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidatePath": self.candidate_path,
            "status": self.status,
            "commands": [
                command.to_dict()
                for command in self.commands
            ],
            "errors": list(self.errors),
        }


class VerificationRunner:
    """
    Executes explicitly approved verification commands inside
    the candidate workspace.

    Commands never run against the original submissions.
    """

    def run(
        self,
        candidate_root: Path,
        commands: list[VerificationCommand],
    ) -> VerificationResult:

        candidate_root = candidate_root.resolve()

        if not candidate_root.exists():
            return VerificationResult(
                candidate_path=str(candidate_root),
                status="failed",
                errors=["Candidate workspace does not exist."],
            )

        if not candidate_root.is_dir():
            return VerificationResult(
                candidate_path=str(candidate_root),
                status="failed",
                errors=["Candidate workspace is not a directory."],
            )

        results: list[CommandResult] = []
        errors: list[str] = []

        for verification_command in commands:
            result = self._run_command(
                candidate_root,
                verification_command,
            )

            results.append(result)

            if result.status != "passed":
                errors.append(
                    f"{result.stage} verification failed: "
                    f"{result.command}"
                )

                # Stop immediately after a failed stage.
                break

        return VerificationResult(
            candidate_path=str(candidate_root),
            status="failed" if errors else "passed",
            commands=results,
            errors=errors,
        )

    def _run_command(
        self,
        candidate_root: Path,
        verification_command: VerificationCommand,
    ) -> CommandResult:

        command = verification_command.command.strip()

        if not command:
            return CommandResult(
                stage=verification_command.stage,
                command=verification_command.command,
                status="failed",
                exit_code=None,
                stdout="",
                stderr="Empty verification command.",
                duration_seconds=0.0,
            )

        # Make sure the working directory itself is still inside
        # the candidate boundary.
        try:
            working_directory = resolve_safe_path(
                candidate_root,
                ".",
            )
        except WorkspaceSecurityError as exc:
            return CommandResult(
                stage=verification_command.stage,
                command=verification_command.command,
                status="failed",
                exit_code=None,
                stdout="",
                stderr=str(exc),
                duration_seconds=0.0,
            )

        started = time.monotonic()

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=verification_command.timeout_seconds,
                check=False,
            )

            duration = time.monotonic() - started

            return CommandResult(
                stage=verification_command.stage,
                command=verification_command.command,
                status=(
                    "passed"
                    if completed.returncode == 0
                    else "failed"
                ),
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started

            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )

            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )

            return CommandResult(
                stage=verification_command.stage,
                command=verification_command.command,
                status="timed_out",
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )