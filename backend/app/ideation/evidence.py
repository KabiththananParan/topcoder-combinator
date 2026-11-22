from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentEvidenceRef:
    evidence_id: str
    submission_id: str
    source_path: str

    page: int | None = None
    slide: int | None = None
    section: str | None = None
    content_block: str | None = None

    evidence_type: str = "document"
    source_hash: str | None = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "evidenceId": self.evidence_id,
            "submissionId": self.submission_id,
            "sourcePath": self.source_path,
            "page": self.page,
            "slide": self.slide,
            "section": self.section,
            "contentBlock": self.content_block,
            "evidenceType": self.evidence_type,
            "sourceHash": self.source_hash,
            "description": self.description,
        }
