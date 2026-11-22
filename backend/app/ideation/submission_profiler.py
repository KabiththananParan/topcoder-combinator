from pathlib import Path

from .extractor import DocumentExtractor
from .models import DocumentBlock, DocumentProfile


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


class IdeationSubmissionProfiler:
    def __init__(self, extractor: DocumentExtractor | None = None) -> None:
        self.extractor = extractor or DocumentExtractor()

    def profile(self, submission_id: str, submission_path: Path) -> list[DocumentProfile]:
        profiles: list[DocumentProfile] = []

        for path in sorted(submission_path.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            profiles.append(
                self.extractor.extract(submission_id, path)
            )

        return profiles
