from pathlib import Path

import pymupdf

from .models import DocumentBlock, DocumentLocation, DocumentProfile


class PdfExtractor:
    def extract(self, submission_id: str, source_path: Path) -> DocumentProfile:
        blocks: list[DocumentBlock] = []

        with pymupdf.open(source_path) as document:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text").strip()

                if not text:
                    continue

                blocks.append(
                    DocumentBlock(
                        block_id=f"page-{page_index}",
                        block_type="page_text",
                        text=text,
                        location=DocumentLocation(
                            source_path=str(source_path),
                            page=page_index,
                        ),
                    )
                )

        return DocumentProfile(
            submission_id=submission_id,
            source_path=source_path,
            file_type="pdf",
            blocks=blocks,
            extraction_status="complete" if blocks else "not_verifiable",
        )
