from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DocumentLocation:
    source_path: str
    page: int | None = None
    slide: int | None = None
    section: str | None = None
    content_block: str | None = None


@dataclass(frozen=True)
class DocumentBlock:
    block_id: str
    block_type: str
    text: str
    location: DocumentLocation
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentProfile:
    submission_id: str
    source_path: Path
    file_type: str
    blocks: list[DocumentBlock]
    extraction_status: str = "complete"
