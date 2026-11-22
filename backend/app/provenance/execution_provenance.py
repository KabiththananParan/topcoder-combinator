from __future__ import annotations

from dataclasses import replace

from .models import ProvenanceEvent, ProvenanceLedger


class ExecutionProvenanceRecorder:
    """
    Records candidate execution lifecycle events in a ProvenanceLedger.

    This class does not modify candidate files. It only records what
    happened during candidate construction and verification.
    """

    def __init__(self, ledger: ProvenanceLedger):
        self.ledger = ledger

    def record_transplant_planned(
        self,
        requirement_id: str,
        source_submission_id: str | None,
        target_submission_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="transplant_planned",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            submission_id=source_submission_id,
            evidence_ids=evidence_ids or [],
            actor="system",
            reason=reason,
            metadata={
                "target_submission_id": target_submission_id,
            },
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def record_transplant_applied(
        self,
        requirement_id: str,
        source_submission_id: str | None,
        target_submission_id: str,
        source_path: str | None,
        target_path: str | None,
        related_event_ids: list[str] | None = None,
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="transplant_applied",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            submission_id=source_submission_id,
            related_event_ids=related_event_ids or [],
            actor="system",
            reason="Approved transplant applied to candidate workspace.",
            metadata={
                "target_submission_id": target_submission_id,
                "source_path": source_path,
                "target_path": target_path,
            },
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def record_verification_started(
        self,
        requirement_id: str,
        related_event_ids: list[str] | None = None,
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="verification_started",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            related_event_ids=related_event_ids or [],
            actor="system",
            reason="Candidate verification started.",
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def record_verification_completed(
        self,
        requirement_id: str,
        related_event_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="verification_completed",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            related_event_ids=related_event_ids or [],
            actor="system",
            reason="Candidate verification completed successfully.",
            metadata=metadata or {},
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def record_verification_failed(
        self,
        requirement_id: str,
        related_event_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="verification_failed",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            related_event_ids=related_event_ids or [],
            actor="system",
            reason="Candidate verification failed.",
            metadata=metadata or {},
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def record_rollback(
        self,
        requirement_id: str,
        related_event_ids: list[str] | None = None,
        reason: str = "Failed transplant rolled back.",
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            event_id=self._next_event_id(),
            event_type="rollback",
            challenge_id=self.ledger.challenge_id,
            requirement_id=requirement_id,
            related_event_ids=related_event_ids or [],
            actor="system",
            reason=reason,
        )

        self.ledger = replace(
            self.ledger,
            events=[*self.ledger.events, event],
        )

        return event

    def get_ledger(self) -> ProvenanceLedger:
        return self.ledger

    def _next_event_id(self) -> str:
        return f"EVENT_{len(self.ledger.events) + 1:06d}"