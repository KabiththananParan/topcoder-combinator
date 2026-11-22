from __future__ import annotations

from .models import (
    Requirement,
    RequirementAssessment,
)
from app.evidence.models import EvidenceCandidate


class RequirementAnalyzer:
    """
    Deterministically assesses the strength of available evidence.

    It does not claim that code is technically correct.
    It only evaluates whether sufficient evidence was found.

    Deeper semantic reasoning will be handled by the LLM layer later.
    """

    def analyze(
        self,
        requirement: Requirement,
        evidence: EvidenceCandidate,
    ) -> RequirementAssessment:

        locations = evidence.locations

        if not locations:
            return RequirementAssessment(
                requirement_id=requirement.requirement_id,
                submission_id=evidence.submission_id,
                assessment="missing",
                evidence=[],
                reasoning=(
                    "No relevant source, test, or documentation "
                    "evidence was located for this requirement."
                ),
                confidence=0.2,
                compatibility_risk="unknown",
            )

        evidence_records = [
            self._location_to_dict(location)
            for location in locations
        ]

        evidence_types = {
            self._classify_location(location.path)
            for location in locations
        }

        has_source = "source" in evidence_types
        has_test = "test" in evidence_types
        has_documentation = "documentation" in evidence_types

        unique_terms = set()

        for location in locations:
            unique_terms.update(
                location.matched_terms
            )

        term_coverage = (
            len(unique_terms) / max(
                len(self._requirement_terms(requirement)),
                1,
            )
        )

        if has_source and has_test and has_documentation:
            assessment = "complete"
            confidence = 0.85

            reasoning = (
                "Relevant implementation, test, and documentation "
                "evidence was located. The evidence provides coverage "
                "across multiple evidence types."
            )

        elif has_source and has_test:
            assessment = "partial"
            confidence = 0.75

            reasoning = (
                "Relevant implementation and test evidence was located, "
                "but supporting documentation evidence was not identified."
            )

        elif has_source and has_documentation:
            assessment = "partial"
            confidence = 0.70

            reasoning = (
                "Relevant implementation and documentation evidence was "
                "located, but supporting test evidence was not identified."
            )

        elif has_source:
            assessment = "partial"
            confidence = 0.60

            reasoning = (
                "Relevant implementation evidence was located, but "
                "independent test or documentation evidence was not identified."
            )

        elif has_documentation or has_test:
            assessment = "manual_review_required"
            confidence = 0.45

            reasoning = (
                "Relevant evidence was located, but it does not include "
                "sufficient implementation evidence to establish coverage."
            )

        else:
            assessment = "not_verifiable"
            confidence = 0.30

            reasoning = (
                "Potentially relevant evidence was found, but its "
                "type or content is insufficient for verification."
            )

        if term_coverage < 0.25:
            confidence *= 0.7

        confidence = round(
            max(0.0, min(confidence, 1.0)),
            3,
        )

        compatibility_risk = self._determine_compatibility_risk(
            evidence
        )

        return RequirementAssessment(
            requirement_id=requirement.requirement_id,
            submission_id=evidence.submission_id,
            assessment=assessment,
            evidence=evidence_records,
            reasoning=reasoning,
            confidence=confidence,
            compatibility_risk=compatibility_risk,
        )

    def _location_to_dict(self, location):
        return {
            "path": location.path,
            "startLine": location.start_line,
            "endLine": location.end_line,
            "symbol": location.symbol,
            "matchedTerms": location.matched_terms,
        }

    def _classify_location(self, path: str) -> str:
        lower_path = path.lower()

        filename = lower_path.split("/")[-1]

        if (
            ".test." in filename
            or ".spec." in filename
            or "_test." in filename
            or filename.startswith("test_")
            or "/tests/" in f"/{lower_path}/"
            or "/test/" in f"/{lower_path}/"
            or "/__tests__/" in f"/{lower_path}/"
        ):
            return "test"

        if (
            lower_path.endswith(".md")
            or lower_path.endswith(".rst")
            or lower_path.endswith(".txt")
            or "/docs/" in f"/{lower_path}/"
        ):
            return "documentation"

        return "source"

    def _requirement_terms(
        self,
        requirement: Requirement,
    ) -> list[str]:

        terms = []

        for value in [
            requirement.title,
            *requirement.constraints,
        ]:
            terms.extend(
                value.lower().split()
            )

        normalized = []

        for term in terms:
            term = (
                term.strip(".,:;()[]{}\"'")
            )

            if (
                len(term) >= 3
                and term not in normalized
            ):
                normalized.append(term)

        return normalized

    def _determine_compatibility_risk(
        self,
        evidence: EvidenceCandidate,
    ) -> str:

        paths = [
            location.path.lower()
            for location in evidence.locations
        ]

        if any(
            "package.json" in path
            for path in paths
        ):
            return "low"

        if len(paths) <= 2:
            return "medium"

        return "low"