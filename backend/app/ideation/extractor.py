from pathlib import Path

from .docx_extractor import DocxExtractor
from .image_extractor import ImageExtractor
from .models import DocumentProfile
from .pdf_extractor import PdfExtractor


class DocumentExtractor:
    def __init__(self) -> None:
        self._pdf = PdfExtractor()
        self._docx = DocxExtractor()
        self._image = ImageExtractor()

    def extract(self, submission_id: str, source_path: Path) -> DocumentProfile:
        suffix = source_path.suffix.lower()

        if suffix == ".pdf":
            return self._pdf.extract(submission_id, source_path)

        if suffix == ".docx":
            return self._docx.extract(submission_id, source_path)

        if suffix in {".png", ".jpg", ".jpeg"}:
            return self._image.extract(submission_id, source_path)

        raise ValueError(f"Unsupported document type: {suffix}")
