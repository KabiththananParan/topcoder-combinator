from __future__ import annotations

import re
from pathlib import Path

from .models import EvidenceCandidate, EvidenceLocation


class EvidenceLocator:
    """
    Deterministically locates possible evidence for a requirement
    inside a submission repository.

    This class does NOT decide whether the evidence proves the
    requirement. It only finds relevant source locations.
    """

    SOURCE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".cs",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".kts",
    }

    DOCUMENTATION_EXTENSIONS = {
        ".md",
        ".rst",
        ".txt",
    }

    TEST_DIRECTORY_NAMES = {
        "test",
        "tests",
        "__tests__",
        "spec",
        "specs",
    }

    IGNORED_DIRECTORIES = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        "coverage",
        ".idea",
        ".vscode",
    }

    MAX_FILE_SIZE = 1_000_000

    def __init__(self, submission_root: Path):
        self.submission_root = submission_root.resolve()

    def locate(
        self,
        submission_id: str,
        requirement_id: str,
        search_terms: list[str],
    ) -> EvidenceCandidate:

        if not search_terms:
            return EvidenceCandidate(
                submission_id=submission_id,
                requirement_id=requirement_id,
                evidence_type="mixed",
                locations=[],
                relevance_score=0.0,
            )

        normalized_terms = self._normalize_terms(search_terms)

        locations: list[EvidenceLocation] = []

        for file_path in self._iter_files():

            file_type = self._classify_file(file_path)

            if file_type is None:
                continue

            content = self._read_text(file_path)

            if content is None:
                continue

            matches = self._find_matches(
                content,
                normalized_terms,
            )

            if not matches:
                continue

            relative_path = file_path.relative_to(
                self.submission_root
            ).as_posix()

            locations.append(
                EvidenceLocation(
                    path=relative_path,
                    start_line=matches["start_line"],
                    end_line=matches["end_line"],
                    symbol=matches["symbol"],
                    matched_terms=matches["matched_terms"],
                )
            )

        locations.sort(
            key=lambda location: self._location_sort_key(
                location,
                normalized_terms,
            )
        )

        relevance_score = self._calculate_relevance(
            locations,
            normalized_terms,
        )

        evidence_type = self._determine_evidence_type(locations)

        return EvidenceCandidate(
            submission_id=submission_id,
            requirement_id=requirement_id,
            evidence_type=evidence_type,
            locations=locations,
            relevance_score=relevance_score,
        )

    def _iter_files(self):
        """
        Recursively walk the submission while respecting the
        submission root as the security boundary.
        """

        for path in self.submission_root.rglob("*"):

            if not path.is_file():
                continue

            if self._contains_ignored_directory(path):
                continue

            try:
                resolved = path.resolve()

                if not resolved.is_relative_to(
                    self.submission_root
                ):
                    continue

            except OSError:
                continue

            yield resolved

    def _contains_ignored_directory(self, path: Path) -> bool:
        try:
            relative_parts = path.relative_to(
                self.submission_root
            ).parts
        except ValueError:
            return True

        return any(
            part in self.IGNORED_DIRECTORIES
            for part in relative_parts
        )

    def _classify_file(self, path: Path) -> str | None:
        suffix = path.suffix.lower()

        if suffix in self.DOCUMENTATION_EXTENSIONS:
            return "documentation"

        if suffix in self.SOURCE_EXTENSIONS:
            if self._is_test_file(path):
                return "test"

            return "source"

        return None

    def _is_test_file(self, path: Path) -> bool:
        parts = {
            part.lower()
            for part in path.parts
        }

        if parts.intersection(self.TEST_DIRECTORY_NAMES):
            return True

        name = path.name.lower()

        test_patterns = [
            ".test.",
            ".spec.",
            "_test.",
            "test_",
        ]

        return any(
            pattern in name
            for pattern in test_patterns
        )

    def _read_text(self, path: Path) -> str | None:
        try:
            if path.stat().st_size > self.MAX_FILE_SIZE:
                return None

            return path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

        except (OSError, UnicodeError):
            return None

    def _normalize_terms(
        self,
        terms: list[str],
    ) -> list[str]:

        normalized = []

        for term in terms:
            term = term.strip().lower()

            if not term:
                continue

            if term not in normalized:
                normalized.append(term)

        return normalized

    def _find_matches(
        self,
        content: str,
        search_terms: list[str],
    ) -> dict:

        lines = content.splitlines()

        matched_lines: list[int] = []
        matched_terms: set[str] = set()

        for index, line in enumerate(lines, start=1):

            lower_line = line.lower()

            line_matched = False

            for term in search_terms:

                if self._term_matches(
                    term,
                    lower_line,
                ):
                    matched_terms.add(term)
                    line_matched = True

            if line_matched:
                matched_lines.append(index)

        if not matched_lines:
            return {}

        start_line = matched_lines[0]

        # Give the evidence a small context window.
        end_line = min(
            len(lines),
            matched_lines[-1] + 3,
        )

        symbol = self._detect_symbol(
            lines,
            start_line,
        )

        return {
            "start_line": start_line,
            "end_line": end_line,
            "symbol": symbol,
            "matched_terms": sorted(matched_terms),
        }

    def _term_matches(
        self,
        term: str,
        text: str,
    ) -> bool:

        # Short terms should use word boundaries.
        if len(term) <= 3:
            pattern = rf"\b{re.escape(term)}\b"
            return bool(re.search(pattern, text))

        return term in text

    def _detect_symbol(
        self,
        lines: list[str],
        start_line: int,
    ) -> str | None:

        start_index = start_line - 1

        patterns = [
            r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        ]

        # Look slightly above the matched line because the
        # declaration may appear immediately before it.
        search_start = max(0, start_index - 5)

        for index in range(
            start_index,
            search_start - 1,
            -1,
        ):
            line = lines[index]

            for pattern in patterns:
                match = re.search(
                    pattern,
                    line,
                    re.IGNORECASE,
                )

                if match:
                    return match.group(1)

        return None

    def _location_sort_key(
        self,
        location: EvidenceLocation,
        search_terms: list[str],
    ):
        matched_count = len(location.matched_terms)

        type_priority = 0

        path_lower = location.path.lower()

        if "test" in path_lower:
            type_priority = 2

        elif (
            path_lower.endswith(".md")
            or "/docs/" in path_lower
        ):
            type_priority = 1

        return (
            -matched_count,
            type_priority,
            location.path,
        )

    def _calculate_relevance(
        self,
        locations: list[EvidenceLocation],
        search_terms: list[str],
    ) -> float:

        if not locations or not search_terms:
            return 0.0

        unique_terms = set()

        for location in locations:
            unique_terms.update(
                location.matched_terms
            )

        term_coverage = (
            len(unique_terms) / len(search_terms)
        )

        location_bonus = min(
            len(locations) / 5,
            1.0,
        )

        score = (
            0.7 * term_coverage
            + 0.3 * location_bonus
        )

        return round(
            min(score, 1.0),
            3,
        )

    def _determine_evidence_type(
        self,
        locations: list[EvidenceLocation],
    ) -> str:

        if not locations:
            return "mixed"

        has_source = False
        has_test = False
        has_documentation = False

        for location in locations:

            path = location.path.lower()

            if self._looks_like_test(path):
                has_test = True

            elif (
                path.endswith(".md")
                or "/docs/" in path
                or path.startswith("docs/")
            ):
                has_documentation = True

            else:
                has_source = True

        types = sum(
            [
                has_source,
                has_test,
                has_documentation,
            ]
        )

        if types > 1:
            return "mixed"

        if has_test:
            return "test"

        if has_documentation:
            return "documentation"

        return "source"

    def _looks_like_test(self, path: str) -> bool:

        name = Path(path).name.lower()

        return any(
            pattern in name
            for pattern in [
                ".test.",
                ".spec.",
                "_test.",
                "test_",
            ]
        ) or any(
            f"/{directory}/" in f"/{path}/"
            for directory in self.TEST_DIRECTORY_NAMES
        )