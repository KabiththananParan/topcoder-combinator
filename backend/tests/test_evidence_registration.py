from app.analysis.models import (
    Requirement,
    RequirementAssessment,
)
from app.matrix.models import (
    MatrixEntry,
    RequirementMatrix,
)
from app.provenance.evidence_registration import (
    EvidenceRegistrationService,
)
from app.provenance.provenance_ledger import (
    ProvenanceLedgerBuilder,
)


def test_register_matrix_evidence_creates_stable_ids():
    requirement = Requirement(
        requirement_id="REQ_001",
        title="Customer Requirements Analysis",
        priority="high",
    )

    assessment = RequirementAssessment(
        requirement_id="REQ_001",
        submission_id="SUB_001",
        assessment="partial",
        evidence=[
            {
                "path": "src/analysis.py",
                "startLine": 10,
                "endLine": 25,
                "symbol": "analyze_requirements",
                "matchedTerms": ["requirements"],
            },
            {
                "path": "tests/analysis.test.py",
                "startLine": 5,
                "endLine": 20,
                "symbol": "test_analysis",
                "matchedTerms": ["requirements"],
            },
        ],
        reasoning="Evidence found.",
        confidence=0.75,
    )

    matrix = RequirementMatrix(
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

    builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    service = EvidenceRegistrationService()

    refs = service.register_matrix_evidence(
        matrix=matrix,
        ledger_builder=builder,
    )

    assert refs == {
        ("REQ_001", "SUB_001"): [
            "EVIDENCE_000001",
            "EVIDENCE_000002",
        ]
    }


def test_registered_evidence_is_stored_in_ledger():
    assessment = RequirementAssessment(
        requirement_id="REQ_001",
        submission_id="SUB_001",
        assessment="complete",
        evidence=[
            {
                "path": "src/analysis.py",
                "startLine": 10,
                "endLine": 20,
                "symbol": "analyze",
                "matchedTerms": ["analysis"],
            }
        ],
    )

    matrix = RequirementMatrix(
        challenge_id="CHALLENGE_001",
        entries=[
            MatrixEntry(
                requirement_id="REQ_001",
                requirement_title="Analysis",
                submission_id="SUB_001",
                assessment=assessment,
            )
        ],
    )

    builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    service = EvidenceRegistrationService()

    service.register_matrix_evidence(
        matrix,
        builder,
    )

    ledger = builder.ledger

    assert len(ledger.evidence) == 1

    evidence = ledger.evidence[0]

    assert evidence.evidence_id == "EVIDENCE_000001"
    assert evidence.submission_id == "SUB_001"
    assert evidence.requirement_id == "REQ_001"
    assert evidence.path == "src/analysis.py"
    assert evidence.start_line == 10
    assert evidence.end_line == 20
    assert evidence.symbol == "analyze"
    assert evidence.evidence_type == "source"


def test_registration_creates_evidence_found_events():
    assessment = RequirementAssessment(
        requirement_id="REQ_001",
        submission_id="SUB_001",
        assessment="complete",
        evidence=[
            {
                "path": "src/analysis.py",
                "startLine": 10,
                "endLine": 20,
            }
        ],
    )

    matrix = RequirementMatrix(
        challenge_id="CHALLENGE_001",
        entries=[
            MatrixEntry(
                requirement_id="REQ_001",
                requirement_title="Analysis",
                submission_id="SUB_001",
                assessment=assessment,
            )
        ],
    )

    builder = ProvenanceLedgerBuilder(
        challenge_id="CHALLENGE_001"
    )

    service = EvidenceRegistrationService()

    service.register_matrix_evidence(
        matrix,
        builder,
    )

    ledger = builder.ledger

    assert len(ledger.events) == 1

    event = ledger.events[0]

    assert event.event_type == "evidence_found"
    assert event.evidence_ids == [
        "EVIDENCE_000001"
    ]