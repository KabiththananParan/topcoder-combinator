from __future__ import annotations

from pathlib import Path

from app.analysis import (
    Requirement,
    RequirementAnalyzer,
)
from app.evidence import EvidenceLocator

from .models import (
    MatrixEntry,
    RequirementMatrix,
)


class RequirementMatrixBuilder:
    """
    Builds a complete requirement × submission matrix.

    The builder is deterministic:
    
        requirements
              +
        submissions
              ↓
        evidence discovery
              ↓
        requirement assessment
              ↓
        matrix
    """

    def __init__(
        self,
        challenge_id: str,
        challenge_root: Path,
    ):
        self.challenge_id = challenge_id
        self.challenge_root = challenge_root.resolve()

        self.submissions_root = (
            self.challenge_root / "submissions"
        )

        self.analyzer = RequirementAnalyzer()

    def build(
        self,
        requirements: list[Requirement],
        submission_ids: list[str],
    ) -> RequirementMatrix:

        entries: list[MatrixEntry] = []

        for submission_id in submission_ids:

            submission_root = (
                self.submissions_root / submission_id
            ).resolve()

            if not submission_root.is_relative_to(
                self.submissions_root.resolve()
            ):
                raise ValueError(
                    f"Invalid submission path: {submission_id}"
                )

            if not submission_root.is_dir():
                raise FileNotFoundError(
                    f"Submission directory does not exist: "
                    f"{submission_id}"
                )

            locator = EvidenceLocator(
                submission_root
            )

            for requirement in requirements:

                search_terms = self._build_search_terms(
                    requirement
                )

                evidence = locator.locate(
                    submission_id=submission_id,
                    requirement_id=(
                        requirement.requirement_id
                    ),
                    search_terms=search_terms,
                )

                assessment = self.analyzer.analyze(
                    requirement,
                    evidence,
                )

                entries.append(
                    MatrixEntry(
                        requirement_id=(
                            requirement.requirement_id
                        ),
                        requirement_title=(
                            requirement.title
                        ),
                        submission_id=submission_id,
                        assessment=assessment,
                    )
                )

        return RequirementMatrix(
            challenge_id=self.challenge_id,
            entries=entries,
        )

    def _build_search_terms(
        self,
        requirement: Requirement,
    ) -> list[str]:

        terms: list[str] = []

        values = [
            requirement.title,
            *requirement.constraints,
        ]

        for value in values:

            for word in value.lower().split():

                cleaned = word.strip(
                    ".,:;!?()[]{}\"'`"
                )

                if (
                    len(cleaned) < 3
                    or cleaned in terms
                ):
                    continue

                terms.append(cleaned)

        return terms