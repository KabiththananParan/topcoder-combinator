from pathlib import Path

from app.analysis import (
    Requirement,
    RequirementAnalyzer,
)
from app.evidence import EvidenceLocator


STARTER_PACK = (
    Path(__file__).resolve().parents[2]
    / "starter-pack"
)

DEAL_SCOPING = (
    STARTER_PACK
    / "challenges"
    / "AI_DEAL_SCOPING_ASSISTANT"
    / "submissions"
)


def test_requirement_with_strong_evidence():

    requirement = Requirement(
        requirement_id="REQ_gbl6ad",
        title="Structured Customer Requirements Analysis",
        priority="high",
        constraints=[
            "Customer requirements must be traceable",
            "Scope must be grounded in customer input",
        ],
    )

    locator = EvidenceLocator(
        DEAL_SCOPING / "SUB_002"
    )

    evidence = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "customer",
            "requirements",
            "grounding",
            "scope",
        ],
    )

    analyzer = RequirementAnalyzer()

    result = analyzer.analyze(
        requirement,
        evidence,
    )

    assert result.requirement_id == "REQ_gbl6ad"
    assert result.submission_id == "SUB_002"

    assert result.assessment in {
        "complete",
        "partial",
        "manual_review_required",
    }

    assert result.evidence
    assert result.confidence > 0


def test_missing_evidence():

    requirement = Requirement(
        requirement_id="REQ_test",
        title="Completely Nonexistent Capability",
        priority="high",
        constraints=[
            "This capability does not exist",
        ],
    )

    locator = EvidenceLocator(
        DEAL_SCOPING / "SUB_002"
    )

    evidence = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_test",
        search_terms=[
            "xyz_nonexistent_capability_12345",
        ],
    )

    analyzer = RequirementAnalyzer()

    result = analyzer.analyze(
        requirement,
        evidence,
    )

    assert result.assessment == "missing"
    assert result.confidence > 0
    assert result.evidence == []


def test_assessment_contains_source_locations():

    requirement = Requirement(
        requirement_id="REQ_gbl6ad",
        title="Customer Requirements Analysis",
        priority="high",
        constraints=[
            "customer requirements",
        ],
    )

    locator = EvidenceLocator(
        DEAL_SCOPING / "SUB_002"
    )

    evidence = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "customer",
            "requirements",
            "grounding",
        ],
    )

    analyzer = RequirementAnalyzer()

    result = analyzer.analyze(
        requirement,
        evidence,
    )

    assert result.evidence

    first = result.evidence[0]

    assert "path" in first
    assert "startLine" in first
    assert "endLine" in first
    assert "matchedTerms" in first


def test_confidence_is_bounded():

    requirement = Requirement(
        requirement_id="REQ_gbl6ad",
        title="Customer Requirements",
        priority="high",
    )

    locator = EvidenceLocator(
        DEAL_SCOPING / "SUB_002"
    )

    evidence = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "customer",
            "requirements",
        ],
    )

    result = RequirementAnalyzer().analyze(
        requirement,
        evidence,
    )

    assert 0.0 <= result.confidence <= 1.0