from pathlib import Path

from app.code_mode.candidate_orchestrator import (
    CandidateOrchestrator,
)
from app.code_mode.models import FileTransplant
from app.code_mode.transplant_plan import (
    TransplantItem,
    TransplantPlan,
)
from app.code_mode.verification_runner import (
    VerificationCommand,
)


def make_plan():
    item = TransplantItem(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        action="transplant",
        reason="Approved.",
        file_transplants=[
            FileTransplant(
                source_path="source.txt",
                target_path="target.txt",
            )
        ],
    )

    return TransplantPlan(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        items=[item],
    )


def create_workspace(tmp_path: Path):
    submissions = tmp_path / "submissions"

    sub1 = submissions / "SUB_001"
    sub2 = submissions / "SUB_002"

    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)

    source = sub1 / "source.txt"
    source.write_text("new content")

    candidate = tmp_path / "candidate"

    return submissions, candidate


def test_successful_transplant_is_kept(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    result = CandidateOrchestrator().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python -c \"print('PASS')\"",
            )
        ],
    )

    target = candidate / "target.txt"

    assert result.status == "success"
    assert target.exists()
    assert target.read_text() == "new content"
    assert result.results[0].final_status == "kept"


def test_failed_verification_rolls_back_new_file(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    result = CandidateOrchestrator().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            )
        ],
    )

    target = candidate / "target.txt"

    assert result.status == "partial"
    assert not target.exists()
    assert result.results[0].final_status == "rolled_back"


def test_failed_verification_restores_existing_target(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    candidate.mkdir(parents=True, exist_ok=True)

    target = candidate / "target.txt"
    target.write_text("old content")

    result = CandidateOrchestrator().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            )
        ],
    )

    assert result.status == "partial"
    assert target.exists()
    assert target.read_text() == "old content"
    assert result.results[0].final_status == "rolled_back"

def test_source_is_unchanged_after_failed_verification(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    source = submissions / "SUB_001" / "source.txt"

    CandidateOrchestrator().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            )
        ],
    )

    assert source.read_text() == "new content"


def test_transplant_failure_does_not_run_verification(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    plan = make_plan()

    # Remove the source so the transplant itself fails.
    source = submissions / "SUB_001" / "source.txt"
    source.unlink()

    marker = candidate / "verification-ran.txt"

    result = CandidateOrchestrator().execute(
        challenge_id="TEST_CHALLENGE",
        plan=plan,
        submissions_root=submissions,
        candidate_root=candidate,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command=(
                    "python -c "
                    "\"from pathlib import Path; "
                    "Path('verification-ran.txt').write_text('yes')\""
                ),
            )
        ],
    )

    assert result.status == "failed"
    assert not marker.exists()
    assert result.results[0].final_status == "failed"


def test_challenge_mismatch_is_rejected(tmp_path):
    submissions, candidate = create_workspace(tmp_path)

    try:
        CandidateOrchestrator().execute(
            challenge_id="OTHER_CHALLENGE",
            plan=make_plan(),
            submissions_root=submissions,
            candidate_root=candidate,
            verification_commands=[],
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("Expected ValueError")