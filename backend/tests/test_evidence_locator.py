from pathlib import Path

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


def test_finds_customer_requirement_source_evidence():
    submission_root = (
        DEAL_SCOPING / "SUB_002"
    )

    locator = EvidenceLocator(
        submission_root
    )

    result = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "customer",
            "requirements",
            "grounding",
            "scope",
        ],
    )

    assert result.locations

    paths = [
        location.path
        for location in result.locations
    ]

    assert any(
        "grounding.ts" in path
        for path in paths
    )


def test_finds_documentation_evidence():
    submission_root = (
        DEAL_SCOPING / "SUB_002"
    )

    locator = EvidenceLocator(
        submission_root
    )

    result = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "customer",
            "requirements",
            "grounding",
        ],
    )

    paths = [
        location.path
        for location in result.locations
    ]

    assert any(
        "constraint-evidence.md" in path
        for path in paths
    )


def test_finds_test_evidence():
    submission_root = (
        DEAL_SCOPING / "SUB_002"
    )

    locator = EvidenceLocator(
        submission_root
    )

    result = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "grounding",
            "customer",
            "requirements",
        ],
    )

    paths = [
        location.path
        for location in result.locations
    ]

    assert any(
        "grounding.test.ts" in path
        for path in paths
    )


def test_handles_nested_repository_structure():
    submission_root = (
        DEAL_SCOPING / "SUB_001"
    )

    locator = EvidenceLocator(
        submission_root
    )

    result = locator.locate(
        submission_id="SUB_001",
        requirement_id="REQ_gbl6ad",
        search_terms=[
            "requirements",
            "scope",
            "customer",
        ],
    )

    assert result.locations

    for location in result.locations:
        assert not location.path.startswith(
            "/"
        )

        assert ".." not in Path(
            location.path
        ).parts


def test_empty_search_terms_returns_empty_result():
    submission_root = (
        DEAL_SCOPING / "SUB_002"
    )

    locator = EvidenceLocator(
        submission_root
    )

    result = locator.locate(
        submission_id="SUB_002",
        requirement_id="REQ_gbl6ad",
        search_terms=[],
    )

    assert result.locations == []
    assert result.relevance_score == 0.0