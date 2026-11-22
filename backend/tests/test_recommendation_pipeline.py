from pathlib import Path

from app.analysis.models import (
    Requirement,
    RequirementAssessment,
)
from app.decisions.decision_engine import DecisionEngine
from app.matrix.models import (
    MatrixEntry,
    RequirementMatrix,
)
from app.pipeline.recommendation_pipeline import (
    RecommendationPipeline,
)
from app.profiling.models import (
    BuildTestProfile,
    RepositoryStructure,
    SubmissionProfile,
    TechnologyProfile,
)
from app.provenance.evidence_registration import (
    EvidenceRegistrationService,
)
from app.provenance.provenance_ledger import (
    ProvenanceLedgerBuilder,
)
from app.recommendation.evidence_enrichment import (
    RecommendationEvidenceEnricher,
)
from app.recommendation.recommendation_engine import (
    RecommendationEngine,
)


def make_profile(
    submission_id: str,
) -> SubmissionProfile:
    return SubmissionProfile(
        submission_id=submission_id,
        root_path=Path("/tmp") / submission_id,
        repository_structure=RepositoryStructure(
            source_files=["src/analysis.py"],
            test_files=["tests/test_analysis.py"],
            documentation_files=["README.md"],
        ),
        technology=TechnologyProfile(
            languages=["Python"],
            frameworks=["FastAPI"],
            package_managers=["pip"],
        ),
        build_test=BuildTestProfile(
            build_commands=["python -m compileall ."],
            test_commands=["pytest"],
            package_manifests=["requirements.txt"],
        ),
        documentation_files=["README.md"],
        total_files=3,
        risks=[],
    )


def make_matrix() -> RequirementMatrix:
    requirement = Requirement(
        requirement_id="REQ_001",
        title="Customer Requirements Analysis",
        priority="high",
    )

    assessment = RequirementAssessment(
        requirement_id="REQ_001",
        submission_id="SUB_001",
        assessment="complete",
        evidence=[
            {
                "path": "src/analysis.py",
                "startLine": 10,
                "endLine": 25,
                "symbol": "analyze_requirements",
                "matchedTerms": [
                    "requirements",
                    "analysis",
                ],
            },
            {
                "path": "tests/test_analysis.py",
                "startLine": 5,
                "endLine": 20,
                "symbol": "test_analysis",
                "matchedTerms": [
                    "requirements",
                ],
            },
            {
                "path": "README.md",
                "startLine": 30,
                "endLine": 40,
                "symbol": None,
                "matchedTerms": [
                    "requirements",
                ],
            },
        ],
        reasoning="Strong implementation evidence.",
        confidence=0.9,
        compatibility_risk="low",
    )

    return RequirementMatrix(
        challenge_id="CHALLENGE_001",
        entries=[
            MatrixEntry(
                requirement_id=requirement.requirement_id,
                requirement_title=requirement.title,
                submission_id="SUB_001",
                assessment=assessment,
            )
        ],
    )


def make_pipeline() -> RecommendationPipeline:
    return RecommendationPipeline(
        recommendation_engine=RecommendationEngine(),
        decision_engine=DecisionEngine(),
        evidence_registration_service=(
            EvidenceRegistrationService()
        ),
        evidence_enricher=(
            RecommendationEvidenceEnricher()
        ),
    )


def test_pipeline_connects_all_stages():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
    }

    ledger_builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    result = make_pipeline().run(
        challenge_id="CHALLENGE_001",
        matrix=matrix,
        profiles=profiles,
        ledger_builder=ledger_builder,
    )

    assert result.challenge_id == "CHALLENGE_001"

    assert len(result.recommendations.recommendations) == 1
    assert len(result.decisions.decisions) == 1

    recommendation = (
        result.recommendations.recommendations[0]
    )

    assert recommendation.requirement_id == "REQ_001"
    assert recommendation.recommended_submission_id == "SUB_001"

    assert recommendation.evidence_refs == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
        "EVIDENCE_000003",
    ]

    decision = result.decisions.decisions[0]

    assert decision.requirement_id == "REQ_001"
    assert decision.state == "pending"
    assert decision.recommended_submission_id == "SUB_001"

    assert decision.evidence_refs == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
        "EVIDENCE_000003",
    ]


def test_pipeline_records_provenance():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
    }

    ledger_builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    result = make_pipeline().run(
        challenge_id="CHALLENGE_001",
        matrix=matrix,
        profiles=profiles,
        ledger_builder=ledger_builder,
    )

    evidence_events = [
        event
        for event in result.provenance.events
        if event.event_type == "evidence_found"
    ]

    recommendation_events = [
        event
        for event in result.provenance.events
        if event.event_type == "recommendation_created"
    ]

    decision_events = [
        event
        for event in result.provenance.events
        if event.event_type == "decision_created"
    ]

    assert len(evidence_events) == 3
    assert len(recommendation_events) == 1
    assert len(decision_events) == 1

    recommendation_event = recommendation_events[0]

    assert recommendation_event.evidence_ids == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
        "EVIDENCE_000003",
    ]

    decision_event = decision_events[0]

    assert decision_event.evidence_ids == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
        "EVIDENCE_000003",
    ]


def test_pipeline_rejects_challenge_id_mismatch():
    matrix = make_matrix()

    profiles = {
        "SUB_001": make_profile("SUB_001"),
    }

    ledger_builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    try:
        make_pipeline().run(
            challenge_id="CHALLENGE_999",
            matrix=matrix,
            profiles=profiles,
            ledger_builder=ledger_builder,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Challenge ID mismatch" in str(exc)