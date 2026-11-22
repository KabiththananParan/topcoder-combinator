from pathlib import Path

from app.code_mode.verification_runner import (
    VerificationCommand,
    VerificationRunner,
)


def test_successful_command(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command="python -c \"print('hello')\"",
            )
        ],
    )

    assert result.status == "passed"
    assert len(result.commands) == 1

    command = result.commands[0]

    assert command.status == "passed"
    assert command.exit_code == 0
    assert "hello" in command.stdout


def test_failed_command(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            )
        ],
    )

    assert result.status == "failed"
    assert result.commands[0].status == "failed"
    assert result.commands[0].exit_code == 1


def test_stops_after_failure(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    marker = candidate / "marker.txt"

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            ),
            VerificationCommand(
                stage="build",
                command=(
                    "python -c "
                    "\"from pathlib import Path; "
                    "Path('marker.txt').write_text('executed')\""
                ),
            ),
        ],
    )

    assert result.status == "failed"
    assert len(result.commands) == 1
    assert not marker.exists()


def test_command_runs_inside_candidate(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="smoke_test",
                command=(
                    "python -c "
                    "\"from pathlib import Path; "
                    "print(Path.cwd())\""
                ),
            )
        ],
    )

    assert result.status == "passed"
    assert str(candidate.resolve()) in result.commands[0].stdout


def test_missing_candidate_fails(tmp_path: Path):
    candidate = tmp_path / "does-not-exist"

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command="echo hello",
            )
        ],
    )

    assert result.status == "failed"
    assert "does not exist" in result.errors[0]


def test_empty_command_fails(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command="",
            )
        ],
    )

    assert result.status == "failed"
    assert result.commands[0].status == "failed"


def test_timeout_is_reported(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    result = VerificationRunner().run(
        candidate,
        [
            VerificationCommand(
                stage="unit_test",
                command=(
                    "python -c "
                    "\"import time; time.sleep(2)\""
                ),
                timeout_seconds=1,
            )
        ],
    )

    assert result.status == "failed"
    assert result.commands[0].status == "timed_out"