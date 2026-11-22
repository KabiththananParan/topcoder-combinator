from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceLocation:
    path: str
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    matched_terms: list[str] | None = None


@dataclass(frozen=True)
class EvidenceCandidate:
    submission_id: str
    requirement_id: str
    locations: list[EvidenceLocation]
    evidence_type: str
    relevance_score: float