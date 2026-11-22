from app.recommendation.evidence_enrichment import (
    RecommendationEvidenceEnricher,
)
from app.recommendation.models import (
    Recommendation,
    RecommendationSet,
)


def test_enricher_attaches_evidence_refs():
    recommendation = Recommendation(
        requirement_id="REQ_001",
        requirement_title="Customer Requirements Analysis",
        recommended_submission_id="SUB_001",
        status="recommended",
        score=0.91,
        confidence=0.88,
        reasoning="Strong evidence.",
        compatibility_risk="low",
    )

    recommendation_set = RecommendationSet(
        challenge_id="CHALLENGE_001",
        recommendations=[recommendation],
    )

    evidence_refs = {
        ("REQ_001", "SUB_001"): [
            "EVIDENCE_000001",
            "EVIDENCE_000002",
        ]
    }

    result = RecommendationEvidenceEnricher().enrich(
        recommendation_set,
        evidence_refs,
    )

    enriched = result.recommendations[0]

    assert enriched.evidence_refs == [
        "EVIDENCE_000001",
        "EVIDENCE_000002",
    ]


def test_enricher_does_not_create_missing_evidence_refs():
    recommendation = Recommendation(
        requirement_id="REQ_001",
        requirement_title="Customer Requirements Analysis",
        recommended_submission_id="SUB_001",
        status="recommended",
        score=0.91,
        confidence=0.88,
        reasoning="Strong evidence.",
        compatibility_risk="low",
    )

    recommendation_set = RecommendationSet(
        challenge_id="CHALLENGE_001",
        recommendations=[recommendation],
    )

    result = RecommendationEvidenceEnricher().enrich(
        recommendation_set,
        {},
    )

    assert result.recommendations[0].evidence_refs == []


def test_enricher_preserves_recommendation_without_selected_submission():
    recommendation = Recommendation(
        requirement_id="REQ_001",
        requirement_title="Customer Requirements Analysis",
        recommended_submission_id=None,
        status="no_suitable_source",
        score=0.0,
        confidence=0.0,
        reasoning="No suitable source.",
        compatibility_risk="unknown",
    )

    recommendation_set = RecommendationSet(
        challenge_id="CHALLENGE_001",
        recommendations=[recommendation],
    )

    result = RecommendationEvidenceEnricher().enrich(
        recommendation_set,
        {
            ("REQ_001", "SUB_001"): [
                "EVIDENCE_000001",
            ]
        },
    )

    enriched = result.recommendations[0]

    assert enriched.recommended_submission_id is None
    assert enriched.evidence_refs == []