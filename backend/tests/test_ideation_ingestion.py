from pathlib import Path

from app.ideation.extractor import DocumentExtractor
from app.ideation.submission_profiler import IdeationSubmissionProfiler


FIXTURE_ROOT = Path(
    "../starter-pack/challenges/"
    "AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC/submissions"
)


def test_document_extractor_supports_fixture_formats():
    extractor = DocumentExtractor()

    pdf = extractor.extract(
        "SUB_001",
        FIXTURE_ROOT / "SUB_001/Idea-1-Topcoder-AI-Agents.pdf",
    )
    docx = extractor.extract(
        "SUB_002",
        FIXTURE_ROOT / "SUB_002/Topcoder multi agent code review workflow.docx",
    )
    image = extractor.extract(
        "SUB_002",
        FIXTURE_ROOT / "SUB_002/Topcoder multi agent code review workflow.png",
    )

    assert pdf.extraction_status == "complete"
    assert len(pdf.blocks) == 10
    assert pdf.blocks[0].location.page == 1

    assert docx.extraction_status == "complete"
    assert len(docx.blocks) == 32

    assert image.extraction_status == "manual_review_required"
    assert len(image.blocks) == 1
    assert image.blocks[0].metadata["extraction"] == "ocr_unavailable"


def test_submission_profiler_discovers_all_supported_documents():
    profiler = IdeationSubmissionProfiler()
    root = FIXTURE_ROOT

    profiles = {
        submission_id: profiler.profile(
            submission_id,
            root / submission_id,
        )
        for submission_id in ["SUB_001", "SUB_002", "SUB_003"]
    }

    assert len(profiles["SUB_001"]) == 3
    assert len(profiles["SUB_002"]) == 2
    assert len(profiles["SUB_003"]) == 2

    assert all(
        profile.extraction_status == "complete"
        for profile in profiles["SUB_001"]
    )
    assert profiles["SUB_002"][1].extraction_status == "manual_review_required"
