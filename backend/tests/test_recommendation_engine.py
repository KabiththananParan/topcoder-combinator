from pathlib import Path

from app.analysis.models import RequirementAssessment
from app.matrix.models import MatrixEntry, RequirementMatrix
from app.profiling.models import (
    BuildTestProfile,
    RepositoryStructure,
    SubmissionProfile,
    TechnologyProfile,
)
from app.recommendation.recommendation_engine import RecommendationEngine


def make_profile(
    submission_id: str,
    *,
    with_tests: bool = True,
    with_docs: bool = True,
) -> SubmissionProfile:
    return SubmissionProfile(
        submission_id=submission_id,
        root_path=Path("/tmp") / submission_id,
        repository_structure=RepositoryStructure(
            root_files=["package.json"],
            directories=["src"],
            source_files=["src/main.ts"],
            test_files=["src/main.test.ts"] if with_tests else [],
            documentation_files=["README.md"] if with_docs else [],
            configuration_files=["package.json"],
        ),
        technology=TechnologyProfile(
            languages=["typescript"],
            frameworks=["react"],
            package_managers=["npm"],
            databases=[],
        ),
        build_test=BuildTestProfile(
            build_commands=["npm run build"],
            test_commands=["npm test"] if with_tests else [],
            package_manifests=["package.json"],
        ),
        documentation_files=["README.md"] if with_docs else [],
        total_files=10,
        risks=[],
    )


def make_entry(
    submission_id: str,
    *,
    assessment: str = "complete",
    evidence: list[dict] | None = None,
    compatibility_risk: str = "low",
) -> MatrixEntry:
    return MatrixEntry(
        requirement_id="REQ_001",
        requirement_title="Structured Customer Requirements Analysis",
        submission_id=submission_id,
        assessment=RequirementAssessment(
            requirement_id="REQ_001",
            submission_id=submission_id,
            assessment=assessment,
            evidence=evidence or [],
            reasoning="deterministic assessment",
            confidence=0.9,
            compatibility_risk=compatibility_risk,
            unresolved_conflicts=[],
        ),
    )


def make_matrix(
    *entries: MatrixEntry,
) -> RequirementMatrix:
    return RequirementMatrix(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        entries=list(entries),
    )


def test_recommends_stronger_candidate():
    matrix = make_matrix(
        make_entry(
            "SUB_001",
            evidence=[
                {
                    "evidenceType": "source",
                    "path": "src/requirements.ts",
                    "relevanceScore": 0.9,
                },
                {
                    "evidenceType": "test",
                    "path": "src/requirements.test.ts",
                    "relevanceScore": 0.9,
                },
            ],
        ),
        make_entry(
            "SUB_002",
            evidence=[
                {
                    "evidenceType": "source",
                    "path": "src/other.ts",
                    "relevanceScore": 0.5,
                },
            ],
        ),
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002", with_tests=False),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    recommendation = result.for_requirement("REQ_001")

    assert recommendation is not None
    assert recommendation.recommended_submission_id == "SUB_001"
    assert recommendation.score > 0.0
    assert recommendation.confidence > 0.0


def test_final_score_is_not_used():
    """
    The recommendation engine receives no finalScore at all.

    This test documents the architectural rule that review ranking
    must not determine technical superiority.
    """

    matrix = make_matrix(
        make_entry(
            "SUB_001",
            evidence=[
                {
                    "evidenceType": "test",
                    "path": "src/test.ts",
                    "relevanceScore": 0.9,
                }
            ],
        ),
        make_entry(
            "SUB_002",
            evidence=[
                {
                    "evidenceType": "source",
                    "path": "src/main.ts",
                    "relevanceScore": 0.8,
                }
            ],
        ),
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    recommendation = result.for_requirement("REQ_001")

    assert recommendation is not None
    assert recommendation.recommended_submission_id == "SUB_001"


def test_high_compatibility_risk_reduces_score():
    low_risk = make_entry(
        "SUB_001",
        evidence=[
            {
                "evidenceType": "source",
                "path": "src/main.ts",
                "relevanceScore": 0.8,
            }
        ],
        compatibility_risk="low",
    )

    high_risk = make_entry(
        "SUB_002",
        evidence=[
            {
                "evidenceType": "source",
                "path": "src/main.ts",
                "relevanceScore": 0.8,
            }
        ],
        compatibility_risk="high",
    )

    matrix = make_matrix(
        low_risk,
        high_risk,
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    recommendation = result.for_requirement("REQ_001")

    assert recommendation is not None
    assert recommendation.recommended_submission_id == "SUB_001"


def test_close_candidates_produce_tie():
    entry1 = make_entry(
        "SUB_001",
        evidence=[
            {
                "evidenceType": "source",
                "path": "src/a.ts",
                "relevanceScore": 0.8,
            }
        ],
    )

    entry2 = make_entry(
        "SUB_002",
        evidence=[
            {
                "evidenceType": "source",
                "path": "src/b.ts",
                "relevanceScore": 0.8,
            }
        ],
    )

    matrix = make_matrix(
        entry1,
        entry2,
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    recommendation = result.for_requirement("REQ_001")

    assert recommendation is not None
    assert recommendation.status == "tie"


def test_missing_requirement_has_no_suitable_source():
    matrix = RequirementMatrix(
        challenge_id="TEST_CHALLENGE",
        entries=[],
    )

    result = RecommendationEngine().recommend(
        matrix,
        {},
    )

    assert result.recommendations == []


def test_missing_profile_does_not_crash():
    matrix = make_matrix(
        make_entry("SUB_001"),
        make_entry("SUB_002"),
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    recommendation = result.for_requirement("REQ_001")

    assert recommendation is not None
    assert recommendation.recommended_submission_id == "SUB_001"


def test_to_dict_contains_required_fields():
    matrix = make_matrix(
        make_entry("SUB_001"),
    )

    profiles = {
        "SUB_001": make_profile("SUB_001"),
    }

    result = RecommendationEngine().recommend(
        matrix,
        profiles,
    )

    data = result.to_dict()

    assert data["challengeId"] == "AI_DEAL_SCOPING_ASSISTANT"
    assert len(data["recommendations"]) == 1

    item = data["recommendations"][0]

    assert item["requirementId"] == "REQ_001"
    assert item["recommendedSubmissionId"] == "SUB_001"
    assert "reasoning" in item
    assert "confidence" in item
    assert "compatibilityRisk" in item