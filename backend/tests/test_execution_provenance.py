from app.provenance.execution_provenance import ExecutionProvenanceRecorder
from app.provenance.models import ProvenanceLedger


def test_successful_transplant_lifecycle():
    ledger = ProvenanceLedger(challenge_id="TEST_CHALLENGE")
    recorder = ExecutionProvenanceRecorder(ledger)

    planned = recorder.record_transplant_planned(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        reason="Approved source.",
    )

    applied = recorder.record_transplant_applied(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        source_path="src/a.py",
        target_path="src/a.py",
        related_event_ids=[planned.event_id],
    )

    started = recorder.record_verification_started(
        requirement_id="REQ_1",
        related_event_ids=[applied.event_id],
    )

    completed = recorder.record_verification_completed(
        requirement_id="REQ_1",
        related_event_ids=[started.event_id],
        metadata={
            "status": "passed",
        },
    )

    events = recorder.get_ledger().events

    assert len(events) == 4

    assert [event.event_type for event in events] == [
        "transplant_planned",
        "transplant_applied",
        "verification_started",
        "verification_completed",
    ]

    assert applied.related_event_ids == [planned.event_id]
    assert started.related_event_ids == [applied.event_id]
    assert completed.related_event_ids == [started.event_id]


def test_failed_verification_and_rollback():
    ledger = ProvenanceLedger(challenge_id="TEST_CHALLENGE")
    recorder = ExecutionProvenanceRecorder(ledger)

    planned = recorder.record_transplant_planned(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        reason="Approved source.",
    )

    applied = recorder.record_transplant_applied(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        source_path="src/a.py",
        target_path="src/a.py",
        related_event_ids=[planned.event_id],
    )

    started = recorder.record_verification_started(
        requirement_id="REQ_1",
        related_event_ids=[applied.event_id],
    )

    failed = recorder.record_verification_failed(
        requirement_id="REQ_1",
        related_event_ids=[started.event_id],
        metadata={
            "status": "failed",
            "errors": ["unit test failed"],
        },
    )

    rollback = recorder.record_rollback(
        requirement_id="REQ_1",
        related_event_ids=[failed.event_id],
    )

    events = recorder.get_ledger().events

    assert [event.event_type for event in events] == [
        "transplant_planned",
        "transplant_applied",
        "verification_started",
        "verification_failed",
        "rollback",
    ]

    assert rollback.related_event_ids == [failed.event_id]


def test_ledger_is_immutable_style():
    ledger = ProvenanceLedger(challenge_id="TEST_CHALLENGE")
    recorder = ExecutionProvenanceRecorder(ledger)

    original_ledger = recorder.get_ledger()

    recorder.record_transplant_planned(
        requirement_id="REQ_1",
        source_submission_id="SUB_001",
        target_submission_id="SUB_002",
        reason="Approved.",
    )

    new_ledger = recorder.get_ledger()

    assert original_ledger is not new_ledger
    assert len(original_ledger.events) == 0
    assert len(new_ledger.events) == 1