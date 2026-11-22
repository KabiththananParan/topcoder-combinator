import json
from pathlib import Path

from ..core.config import settings
from .models import ChallengeInventory
from .safe_path import safe_resolve


class StarterPackError(ValueError):
    pass


class StarterPackScanner:
    REQUIRED_CHALLENGE_FILES = {
        "challenge-context.json",
        "challenge-package.json",
        "README.md",
    }

    REQUIRED_CHALLENGE_DIRECTORIES = {
        "submissions",
        "reviews",
        "verification",
        "integrity",
    }

    def __init__(self, starter_pack_path: Path | None = None):
        self.starter_pack_path = (
            starter_pack_path or settings.starter_pack_path
        ).resolve()

    def scan(
        self,
        starter_pack_path: Path | None = None,
    ) -> list[ChallengeInventory]:
        """
        Scan the starter pack and return an inventory for each challenge.

        A path passed to scan() takes precedence over the configured
        starter-pack path.
        """
        starter_pack = (
            starter_pack_path or self.starter_pack_path
        ).resolve()

        if not starter_pack.exists():
            raise StarterPackError(
                f"Starter pack does not exist: {starter_pack}"
            )

        if not starter_pack.is_dir():
            raise StarterPackError(
                f"Starter pack is not a directory: {starter_pack}"
            )

        manifest_path = starter_pack / "manifest.json"

        if not manifest_path.is_file():
            raise StarterPackError(
                f"Starter pack manifest does not exist: {manifest_path}"
            )

        challenges_dir = starter_pack / "challenges"

        if not challenges_dir.is_dir():
            raise StarterPackError(
                f"Challenges directory does not exist: {challenges_dir}"
            )

        inventories: list[ChallengeInventory] = []

        for challenge_dir in sorted(challenges_dir.iterdir()):
            if not challenge_dir.is_dir():
                continue

            inventory = self._scan_challenge(
                starter_pack,
                challenge_dir,
            )

            inventories.append(inventory)

        return inventories

    def _scan_challenge(
        self,
        starter_pack: Path,
        challenge_dir: Path,
    ) -> ChallengeInventory:
        self._validate_required_files(challenge_dir)
        self._validate_required_directories(challenge_dir)

        context_path = challenge_dir / "challenge-context.json"
        package_path = challenge_dir / "challenge-package.json"

        self._load_json(context_path)
        package = self._load_json(package_path)

        challenge_id = package.get("challengeId")

        if not challenge_id:
            raise StarterPackError(
                f"Missing challengeId in {package_path}"
            )

        mode = package.get("challengeMode")

        if not mode:
            raise StarterPackError(
                f"Missing challengeMode in {package_path}"
            )

        submission_ids = package.get("submissionIds")

        if not isinstance(submission_ids, list):
            raise StarterPackError(
                f"submissionIds must be a list in {package_path}"
            )

        self._validate_submission_directories(
            challenge_dir,
            submission_ids,
        )

        review_context_path = self._resolve_review_context(
            starter_pack,
            challenge_dir,
            package,
        )

        return ChallengeInventory(
            challenge_id=challenge_id,
            mode=mode,
            root_path=challenge_dir,
            challenge_context_path=context_path,
            challenge_package_path=package_path,
            review_context_path=review_context_path,
            submission_ids=submission_ids,
            reviews_path=challenge_dir / "reviews",
            scorecards_path=challenge_dir / "scorecards",
            verification_path=challenge_dir / "verification",
            integrity_path=challenge_dir / "integrity",
        )

    def _validate_required_files(
        self,
        challenge_dir: Path,
    ) -> None:
        for filename in self.REQUIRED_CHALLENGE_FILES:
            path = challenge_dir / filename

            if not path.is_file():
                raise StarterPackError(
                    f"Required challenge file does not exist: {path}"
                )

    def _validate_required_directories(
        self,
        challenge_dir: Path,
    ) -> None:
        for dirname in self.REQUIRED_CHALLENGE_DIRECTORIES:
            path = challenge_dir / dirname

            if not path.is_dir():
                raise StarterPackError(
                    f"Required challenge directory does not exist: {path}"
                )

    def _validate_submission_directories(
        self,
        challenge_dir: Path,
        submission_ids: list[str],
    ) -> None:
        submissions_dir = challenge_dir / "submissions"

        for submission_id in submission_ids:
            submission_dir = safe_resolve(
                submissions_dir,
                submission_id,
                allowed_root=submissions_dir,
            )

            if not submission_dir.is_dir():
                raise StarterPackError(
                    f"Submission directory does not exist: {submission_dir}"
                )

    def _resolve_review_context(
        self,
        starter_pack: Path,
        challenge_dir: Path,
        package: dict,
    ) -> Path | None:
        reference = package.get("reviewContextRef")

        if not reference:
            return None

        # reviewContextRef is relative to the challenge directory.
        #
        # Example:
        #
        # challenges/AI_DEAL_SCOPING_ASSISTANT/
        #   ../../review-context/ai-deal-scoping-assistant.json
        #
        # The resulting path must remain inside the starter pack.

        path = safe_resolve(
            challenge_dir,
            reference,
            allowed_root=starter_pack,
        )

        if not path.is_file():
            raise StarterPackError(
                f"Review context does not exist: {path}"
            )

        return path

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise StarterPackError(
                f"Invalid JSON in {path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise StarterPackError(
                f"Expected JSON object in {path}"
            )

        return data