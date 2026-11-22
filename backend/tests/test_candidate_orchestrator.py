from pathlib import Path

from app.code_mode.candidate_orchestrator import CandidateOrchestrator
from app.code_mode.transplant_plan import (
    TransplantItem,
    TransplantPlan,
)
from app.code_mode.models import FileTransplant
from app.code_mode.verification_runner import VerificationCommand


def make_plan() -> TransplantPlan:
    return TransplantPlan(
        challenge_id="CHALLENGE_001",
        base_submission_id="SUB_001",
        items=[
            TransplantItem(
                requirement_id="REQ_001",
                requirement_title="Analysis",
                action="transplant",
                source_submission_id="SUB_002",
                target_submission_id="SUB_001",
                reason="Approved transplant.",
                file_transplants=[
                    FileTransplant(
                        source_path="src/feature.py",
                        target_path="src/feature.py",
                        reason="Approved transplant.",
                    )
                ],
                evidence_refs=[
                    "EVIDENCE_000001",
                ],
            )
        ],
        risks=[],
    )


def test_candidate_orchestrator_keeps_successful_transplant(
    tmp_path: Path,
):
    submissions_root = tmp_path / "submissions"
    candidate_root = tmp_path / "candidate"

    source = (
        submissions_root
        / "SUB_002"
        / "src"
        / "feature.py"
    )

    source.parent.mkdir(parents=True)

    source.write_text(
        "print('SUB_002 implementation')\n"
    )

    candidate_source = (
        candidate_root
        / "src"
        / "feature.py"
    )

    candidate_source.parent.mkdir(parents=True)

    candidate_source.write_text(
        "print('SUB_001 implementation')\n"
    )

    plan = make_plan()

    result = CandidateOrchestrator().execute(
        challenge_id="CHALLENGE_001",
        plan=plan,
        submissions_root=submissions_root,
        candidate_root=candidate_root,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python3 -m py_compile src/feature.py",
            )
        ],
    )

    assert result.status == "success"
    assert len(result.results) == 1

    item_result = result.results[0]

    assert item_result.final_status == "kept"
    assert item_result.transplant.status == "success"
    assert item_result.verification.status == "passed"

    assert (
        candidate_source.read_text()
        == "print('SUB_002 implementation')\n"
    )

    assert (
        source.read_text()
        == "print('SUB_002 implementation')\n"
    )
    
    
def test_candidate_orchestrator_rolls_back_failed_verification(tmp_path):
    submissions_root = tmp_path / "submissions"
    candidate_root = tmp_path / "candidate"

    source_root = submissions_root / "SUB_002"
    source_root.mkdir(parents=True)

    source_file = source_root / "src" / "feature.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        "print('SUB_002 implementation')\n",
        encoding="utf-8",
    )

    candidate_file = candidate_root / "src" / "feature.py"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "print('SUB_001 implementation')\n",
        encoding="utf-8",
    )

    plan = make_plan()

    orchestrator = CandidateOrchestrator()

    result = orchestrator.execute(
        challenge_id="CHALLENGE_001",
        plan=plan,
        submissions_root=submissions_root,
        candidate_root=candidate_root,
        verification_commands=[
            VerificationCommand(
                stage="unit_test",
                command="python -c \"raise SystemExit(1)\"",
            )
        ],
    )

    assert result.status == "partial"
    assert len(result.results) == 1

    item_result = result.results[0]

    assert item_result.final_status == "rolled_back"
    assert item_result.transplant.status == "rolled_back"
    assert item_result.verification.status == "failed"

    # Candidate must be restored to its original state.
    assert candidate_file.read_text(encoding="utf-8") == (
        "print('SUB_001 implementation')\n"
    )

    # Source submission must remain immutable.
    assert source_file.read_text(encoding="utf-8") == (
        "print('SUB_002 implementation')\n"
    )