from dataclasses import dataclass, field
from typing import Literal


ProvenanceEventType = Literal[
    "evidence_found",
    "assessment_created",
    "recommendation_created",
    "decision_created",
    "source_selected",
    "transplant_planned",
    "transplant_applied",
    "verification_started",
    "verification_completed",
    "verification_failed",
    "rollback",
]


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    submission_id: str
    requirement_id: str

    path: str

    start_line: int | None = None
    end_line: int | None = None

    symbol: str | None = None

    evidence_type: str = "unknown"

    source_hash: str | None = None

    description: str = ""

    def to_dict(self) -> dict:
        return {
            "evidenceId": self.evidence_id,
            "submissionId": self.submission_id,
            "requirementId": self.requirement_id,
            "path": self.path,
            "startLine": self.start_line,
            "endLine": self.end_line,
            "symbol": self.symbol,
            "evidenceType": self.evidence_type,
            "sourceHash": self.source_hash,
            "description": self.description,
        }


@dataclass(frozen=True)
class ProvenanceEvent:
    event_id: str
    event_type: ProvenanceEventType

    challenge_id: str
    requirement_id: str | None = None
    submission_id: str | None = None

    evidence_ids: list[str] = field(default_factory=list)

    related_event_ids: list[str] = field(default_factory=list)

    actor: str = "system"

    reason: str = ""

    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "challengeId": self.challenge_id,
            "requirementId": self.requirement_id,
            "submissionId": self.submission_id,
            "evidenceIds": self.evidence_ids,
            "relatedEventIds": self.related_event_ids,
            "actor": self.actor,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProvenanceLedger:
    challenge_id: str

    evidence: list[EvidenceRef] = field(default_factory=list)

    events: list[ProvenanceEvent] = field(default_factory=list)

    def evidence_by_id(
        self,
        evidence_id: str,
    ) -> EvidenceRef | None:
        for item in self.evidence:
            if item.evidence_id == evidence_id:
                return item

        return None

    def events_for_requirement(
        self,
        requirement_id: str,
    ) -> list[ProvenanceEvent]:
        return [
            event
            for event in self.events
            if event.requirement_id == requirement_id
        ]

    def events_for_submission(
        self,
        submission_id: str,
    ) -> list[ProvenanceEvent]:
        return [
            event
            for event in self.events
            if event.submission_id == submission_id
        ]

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
            "events": [
                event.to_dict()
                for event in self.events
            ],
        }