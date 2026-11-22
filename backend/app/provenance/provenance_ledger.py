from dataclasses import replace

from app.decisions.models import Decision
from app.evidence.models import EvidenceCandidate
from app.matrix.models import MatrixEntry
from app.recommendation.models import Recommendation

from .models import (
    EvidenceRef,
    ProvenanceEvent,
    ProvenanceLedger,
)


class ProvenanceLedgerBuilder:
    """
    Builds an immutable-style provenance ledger.

    The original submissions are never modified.

    The ledger records:
        evidence
        assessment
        recommendation
        decision
        source selection
        later execution / verification events
    """

    def __init__(
        self,
        challenge_id: str,
    ) -> None:
        self._ledger = ProvenanceLedger(
            challenge_id=challenge_id,
        )

        self._event_counter = 0
        self._evidence_counter = 0

    @property
    def ledger(self) -> ProvenanceLedger:
        return self._ledger

    def add_evidence(
        self,
        *,
        submission_id: str,
        requirement_id: str,
        path: str,
        evidence_type: str,
        start_line: int | None = None,
        end_line: int | None = None,
        symbol: str | None = None,
        source_hash: str | None = None,
        description: str = "",
    ) -> str:
        self._evidence_counter += 1

        evidence_id = (
            f"EVIDENCE_{self._evidence_counter:06d}"
        )

        evidence = EvidenceRef(
            evidence_id=evidence_id,
            submission_id=submission_id,
            requirement_id=requirement_id,
            path=path,
            start_line=start_line,
            end_line=end_line,
            symbol=symbol,
            evidence_type=evidence_type,
            source_hash=source_hash,
            description=description,
        )

        evidence_items = [
            *self._ledger.evidence,
            evidence,
        ]

        self._ledger = replace(
            self._ledger,
            evidence=evidence_items,
        )

        self.record_event(
            event_type="evidence_found",
            requirement_id=requirement_id,
            submission_id=submission_id,
            evidence_ids=[evidence_id],
            reason=description,
        )

        return evidence_id

    def record_matrix_assessment(
        self,
        entry: MatrixEntry,
    ) -> str:
        return self.record_event(
            event_type="assessment_created",
            requirement_id=entry.requirement_id,
            submission_id=entry.submission_id,
            reason=entry.assessment.reasoning,
            metadata={
                "assessment": entry.assessment.assessment,
                "confidence": entry.assessment.confidence,
                "compatibilityRisk": (
                    entry.assessment.compatibility_risk
                ),
            },
        )

    def record_recommendation(
        self,
        recommendation: Recommendation,
    ) -> str:
        return self.record_event(
            event_type="recommendation_created",
            requirement_id=recommendation.requirement_id,
            submission_id=(
                recommendation.recommended_submission_id
            ),
            evidence_ids=self._find_evidence_ids(
                recommendation.requirement_id,
            ),
            reason=recommendation.reasoning,
            metadata={
                "recommendedSubmissionId": (
                    recommendation.recommended_submission_id
                ),
                "score": recommendation.score,
                "confidence": recommendation.confidence,
                "compatibilityRisk": (
                    recommendation.compatibility_risk
                ),
                "status": recommendation.status,
            },
        )

    def record_decision(
        self,
        decision: Decision,
    ) -> str:
        return self.record_event(
            event_type="decision_created",
            requirement_id=decision.requirement_id,
            submission_id=decision.selected_submission_id,
            evidence_ids=list(decision.evidence_refs),
            reason=decision.reason,
            actor=decision.reviewer or "system",
            metadata={
                "state": decision.state,
                "recommendedSubmissionId": (
                    decision.recommended_submission_id
                ),
                "selectedSubmissionId": (
                    decision.selected_submission_id
                ),
            },
        )

    def record_source_selected(
        self,
        *,
        requirement_id: str,
        submission_id: str,
        decision_event_id: str,
        reason: str,
    ) -> str:
        return self.record_event(
            event_type="source_selected",
            requirement_id=requirement_id,
            submission_id=submission_id,
            related_event_ids=[
                decision_event_id,
            ],
            reason=reason,
        )

    def record_event(
        self,
        *,
        event_type,
        requirement_id: str | None = None,
        submission_id: str | None = None,
        evidence_ids: list[str] | None = None,
        related_event_ids: list[str] | None = None,
        actor: str = "system",
        reason: str = "",
        metadata: dict | None = None,
    ) -> str:
        self._event_counter += 1

        event_id = (
            f"EVENT_{self._event_counter:06d}"
        )

        event = ProvenanceEvent(
            event_id=event_id,
            event_type=event_type,
            challenge_id=self._ledger.challenge_id,
            requirement_id=requirement_id,
            submission_id=submission_id,
            evidence_ids=list(
                evidence_ids or []
            ),
            related_event_ids=list(
                related_event_ids or []
            ),
            actor=actor,
            reason=reason,
            metadata=dict(
                metadata or {}
            ),
        )

        self._ledger = replace(
            self._ledger,
            events=[
                *self._ledger.events,
                event,
            ],
        )

        return event_id

    def _find_evidence_ids(
        self,
        requirement_id: str,
    ) -> list[str]:
        return [
            item.evidence_id
            for item in self._ledger.evidence
            if item.requirement_id == requirement_id
        ]