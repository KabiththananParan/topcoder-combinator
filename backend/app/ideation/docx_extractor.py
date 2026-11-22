from pathlib import Path

from docx import Document

from .models import DocumentBlock, DocumentLocation, DocumentProfile


class DocxExtractor:
    def extract(self, submission_id: str, source_path: Path) -> DocumentProfile:
        document = Document(source_path)
        blocks: list[DocumentBlock] = []

        for index, paragraph in enumerate(document.paragraphs, start=1):
            text = paragraph.text.strip()

            if not text:
                continue

            blocks.append(
                DocumentBlock(
                    block_id=f"paragraph-{index}",
                    block_type="paragraph",
                    text=text,
                    location=DocumentLocation(
                        source_path=str(source_path),
                        section=paragraph.style.name if paragraph.style else None,
                        content_block=f"paragraph-{index}",
                    ),
                )
            )

        for table_index, table in enumerate(document.tables, start=1):
            for row_index, row in enumerate(table.rows, start=1):
                cells = [cell.text.strip() for cell in row.cells]
                text = " | ".join(cell for cell in cells if cell)

                if not text:
                    continue

                blocks.append(
                    DocumentBlock(
                        block_id=f"table-{table_index}-row-{row_index}",
                        block_type="table_row",
                        text=text,
                        location=DocumentLocation(
                            source_path=str(source_path),
                            content_block=(
                                f"table-{table_index}-row-{row_index}"
                            ),
                        ),
                    )
                )

        return DocumentProfile(
            submission_id=submission_id,
            source_path=source_path,
            file_type="docx",
            blocks=blocks,
            extraction_status="complete" if blocks else "not_verifiable",
        )
