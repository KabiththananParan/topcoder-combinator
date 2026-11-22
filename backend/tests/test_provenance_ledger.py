from app.matrix.models import MatrixEntry
from app.analysis.models import RequirementAssessment
from app.provenance.provenance_ledger import (
    ProvenanceLedgerBuilder,
)
from app.recommendation.models import Recommendation
from app.decisions.models import Decision


def make_matrix_entry() -> MatrixEntry:
    return MatrixEntry(
        requirement_id="REQ_001",
        requirement_title="Requirements Analysis",
        submission_id="SUB_001",
        assessment=RequirementAssessment(
            requirement_id="REQ_001",
            submission_id="SUB_001",
            assessment="complete",
            evidence=[],
            reasoning="Requirement is strongly supported.",
            confidence=0.9,
            compatibility_risk="low",
            unresolved_conflicts=[],
        ),
    )


def test_add_evidence():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    evidence_id = builder.add_evidence(
        submission_id="SUB_001",
        requirement_id="REQ_001",
        path="src/analysis/grounding.ts",
        evidence_type="source",
        start_line=10,
        end_line=30,
        symbol="groundScopeItems",
        source_hash="abc123",
        description="Grounds customer requirements.",
    )

    evidence = builder.ledger.evidence_by_id(
        evidence_id
    )

    assert evidence is not None
    assert evidence.evidence_id == evidence_id
    assert evidence.submission_id == "SUB_001"
    assert evidence.path == "src/analysis/grounding.ts"
    assert evidence.start_line == 10
    assert evidence.end_line == 30
    assert evidence.symbol == "groundScopeItems"
    assert evidence.source_hash == "abc123"


def test_add_evidence_creates_event():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    evidence_id = builder.add_evidence(
        submission_id="SUB_001",
        requirement_id="REQ_001",
        path="src/main.ts",
        evidence_type="source",
    )

    events = builder.ledger.events

    assert len(events) == 1
    assert events[0].event_type == "evidence_found"
    assert events[0].evidence_ids == [evidence_id]


def test_record_matrix_assessment():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    event_id = builder.record_matrix_assessment(
        make_matrix_entry()
    )

    event = builder.ledger.events[0]

    assert event_id == event.event_id
    assert event.event_type == "assessment_created"
    assert event.requirement_id == "REQ_001"
    assert event.submission_id == "SUB_001"
    assert event.metadata["assessment"] == "complete"
    assert event.metadata["confidence"] == 0.9


def test_record_recommendation_links_evidence():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    evidence_id = builder.add_evidence(
        submission_id="SUB_002",
        requirement_id="REQ_001",
        path="src/analysis.ts",
        evidence_type="source",
    )

    recommendation = Recommendation(
        requirement_id="REQ_001",
        requirement_title="Requirements Analysis",
        recommended_submission_id="SUB_002",
        status="recommended",
        score=0.91,
        confidence=0.88,
        reasoning="Strong implementation and evidence.",
        compatibility_risk="low",
        evidence_summary=[
            "source: src/analysis.ts",
        ],
        alternatives=["SUB_001"],
    )

    event_id = builder.record_recommendation(
        recommendation
    )

    event = builder.ledger.events[-1]

    assert event_id == event.event_id
    assert event.event_type == "recommendation_created"
    assert event.submission_id == "SUB_002"
    assert event.evidence_ids == [evidence_id]
    assert event.metadata["score"] == 0.91


def test_record_decision():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    decision = Decision(
        requirement_id="REQ_001",
        requirement_title="Requirements Analysis",
        state="accepted",
        selected_submission_id="SUB_002",
        recommended_submission_id="SUB_002",
        reason="Approved by reviewer.",
        recommendation_score=0.91,
        recommendation_confidence=0.88,
        evidence_refs=["EVIDENCE_000001"],
        reviewer="reviewer-1",
    )

    event_id = builder.record_decision(
        decision
    )

    event = builder.ledger.events[0]

    assert event_id == event.event_id
    assert event.event_type == "decision_created"
    assert event.submission_id == "SUB_002"
    assert event.actor == "reviewer-1"
    assert event.metadata["state"] == "accepted"


def test_record_source_selection():
    builder = ProvenanceLedgerBuilder(
        "AI_DEAL_SCOPING_ASSISTANT"
    )

    decision_event = builder.record_event(
        event_type="decision_created",
        requirement_id="REQ_001",
        submission_id="SUB_002",
        reason="Accepted.",
    )

    selection_event = builder.record_source_selected(
        requirement_id="REQ_001",
        submission_id="SUB_002",
        decision_event_id=decision_event,
        reason="Accepted source for implementation.",
    )

    event = builder.ledger.events[-1]

    assert selection_event == event.event_id
    assert event.event_type == "source_selected"
    assert event.submission_id == "SUB_002"
    assert event.related_event_ids == [
        decision_event
    ]


def test_events_are_ordered():
    builder = ProvenanceLedgerBuilder(
        "TEST_CHALLENGE"
    )

    first = builder.record_event(
        event_type="assessment_created"
    )

    second = builder.record_event(
        event_type="recommendation_created"
    )

    third = builder.record_event(
        event_type="decision_created"
    )

    assert [first, second, third] == [
        "EVENT_000001",
        "EVENT_000002",
        "EVENT_000003",
    ]


def test_requirement_event_filter():
    builder = ProvenanceLedgerBuilder(
        "TEST_CHALLENGE"
    )

    builder.record_event(
        event_type="assessment_created",
        requirement_id="REQ_001",
    )

    builder.record_event(
        event_type="recommendation_created",
        requirement_id="REQ_002",
    )

    builder.record_event(
        event_type="decision_created",
        requirement_id="REQ_001",
    )

    events = builder.ledger.events_for_requirement(
        "REQ_001"
    )

    assert len(events) == 2
    assert all(
        event.requirement_id == "REQ_001"
        for event in events
    )


def test_submission_event_filter():
    builder = ProvenanceLedgerBuilder(
        "TEST_CHALLENGE"
    )

    builder.record_event(
        event_type="evidence_found",
        submission_id="SUB_001",
    )

    builder.record_event(
        event_type="evidence_found",
        submission_id="SUB_002",
    )

    events = builder.ledger.events_for_submission(
        "SUB_001"
    )

    assert len(events) == 1
    assert events[0].submission_id == "SUB_001"


def test_to_dict():
    builder = ProvenanceLedgerBuilder(
        "TEST_CHALLENGE"
    )

    builder.add_evidence(
        submission_id="SUB_001",
        requirement_id="REQ_001",
        path="src/main.ts",
        evidence_type="source",
    )

    data = builder.ledger.to_dict()

    assert data["challengeId"] == "TEST_CHALLENGE"
    assert len(data["evidence"]) == 1
    assert len(data["events"]) == 1

    assert data["evidence"][0]["submissionId"] == "SUB_001"
    assert data["events"][0]["eventType"] == "evidence_found"