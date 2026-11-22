from app.decisions.models import Decision, DecisionSet
from app.decisions.persistence import DecisionPersistence


def test_decision_persistence_round_trip(tmp_path):
    original = DecisionSet(
        challenge_id="TEST_CHALLENGE",
        decisions=[
            Decision(
                requirement_id="REQ_001",
                requirement_title="Test requirement",
                state="accepted",
                selected_submission_id="SUB_001",
                recommended_submission_id="SUB_001",
                reason="Strongest evidence",
                recommendation_score=0.91,
                recommendation_confidence=0.88,
                evidence_refs=["EVIDENCE_001"],
                reviewer="copilot",
            )
        ],
    )

    persistence = DecisionPersistence(tmp_path)

    path = persistence.save(original)
    restored = persistence.load("TEST_CHALLENGE")

    assert path == tmp_path / "TEST_CHALLENGE" / "decisions.json"
    assert restored is not None
    assert restored.to_dict() == original.to_dict()
