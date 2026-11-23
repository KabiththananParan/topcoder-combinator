from pathlib import Path
from zipfile import ZipFile

import pytest

from app.ideation.docx_extractor import DocxExtractor


def test_docx_extractor_rejects_macro_package(tmp_path: Path):
    source = tmp_path / "macro.docx"
    with ZipFile(source, "w") as archive:
        archive.writestr("word/vbaProject.bin", b"not executable here")

    with pytest.raises(ValueError, match="active content"):
        DocxExtractor().extract("SUB_001", source)
