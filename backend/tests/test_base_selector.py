from pathlib import Path

from app.code_mode import BaseSubmissionSelector
from app.matrix.models import MatrixEntry, RequirementMatrix
from app.analysis.models import RequirementAssessment
from app.profiling.models import (
    BuildTestProfile,
    RepositoryStructure,
    SubmissionProfile,
    TechnologyProfile,
)
from app.recommendation.models import RecommendationSet


def make_profile(
    submission_id: str,
    tests: bool = True,
    docs: bool = True,
):
    return SubmissionProfile(
        submission_id=submission_id,
        root_path=Path("/tmp") / submission_id,
        repository_structure=RepositoryStructure(
            source_files=[
                "src/app.ts",
                "src/service.ts",
            ],
            directories=[
                "src",
                "src/domain",
                "src/services",
                "src/tests",
                "docs",
            ],
        ),
        technology=TechnologyProfile(
            languages=["TypeScript"],
            frameworks=["React"],
            package_managers=["npm"],
        ),
        build_test=BuildTestProfile(
            build_commands=["npm run build"],
            test_commands=["npm test"] if tests else [],
            package_manifests=["package.json"],
        ),
        documentation_files=["README.md"] if docs else [],
        total_files=10,
        risks=[],
    )


def make_matrix():
    entries = [
        MatrixEntry(
            requirement_id="REQ_1",
            requirement_title="Requirement 1",
            submission_id="SUB_001",
            assessment=RequirementAssessment(
                requirement_id="REQ_1",
                submission_id="SUB_001",
                assessment="complete",
                confidence=0.9,
                compatibility_risk="low",
            ),
        ),
        MatrixEntry(
            requirement_id="REQ_2",
            requirement_title="Requirement 2",
            submission_id="SUB_001",
            assessment=RequirementAssessment(
                requirement_id="REQ_2",
                submission_id="SUB_001",
                assessment="complete",
                confidence=0.9,
                compatibility_risk="low",
            ),
        ),
        MatrixEntry(
            requirement_id="REQ_1",
            requirement_title="Requirement 1",
            submission_id="SUB_002",
            assessment=RequirementAssessment(
                requirement_id="REQ_1",
                submission_id="SUB_002",
                assessment="partial",
                confidence=0.5,
                compatibility_risk="medium",
            ),
        ),
        MatrixEntry(
            requirement_id="REQ_2",
            requirement_title="Requirement 2",
            submission_id="SUB_002",
            assessment=RequirementAssessment(
                requirement_id="REQ_2",
                submission_id="SUB_002",
                assessment="partial",
                confidence=0.5,
                compatibility_risk="medium",
            ),
        ),
    ]

    return RequirementMatrix(
        challenge_id="TEST_CHALLENGE",
        entries=entries,
    )


def test_selects_strongest_base():
    selector = BaseSubmissionSelector()

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[
            make_profile("SUB_001"),
            make_profile("SUB_002"),
        ],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    assert result.status == "selected"
    assert result.selected_submission_id == "SUB_001"
    assert result.score > 0
    assert result.confidence > 0


def test_does_not_use_final_score():
    selector = BaseSubmissionSelector()

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[
            make_profile("SUB_001"),
            make_profile("SUB_002"),
        ],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    assert "Final challenge score was not used." in result.reasoning


def test_no_profiles_returns_no_suitable_base():
    selector = BaseSubmissionSelector()

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    assert result.status == "no_suitable_base"
    assert result.selected_submission_id is None


def test_single_profile_can_be_selected():
    selector = BaseSubmissionSelector()

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[make_profile("SUB_001")],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    assert result.status == "selected"
    assert result.selected_submission_id == "SUB_001"


def test_weak_profile_has_risk():
    selector = BaseSubmissionSelector()

    profile = make_profile(
        "SUB_001",
        tests=False,
        docs=False,
    )

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[profile],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    assert result.status == "selected"
    assert "limited_test_evidence" in result.risks
    assert "limited_documentation" in result.risks


def test_serialization():
    selector = BaseSubmissionSelector()

    result = selector.select(
        challenge_id="TEST_CHALLENGE",
        matrix=make_matrix(),
        profiles=[make_profile("SUB_001")],
        recommendations=RecommendationSet(
            challenge_id="TEST_CHALLENGE",
            recommendations=[],
        ),
    )

    data = result.to_dict()

    assert data["challengeId"] == "TEST_CHALLENGE"
    assert data["selectedSubmissionId"] == "SUB_001"
    assert data["status"] == "selected"