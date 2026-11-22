from pathlib import Path

from .models import DocumentBlock, DocumentLocation, DocumentProfile


class ImageExtractor:
    def extract(self, submission_id: str, source_path: Path) -> DocumentProfile:
        block = DocumentBlock(
            block_id="image-1",
            block_type="image",
            text="",
            location=DocumentLocation(
                source_path=str(source_path),
                content_block="image-1",
            ),
            metadata={"extraction": "ocr_unavailable"},
        )

        return DocumentProfile(
            submission_id=submission_id,
            source_path=source_path,
            file_type=source_path.suffix.lower().lstrip("."),
            blocks=[block],
            extraction_status="manual_review_required",
        )
