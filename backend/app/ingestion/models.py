from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChallengeInventory:
    challenge_id: str
    mode: str
    root_path: Path
    challenge_context_path: Path
    challenge_package_path: Path
    review_context_path: Path | None
    submission_ids: list[str]
    reviews_path: Path
    scorecards_path: Path
    verification_path: Path
    integrity_path: Path