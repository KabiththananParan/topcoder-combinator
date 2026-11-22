from pathlib import Path

from app.analysis.models import (
    Requirement,
    RequirementAssessment,
)
from app.code_mode.pipeline import CodeModePipeline
from app.decisions.decision_engine import DecisionEngine
from app.matrix.models import (
    MatrixEntry,
    RequirementMatrix,
)
from app.profiling.models import (
    BuildTestProfile,
    RepositoryStructure,
    SubmissionProfile,
    TechnologyProfile,
)
from app.provenance.models import ProvenanceLedger
from app.recommendation.models import (
    Recommendation,
    RecommendationSet,
)
from app.decisions.models import DecisionSet


def make_profile(
    submission_id: str,
) -> SubmissionProfile:
    return SubmissionProfile(
        submission_id=submission_id,
        root_path=Path("/tmp") / submission_id,
        repository_structure=RepositoryStructure(
            source_files=[
                "src/analysis.py",
                "src/service.py",
            ],
            test_files=[
                "tests/test_analysis.py",
            ],
            documentation_files=[
                "README.md",
            ],
            directories=[
                "src",
                "tests",
                "docs",
            ],
        ),
        technology=TechnologyProfile(
            languages=["Python"],
            frameworks=["FastAPI"],
            package_managers=["pip"],
        ),
        build_test=BuildTestProfile(
            build_commands=[
                "python -m compileall .",
            ],
            test_commands=[
                "pytest",
            ],
            package_manifests=[
                "requirements.txt",
            ],
        ),
        documentation_files=[
            "README.md",
        ],
        total_files=5,
        risks=[],
    )


def make_matrix() -> RequirementMatrix:
    assessment = RequirementAssessment(
        requirement_id="REQ_001",
        submission_id="SUB_001",
        assessment="complete",
        evidence=[
            {
                "path": "src/analysis.py",
                "startLine": 10,
                "endLine": 25,
                "symbol": "analyze",
                "matchedTerms": [
                    "analysis",
                ],
            },
            {
                "path": "tests/test_analysis.py",
                "startLine": 5,
                "endLine": 15,
                "symbol": "test_analysis",
                "matchedTerms": [
                    "analysis",
                ],
            },
        ],
        confidence=0.9,
        compatibility_risk="low",
    )

    return RequirementMatrix(
        challenge_id="CHALLENGE_001",
        entries=[
            MatrixEntry(
                requirement_id="REQ_001",
                requirement_title="Analysis",
                submission_id="SUB_001",
                assessment=assessment,
            ),
        ],
    )


def make_recommendations() -> RecommendationSet:
    return RecommendationSet(
        challenge_id="CHALLENGE_001",
        recommendations=[
            Recommendation(
                requirement_id="REQ_001",
                requirement_title="Analysis",
                recommended_submission_id="SUB_001",
                status="recommended",
                score=0.9,
                confidence=0.9,
                reasoning="Strong implementation.",
                compatibility_risk="low",
                evidence_refs=[
                    "EVIDENCE_000001",
                    "EVIDENCE_000002",
                ],
            ),
        ],
    )


def make_decisions() -> DecisionSet:
    engine = DecisionEngine()

    recommendations = make_recommendations()

    return engine.create_pending_decisions(
        recommendations
    )


def test_code_mode_pipeline_selects_base_and_builds_plan():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    recommendations = make_recommendations()
    decisions = make_decisions()

    ledger = ProvenanceLedger(
        challenge_id="CHALLENGE_001"
    )

    result = CodeModePipeline().plan(
        challenge_id="CHALLENGE_001",
        matrix=matrix,
        profiles=profiles,
        recommendations=recommendations,
        decisions=decisions,
        ledger=ledger,
    )

    assert result.base_selection.status == "selected"
    assert (
        result.base_selection.selected_submission_id
        == "SUB_001"
    )

    assert (
        result.transplant_plan.base_submission_id
        == "SUB_001"
    )

    assert len(result.transplant_plan.items) == 1

    item = result.transplant_plan.items[0]

    assert item.requirement_id == "REQ_001"
    assert item.action == "manual_review"
    assert item.evidence_refs == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
    ]


def test_code_mode_plan_records_transplant_planning_provenance():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    recommendations = make_recommendations()

    decisions = make_decisions()

    ledger = ProvenanceLedger(
        challenge_id="CHALLENGE_001"
    )

    result = CodeModePipeline().plan(
        challenge_id="CHALLENGE_001",
        matrix=matrix,
        profiles=profiles,
        recommendations=recommendations,
        decisions=decisions,
        ledger=ledger,
    )

    events = result.provenance.events

    assert not any(
        event.event_type == "transplant_planned"
        for event in events
    )
    
def test_code_mode_plan_records_approved_transplant():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
        "SUB_002": make_profile("SUB_002"),
    }

    recommendations = make_recommendations()

    decisions = DecisionEngine().select_alternative(
        make_decisions(),
        "REQ_001",
        alternative_submission_id="SUB_002",
        reason="SUB_002 provides stronger implementation evidence.",
    )

    ledger = ProvenanceLedger(
        challenge_id="CHALLENGE_001"
    )

    result = CodeModePipeline().plan(
        challenge_id="CHALLENGE_001",
        matrix=matrix,
        profiles=profiles,
        recommendations=recommendations,
        decisions=decisions,
        ledger=ledger,
    )

    item = result.transplant_plan.items[0]

    assert item.action == "transplant"
    assert item.source_submission_id == "SUB_002"
    assert item.target_submission_id == "SUB_001"