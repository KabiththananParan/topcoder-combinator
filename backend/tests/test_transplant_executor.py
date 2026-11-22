from pathlib import Path

from app.code_mode.models import FileTransplant
from app.code_mode.transplant_executor import TransplantExecutor
from app.code_mode.transplant_plan import (
    TransplantItem,
    TransplantPlan,
)


def make_plan(
    source_path="src/source.txt",
    target_path="src/target.txt",
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


def test_transplants_file(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "src" / "source.txt"
    source.parent.mkdir(parents=True)
    source.write_text("hello from SUB_001")

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    target = candidate / "src" / "target.txt"

    assert result.status == "success"
    assert target.exists()
    assert target.read_text() == "hello from SUB_001"


def test_source_submission_is_not_modified(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text("original")

    candidate = tmp_path / "candidate"

    TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="source.txt",
            target_path="copied.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert source.read_text() == "original"


def test_existing_target_is_snapshotted(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text("new content")

    candidate = tmp_path / "candidate"
    target = candidate / "target.txt"
    target.parent.mkdir(parents=True)
    target.write_text("old content")

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="source.txt",
            target_path="target.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "success"
    assert target.read_text() == "new content"

    snapshot = candidate / ".transplant-snapshots"

    assert snapshot.exists()
    assert any(
        path.read_text() == "old content"
        for path in snapshot.iterdir()
    )


def test_missing_source_fails(tmp_path):
    submissions, _, _ = create_submissions(tmp_path)

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="does-not-exist.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "failed"
    assert len(result.errors) == 1


def test_path_traversal_is_rejected(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text("secret")

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="../SUB_002/source.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "failed"
    assert "escapes" in result.errors[0]


def test_target_path_traversal_is_rejected(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    source = sub1 / "source.txt"
    source.write_text("content")

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="source.txt",
            target_path="../outside.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "failed"
    assert "escapes" in result.errors[0]


def test_symlink_source_is_rejected(tmp_path):
    submissions, sub1, _ = create_submissions(tmp_path)

    real_file = tmp_path / "outside.txt"
    real_file.write_text("outside")

    source = sub1 / "source.txt"
    source.symlink_to(real_file)

    candidate = tmp_path / "candidate"

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=make_plan(
            source_path="source.txt",
        ),
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "failed"
    assert "symlink" in result.errors[0]


def test_non_transplant_items_are_skipped(tmp_path):
    submissions, _, _ = create_submissions(tmp_path)

    candidate = tmp_path / "candidate"

    item = TransplantItem(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        source_submission_id=None,
        target_submission_id="SUB_002",
        action="keep_base",
        reason="Already present.",
    )

    plan = TransplantPlan(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        items=[item],
    )

    result = TransplantExecutor().execute(
        challenge_id="TEST_CHALLENGE",
        plan=plan,
        submissions_root=submissions,
        candidate_root=candidate,
    )

    assert result.status == "success"
    assert result.executions[0].status == "skipped"


def test_challenge_mismatch_is_rejected(tmp_path):
    submissions, _, _ = create_submissions(tmp_path)

    candidate = tmp_path / "candidate"

    plan = make_plan()

    try:
        TransplantExecutor().execute(
            challenge_id="OTHER_CHALLENGE",
            plan=plan,
            submissions_root=submissions,
            candidate_root=candidate,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("Expected ValueError")