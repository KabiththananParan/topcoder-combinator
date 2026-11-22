from app.decisions.decision_engine import DecisionEngine
from app.matrix.models import RequirementMatrix
from app.profiling.models import SubmissionProfile
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

from .models import RecommendationPipelineResult


class RecommendationPipeline:
    """
    Orchestrates:

        matrix
          ↓
        evidence registration
          ↓
        recommendation
          ↓
        evidence enrichment
          ↓
        pending decisions
          ↓
        provenance
    """

    def __init__(
        self,
        recommendation_engine: RecommendationEngine,
        decision_engine: DecisionEngine,
        evidence_registration_service: EvidenceRegistrationService,
        evidence_enricher: RecommendationEvidenceEnricher,
    ):
        self.recommendation_engine = recommendation_engine
        self.decision_engine = decision_engine
        self.evidence_registration_service = (
            evidence_registration_service
        )
        self.evidence_enricher = evidence_enricher

    def run(
        self,
        challenge_id: str,
        matrix: RequirementMatrix,
        profiles: dict[str, SubmissionProfile],
        ledger_builder: ProvenanceLedgerBuilder,
    ) -> RecommendationPipelineResult:

        if matrix.challenge_id != challenge_id:
            raise ValueError(
                "Challenge ID mismatch between pipeline "
                "and requirement matrix."
            )

        # 1. Register matrix evidence.
        #
        # This creates canonical stable evidence IDs.
        evidence_refs = (
            self.evidence_registration_service
            .register_matrix_evidence(
                matrix=matrix,
                ledger_builder=ledger_builder,
            )
        )

        # 2. Generate recommendations.
        #
        # RecommendationEngine remains responsible only
        # for recommendation logic.
        recommendations = (
            self.recommendation_engine.recommend(
                matrix=matrix,
                profiles=profiles,
            )
        )

        # 3. Attach canonical evidence IDs.
        recommendations = (
            self.evidence_enricher.enrich(
                recommendations=recommendations,
                evidence_refs=evidence_refs,
            )
        )

        # 4. Create pending human/Copilot decisions.
        decisions = (
            self.decision_engine.create_pending_decisions(
                recommendations
            )
        )

        # 5. Record recommendation provenance.
        for recommendation in recommendations.recommendations:
            ledger_builder.record_recommendation(
                recommendation
            )

        # 6. Record decision provenance.
        for decision in decisions.decisions:
            ledger_builder.record_decision(
                decision
            )

        return RecommendationPipelineResult(
            challenge_id=challenge_id,
            matrix=matrix,
            recommendations=recommendations,
            decisions=decisions,
            provenance=ledger_builder.ledger,
        )