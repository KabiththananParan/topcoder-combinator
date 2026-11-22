from pathlib import Path

import pytest

from app.code_mode.models import (
    FileTransplant,
    TransplantExecution,
)
from app.code_mode.transplant_executor import TransplantExecutor
from app.code_mode.transplant_rollback import (
    TransplantRollbackController,
    TransplantRollbackError,
)
from app.code_mode.transplant_plan import (
    TransplantItem,
    TransplantPlan,
)


def make_plan(
    source_path="source.txt",
    target_path="target.txt",
):
    item = TransplantItem(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        action="transplant",
        reason="Approved transplant.",
        file_transplants=[
            FileTransplant(
                source_path=source_path,
                target_path=target_path,
            )
        ],
    )

    return TransplantPlan(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        items=[item],
    )


def create_submissions(tmp_path: Path):
    submissions = tmp_path / "submissions"

    sub1 = submissions / "SUB_001"
    sub2 = submissions / "SUB_002"

    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)

    return submissions, sub1, sub2


def execute_transplant(
    tmp_path: Path,
    source_content: str,
    target_content: str | None = None,
):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text(source_content)

    candidate = tmp_path / "candidate"

    if target_content is not None:
        target = candidate / "target.txt"
        target.parent.mkdir(parents=True)
        target.write_text(target_content)

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "success"

    return candidate, result.executions[0]


def test_rollback_new_file(tmp_path):
    candidate, execution = execute_transplant(
        tmp_path,
        source_content="new content",
    )

    target = candidate / "target.txt"

    assert target.exists()
    assert target.read_text() == "new content"
    assert execution.snapshot_path is None

    rolled_back = TransplantRollbackController().rollback(
        execution,
        candidate,
    )

    assert rolled_back.status == "rolled_back"
    assert not target.exists()


def test_rollback_restores_existing_file(tmp_path):
    candidate, execution = execute_transplant(
        tmp_path,
        source_content="new content",
        target_content="old content",
    )

    target = candidate / "target.txt"

    assert target.read_text() == "new content"
    assert execution.snapshot_path is not None

    rolled_back = TransplantRollbackController().rollback(
        execution,
        candidate,
    )

    assert rolled_back.status == "rolled_back"
    assert target.exists()
    assert target.read_text() == "old content"


def test_rollback_removes_snapshot(tmp_path):
    candidate, execution = execute_transplant(
        tmp_path,
        source_content="new content",
        target_content="old content",
    )

    snapshot = Path(execution.snapshot_path)

    assert snapshot.exists()

    TransplantRollbackController().rollback(
        execution,
        candidate,
    )

    assert not snapshot.exists()


def test_source_remains_immutable_after_rollback(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text("original source")

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    execution = result.executions[0]

    TransplantRollbackController().rollback(
        execution,
        candidate,
    )

    assert source.read_text() == "original source"


def test_only_successful_execution_can_be_rolled_back(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    execution = TransplantExecution(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        source_path="source.txt",
        target_path="target.txt",
        status="failed",
        message="Transplant failed.",
    )

    with pytest.raises(TransplantRollbackError):
        TransplantRollbackController().rollback(
            execution,
            candidate,
        )


def test_rollback_all_uses_reverse_order(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    target_a = candidate / "a.txt"
    target_b = candidate / "b.txt"

    target_a.write_text("A")
    target_b.write_text("B")

    executions = [
        TransplantExecution(
            requirement_id="REQ_1",
            source_submission_id="SUB_001",
            target_submission_id="SUB_002",
            source_path="a-source.txt",
            target_path="a.txt",
            status="success",
            message="Transplanted A.",
        ),
        TransplantExecution(
            requirement_id="REQ_2",
            source_submission_id="SUB_001",
            target_submission_id="SUB_002",
            source_path="b-source.txt",
            target_path="b.txt",
            status="success",
            message="Transplanted B.",
        ),
    ]

    results = TransplantRollbackController().rollback_all(
        executions,
        candidate,
    )

    assert results[0].status == "rolled_back"
    assert results[1].status == "rolled_back"

    assert not target_a.exists()
    assert not target_b.exists()