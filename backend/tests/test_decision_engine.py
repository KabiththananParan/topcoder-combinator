from app.decisions.decision_engine import DecisionEngine
from app.recommendation.models import (
    Recommendation,
    RecommendationSet,
)


def make_recommendations() -> RecommendationSet:
    return RecommendationSet(
        challenge_id="AI_DEAL_SCOPING_ASSISTANT",
        recommendations=[
            Recommendation(
                requirement_id="REQ_001",
                requirement_title="Requirements Analysis",
                recommended_submission_id="SUB_002",
                status="recommended",
                score=0.87,
                confidence=0.91,
                reasoning="Strong evidence and test coverage.",
                compatibility_risk="low",
                evidence_summary=[
                    "source: src/analysis/grounding.ts",
                    "test: src/analysis/grounding.test.ts",
                ],
                alternatives=["SUB_001"],
            ),
            Recommendation(
                requirement_id="REQ_002",
                requirement_title="PRD Generation",
                recommended_submission_id="SUB_001",
                status="recommended",
                score=0.82,
                confidence=0.84,
                reasoning="Strong PRD implementation.",
                compatibility_risk="medium",
                evidence_summary=[
                    "source: src/prd.ts",
                ],
                alternatives=["SUB_002"],
            ),
        ],
    )


def test_creates_pending_decisions():
    engine = DecisionEngine()

    result = engine.create_pending_decisions(
        make_recommendations()
    )

    assert len(result.decisions) == 2

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "pending"
    assert decision.recommended_submission_id == "SUB_002"
    assert decision.selected_submission_id is None
    assert decision.recommendation_score == 0.87
    assert decision.recommendation_confidence == 0.91


def test_accept_selects_recommended_submission():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.accept(
        decisions,
        "REQ_001",
        reason="Approved after reviewing evidence.",
        reviewer="human-reviewer",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "accepted"
    assert decision.selected_submission_id == "SUB_002"
    assert decision.reviewer == "human-reviewer"


def test_reject_requires_reason():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    try:
        engine.reject(
            decisions,
            "REQ_001",
            reason="",
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_reject_does_not_select_submission():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.reject(
        decisions,
        "REQ_001",
        reason="Evidence is insufficient.",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "rejected"
    assert decision.selected_submission_id is None
    assert decision.reason == "Evidence is insufficient."


def test_select_alternative():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.select_alternative(
        decisions,
        "REQ_001",
        "SUB_001",
        reason="SUB_001 integrates better with the selected base.",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "alternative_selected"
    assert decision.selected_submission_id == "SUB_001"
    assert decision.alternative_submission_id == "SUB_001"


def test_cannot_select_recommended_submission_as_alternative():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    try:
        engine.select_alternative(
            decisions,
            "REQ_001",
            "SUB_002",
            reason="Testing invalid alternative.",
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_block():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.block(
        decisions,
        "REQ_001",
        reason="Security review is required first.",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "blocked"
    assert decision.selected_submission_id is None


def test_manual_review():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.manual_review(
        decisions,
        "REQ_001",
        reason="Conflicting evidence requires human review.",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "manual_review"


def test_unresolved():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.unresolved(
        decisions,
        "REQ_001",
        reason="No sufficiently reliable source exists.",
    )

    decision = result.for_requirement("REQ_001")

    assert decision is not None
    assert decision.state == "unresolved"


def test_decisions_are_immutable():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.accept(
        decisions,
        "REQ_001",
        reason="Approved.",
    )

    original = decisions.for_requirement("REQ_001")
    updated = result.for_requirement("REQ_001")

    assert original is not None
    assert updated is not None

    assert original.state == "pending"
    assert updated.state == "accepted"


def test_to_dict():
    engine = DecisionEngine()

    decisions = engine.create_pending_decisions(
        make_recommendations()
    )

    result = engine.accept(
        decisions,
        "REQ_001",
        reason="Approved.",
    )

    data = result.to_dict()

    assert data["challengeId"] == "AI_DEAL_SCOPING_ASSISTANT"
    assert len(data["decisions"]) == 2

    item = data["decisions"][0]

    assert item["requirementId"] == "REQ_001"
    assert item["state"] == "accepted"
    assert item["selectedSubmissionId"] == "SUB_002"
    assert item["recommendedSubmissionId"] == "SUB_002"
    assert item["reason"] == "Approved."