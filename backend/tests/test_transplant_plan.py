from app.code_mode import (
    TransplantPlanBuilder,
)
from app.decisions.models import Decision, DecisionSet


def make_decision_set(*decisions):
    return DecisionSet(
        challenge_id="TEST_CHALLENGE",
        decisions=list(decisions),
    )


def test_accepted_different_source_creates_transplant():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="accepted",
        selected_submission_id="SUB_001",
        evidence_refs=["EVIDENCE_000001"],
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    item = plan.items[0]

    assert item.action == "transplant"
    assert item.source_submission_id == "SUB_001"
    assert item.target_submission_id == "SUB_002"
    assert item.evidence_refs == ["EVIDENCE_000001"]


def test_accepted_base_source_keeps_base():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="accepted",
        selected_submission_id="SUB_002",
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    assert plan.items[0].action == "keep_base"


def test_rejected_decision_is_blocked():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="rejected",
        reason="Do not use this implementation.",
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    assert plan.items[0].action == "blocked"


def test_pending_decision_requires_manual_review():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="pending",
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    assert plan.items[0].action == "manual_review"


def test_alternative_selected_creates_transplant():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="alternative_selected",
        alternative_submission_id="SUB_001",
        reason="Alternative is preferred.",
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    item = plan.items[0]

    assert item.action == "transplant"
    assert item.source_submission_id == "SUB_001"


def test_unknown_submission_is_rejected():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="accepted",
        selected_submission_id="SUB_999",
    )

    try:
        TransplantPlanBuilder().build(
            challenge_id="TEST_CHALLENGE",
            base_submission_id="SUB_002",
            decisions=make_decision_set(decision),
            submission_ids=["SUB_001", "SUB_002"],
        )
    except ValueError as exc:
        assert "does not belong to challenge" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_invalid_base_is_rejected():
    try:
        TransplantPlanBuilder().build(
            challenge_id="TEST_CHALLENGE",
            base_submission_id="SUB_999",
            decisions=make_decision_set(),
            submission_ids=["SUB_001", "SUB_002"],
        )
    except ValueError as exc:
        assert "Base submission does not belong" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_plan_serialization():
    decision = Decision(
        requirement_id="REQ_1",
        requirement_title="Requirement 1",
        state="accepted",
        selected_submission_id="SUB_001",
    )

    plan = TransplantPlanBuilder().build(
        challenge_id="TEST_CHALLENGE",
        base_submission_id="SUB_002",
        decisions=make_decision_set(decision),
        submission_ids=["SUB_001", "SUB_002"],
    )

    data = plan.to_dict()

    assert data["challengeId"] == "TEST_CHALLENGE"
    assert data["baseSubmissionId"] == "SUB_002"
    assert data["items"][0]["action"] == "transplant"