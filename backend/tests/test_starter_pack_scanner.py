from pathlib import Path

from app.ingestion.starter_pack_scanner import StarterPackScanner


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STARTER_PACK = PROJECT_ROOT / "starter-pack"


def test_discovers_all_challenges():
    scanner = StarterPackScanner()

    inventories = scanner.scan(STARTER_PACK)

    assert len(inventories) == 4

    challenge_ids = {
        inventory.challenge_id
        for inventory in inventories
    }

    assert challenge_ids == {
        "AI_DEAL_SCOPING_ASSISTANT",
        "AI_LEARNING_ADVENTURE",
        "AI_WORKFLOW_PUZZLE_BUILDER",
        "AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC",
    }


def test_deal_scoping_challenge():
    scanner = StarterPackScanner()

    inventories = scanner.scan(STARTER_PACK)

    inventory = next(
        item
        for item in inventories
        if item.challenge_id == "AI_DEAL_SCOPING_ASSISTANT"
    )

    assert inventory.mode == "code"

    assert inventory.submission_ids == [
        "SUB_001",
        "SUB_002",
    ]

    assert inventory.review_context_path is not None
    assert inventory.review_context_path.is_file()


def test_submission_directories_exist():
    scanner = StarterPackScanner()

    inventories = scanner.scan(STARTER_PACK)

    for inventory in inventories:
        for submission_id in inventory.submission_ids:
            submission_path = (
                inventory.root_path
                / "submissions"
                / submission_id
            )

            assert submission_path.is_dir()