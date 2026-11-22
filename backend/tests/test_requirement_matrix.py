from pathlib import Path

from app.analysis import Requirement
from app.matrix import RequirementMatrixBuilder


STARTER_PACK = (
    Path(__file__).resolve().parents[2]
    / "starter-pack"
)

CHALLENGE_ROOT = (
    STARTER_PACK
    / "challenges"
    / "AI_DEAL_SCOPING_ASSISTANT"
)


def test_builds_complete_matrix():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title=(
                "Structured Customer Requirements Analysis"
            ),
            priority="high",
            constraints=[
                "Customer requirements must be traceable",
                "Scope must be grounded in customer input",
            ],
        ),
        Requirement(
            requirement_id="REQ_r2gz0o",
            title=(
                "Scope Review and Controlled Generation"
            ),
            priority="high",
            constraints=[
                "User review must occur before generation",
            ],
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=[
            "SUB_001",
            "SUB_002",
        ],
    )

    assert len(matrix.entries) == 4


def test_matrix_contains_every_requirement_submission_pair():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title="Customer Requirements Analysis",
            priority="high",
        ),
        Requirement(
            requirement_id="REQ_r2gz0o",
            title="Scope Review",
            priority="high",
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=[
            "SUB_001",
            "SUB_002",
        ],
    )

    pairs = {
        (
            entry.requirement_id,
            entry.submission_id,
        )
        for entry in matrix.entries
    }

    expected = {
        ("REQ_gbl6ad", "SUB_001"),
        ("REQ_gbl6ad", "SUB_002"),
        ("REQ_r2gz0o", "SUB_001"),
        ("REQ_r2gz0o", "SUB_002"),
    }

    assert pairs == expected


def test_matrix_preserves_requirement_ids():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title="Structured Customer Requirements Analysis",
            priority="high",
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=["SUB_001"],
    )

    assert (
        matrix.entries[0].requirement_id
        == "REQ_gbl6ad"
    )


def test_matrix_can_filter_by_requirement():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title="Customer Requirements Analysis",
            priority="high",
        ),
        Requirement(
            requirement_id="REQ_r2gz0o",
            title="Scope Review",
            priority="high",
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=[
            "SUB_001",
            "SUB_002",
        ],
    )

    result = matrix.for_requirement(
        "REQ_gbl6ad"
    )

    assert len(result) == 2

    assert {
        entry.submission_id
        for entry in result
    } == {
        "SUB_001",
        "SUB_002",
    }


def test_matrix_can_filter_by_submission():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title="Customer Requirements Analysis",
            priority="high",
        ),
        Requirement(
            requirement_id="REQ_r2gz0o",
            title="Scope Review",
            priority="high",
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=[
            "SUB_001",
            "SUB_002",
        ],
    )

    result = matrix.for_submission(
        "SUB_001"
    )

    assert len(result) == 2

    assert all(
        entry.submission_id == "SUB_001"
        for entry in result
    )


def test_matrix_can_be_serialized():

    requirements = [
        Requirement(
            requirement_id="REQ_gbl6ad",
            title="Customer Requirements Analysis",
            priority="high",
        ),
    ]

    builder = RequirementMatrixBuilder(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        challenge_root=CHALLENGE_ROOT,
    )

    matrix = builder.build(
        requirements=requirements,
        submission_ids=["SUB_002"],
    )

    data = matrix.to_dict()

    assert data["challengeId"] == (
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    assert len(data["entries"]) == 1

    assert (
        data["entries"][0]["requirementId"]
        == "REQ_gbl6ad"
    )