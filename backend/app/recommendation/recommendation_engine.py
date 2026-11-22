from dataclasses import dataclass

from app.matrix.models import MatrixEntry, RequirementMatrix
from app.profiling.models import SubmissionProfile

from .models import (
    CompatibilityRisk,
    Recommendation,
    RecommendationSet,
)


@dataclass(frozen=True)
class CandidateScore:
    submission_id: str
    total: float

    coverage_score: float
    evidence_score: float
    test_score: float
    documentation_score: float
    architecture_score: float
    compatibility_score: float
    implementation_risk_score: float

    compatibility_risk: CompatibilityRisk

    evidence_summary: list[str]
    unresolved_conflicts: list[str]


class RecommendationEngine:
    """
    Deterministic recommendation engine.

    The engine ranks submissions for each requirement using:
      - requirement coverage
      - evidence strength
      - test evidence
      - documentation
      - technology / architecture signals
      - compatibility risk
      - implementation risk

    It deliberately does NOT use final submission scores.
    """

    # Keep the weights explicit and easy to audit.
    WEIGHTS = {
        "coverage": 0.30,
        "evidence": 0.20,
        "tests": 0.15,
        "documentation": 0.10,
        "architecture": 0.10,
        "compatibility": 0.10,
        "implementation_risk": 0.05,
    }

    def recommend(
        self,
        matrix: RequirementMatrix,
        profiles: dict[str, SubmissionProfile],
    ) -> RecommendationSet:
        recommendations: list[Recommendation] = []

        requirement_ids = self._requirement_ids(matrix)

        for requirement_id in requirement_ids:
            entries = matrix.for_requirement(requirement_id)

            recommendation = self._recommend_requirement(
                entries=entries,
                profiles=profiles,
            )

            recommendations.append(recommendation)

        return RecommendationSet(
            challenge_id=matrix.challenge_id,
            recommendations=recommendations,
        )

    def _recommend_requirement(
        self,
        entries: list[MatrixEntry],
        profiles: dict[str, SubmissionProfile],
    ) -> Recommendation:
        if not entries:
            return Recommendation(
                requirement_id="unknown",
                requirement_title="Unknown requirement",
                recommended_submission_id=None,
                status="no_suitable_source",
                score=0.0,
                confidence=0.0,
                reasoning="No matrix entries were available.",
                compatibility_risk="unknown",
            )

        candidates: list[CandidateScore] = []

        for entry in entries:
            profile = profiles.get(entry.submission_id)

            if profile is None:
                continue

            candidates.append(
                self._score_candidate(
                    entry=entry,
                    profile=profile,
                )
            )

        if not candidates:
            first = entries[0]

            return Recommendation(
                requirement_id=first.requirement_id,
                requirement_title=first.requirement_title,
                recommended_submission_id=None,
                status="no_suitable_source",
                score=0.0,
                confidence=0.0,
                reasoning=(
                    "No submission profile was available for the "
                    "candidate submissions."
                ),
                compatibility_risk="unknown",
            )

        candidates.sort(
            key=lambda candidate: (
                candidate.total,
                candidate.coverage_score,
                candidate.evidence_score,
                candidate.test_score,
            ),
            reverse=True,
        )

        winner = candidates[0]

        alternatives = [
            candidate.submission_id
            for candidate in candidates[1:]
        ]

        status: str = "recommended"

        if winner.total < 0.40:
            status = "no_suitable_source"

        elif len(candidates) > 1:
            second = candidates[1]

            # Very close candidates should not be presented as
            # confidently superior.
            if abs(winner.total - second.total) < 0.05:
                status = "tie"

        confidence = self._calculate_confidence(
            winner=winner,
            candidates=candidates,
        )

        reasoning = self._build_reasoning(
            winner=winner,
            candidates=candidates,
        )

        return Recommendation(
            requirement_id=entries[0].requirement_id,
            requirement_title=entries[0].requirement_title,
            recommended_submission_id=winner.submission_id,
            status=status,
            score=round(winner.total, 4),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            compatibility_risk=winner.compatibility_risk,
            unresolved_conflicts=winner.unresolved_conflicts,
            evidence_summary=winner.evidence_summary,
            alternatives=alternatives,
        )

    def _score_candidate(
        self,
        entry: MatrixEntry,
        profile: SubmissionProfile,
    ) -> CandidateScore:
        assessment = entry.assessment

        coverage_score = self._coverage_score(
            assessment.assessment
        )

        evidence_score = self._evidence_score(
            assessment.evidence
        )

        test_score = self._test_score(
            assessment.evidence
        )

        documentation_score = self._documentation_score(
            profile
        )

        architecture_score = self._architecture_score(
            profile
        )

        compatibility_score = self._compatibility_score(
            assessment.compatibility_risk
        )

        implementation_risk_score = self._implementation_risk_score(
            profile,
            assessment,
        )

        total = (
            coverage_score
            * self.WEIGHTS["coverage"]
            + evidence_score
            * self.WEIGHTS["evidence"]
            + test_score
            * self.WEIGHTS["tests"]
            + documentation_score
            * self.WEIGHTS["documentation"]
            + architecture_score
            * self.WEIGHTS["architecture"]
            + compatibility_score
            * self.WEIGHTS["compatibility"]
            + implementation_risk_score
            * self.WEIGHTS["implementation_risk"]
        )

        evidence_summary = self._build_evidence_summary(
            assessment.evidence
        )

        return CandidateScore(
            submission_id=entry.submission_id,
            total=max(0.0, min(1.0, total)),
            coverage_score=coverage_score,
            evidence_score=evidence_score,
            test_score=test_score,
            documentation_score=documentation_score,
            architecture_score=architecture_score,
            compatibility_score=compatibility_score,
            implementation_risk_score=implementation_risk_score,
            compatibility_risk=self._normalize_risk(
                assessment.compatibility_risk
            ),
            evidence_summary=evidence_summary,
            unresolved_conflicts=list(
                assessment.unresolved_conflicts
            ),
        )

    @staticmethod
    def _coverage_score(status: str) -> float:
        """
        Coverage is the strongest deterministic signal.

        Important:
        'complete' does not mean technically perfect.
        It means the existing analyzer found strong coverage.
        """

        return {
            "complete": 1.0,
            "partial": 0.60,
            "missing": 0.0,
            "not_verifiable": 0.25,
            "manual_review_required": 0.35,
        }.get(status, 0.0)

    @staticmethod
    def _evidence_score(evidence: list[dict]) -> float:
        if not evidence:
            return 0.0

        total = 0.0

        for item in evidence:
            relevance = item.get("relevanceScore")

            if relevance is None:
                relevance = item.get("relevance_score", 0.5)

            try:
                relevance = float(relevance)
            except (TypeError, ValueError):
                relevance = 0.5

            total += max(0.0, min(1.0, relevance))

        return min(1.0, total / max(1, len(evidence)))

    @staticmethod
    def _test_score(evidence: list[dict]) -> float:
        if not evidence:
            return 0.0

        test_count = 0
        total_count = 0

        for item in evidence:
            total_count += 1

            evidence_type = str(
                item.get("evidenceType")
                or item.get("evidence_type")
                or ""
            ).lower()

            path = str(item.get("path", "")).lower()

            if (
                "test" in evidence_type
                or "/test" in path
                or "test/" in path
                or path.startswith("test")
            ):
                test_count += 1

        return test_count / total_count

    @staticmethod
    def _documentation_score(
        profile: SubmissionProfile,
    ) -> float:
        if not profile.documentation_files:
            return 0.0

        return min(
            1.0,
            len(profile.documentation_files) / 5.0,
        )

    @staticmethod
    def _architecture_score(
        profile: SubmissionProfile,
    ) -> float:
        """
        A lightweight architecture signal.

        We reward evidence of a structured project rather than
        assuming that a particular framework is superior.
        """

        score = 0.0

        structure = profile.repository_structure

        if structure.source_files:
            score += 0.35

        if structure.test_files:
            score += 0.25

        if structure.configuration_files:
            score += 0.15

        if structure.documentation_files:
            score += 0.15

        if profile.technology.frameworks:
            score += 0.10

        return min(1.0, score)

    @staticmethod
    def _compatibility_score(
        risk: str,
    ) -> float:
        return {
            "low": 1.0,
            "medium": 0.65,
            "high": 0.25,
            "unknown": 0.50,
        }.get(
            str(risk).lower(),
            0.50,
        )

    @staticmethod
    def _implementation_risk_score(
        profile: SubmissionProfile,
        assessment,
    ) -> float:
        """
        Higher value means lower implementation risk.
        """

        score = 0.5

        if profile.build_test.build_commands:
            score += 0.15

        if profile.build_test.test_commands:
            score += 0.15

        if profile.build_test.package_manifests:
            score += 0.10

        if assessment.unresolved_conflicts:
            score -= min(
                0.25,
                len(assessment.unresolved_conflicts) * 0.05,
            )

        if profile.risks:
            score -= min(
                0.20,
                len(profile.risks) * 0.05,
            )

        return max(0.0, min(1.0, score))

    @staticmethod
    def _normalize_risk(
        risk: str,
    ) -> CompatibilityRisk:
        normalized = str(risk).lower()

        if normalized in {
            "low",
            "medium",
            "high",
        }:
            return normalized  # type: ignore[return-value]

        return "unknown"

    @staticmethod
    def _build_evidence_summary(
        evidence: list[dict],
    ) -> list[str]:
        summary: list[str] = []

        for item in evidence[:5]:
            path = item.get("path")

            if not path:
                locations = item.get("locations", [])

                if locations:
                    path = locations[0].get("path")

            if path:
                evidence_type = (
                    item.get("evidenceType")
                    or item.get("evidence_type")
                    or "evidence"
                )

                summary.append(
                    f"{evidence_type}: {path}"
                )

        return summary

    @staticmethod
    def _calculate_confidence(
        winner: CandidateScore,
        candidates: list[CandidateScore],
    ) -> float:
        """
        Confidence is intentionally separate from recommendation score.

        A candidate can score highly while confidence remains low if:
        - evidence is weak
        - the result is close to another candidate
        - compatibility is unknown
        """

        confidence = 0.50

        confidence += (
            winner.evidence_score * 0.20
        )

        confidence += (
            winner.coverage_score * 0.20
        )

        confidence += (
            winner.test_score * 0.10
        )

        if winner.compatibility_risk == "low":
            confidence += 0.05
        elif winner.compatibility_risk == "high":
            confidence -= 0.10

        if len(candidates) > 1:
            gap = winner.total - candidates[1].total

            if gap >= 0.20:
                confidence += 0.10
            elif gap < 0.05:
                confidence -= 0.15

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _build_reasoning(
        winner: CandidateScore,
        candidates: list[CandidateScore],
    ) -> str:
        reasons: list[str] = []

        if winner.coverage_score >= 0.8:
            reasons.append("strong requirement coverage")
        elif winner.coverage_score >= 0.5:
            reasons.append("partial requirement coverage")

        if winner.evidence_score >= 0.7:
            reasons.append("strong supporting evidence")
        elif winner.evidence_score < 0.4:
            reasons.append("limited supporting evidence")

        if winner.test_score >= 0.5:
            reasons.append("test evidence is available")

        if winner.documentation_score >= 0.5:
            reasons.append("useful documentation is available")

        if winner.compatibility_risk == "low":
            reasons.append("low compatibility risk")
        elif winner.compatibility_risk == "high":
            reasons.append("high compatibility risk")

        if winner.unresolved_conflicts:
            reasons.append(
                f"{len(winner.unresolved_conflicts)} unresolved conflict(s)"
            )

        if not reasons:
            reasons.append(
                "candidate has the strongest available deterministic score"
            )

        result = (
            f"{winner.submission_id} is recommended because "
            + ", ".join(reasons)
            + "."
        )

        if len(candidates) > 1:
            second = candidates[1]

            result += (
                f" Its score is {winner.total:.2f} versus "
                f"{second.submission_id} at {second.total:.2f}."
            )

        return result

    @staticmethod
    def _requirement_ids(
        matrix: RequirementMatrix,
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for entry in matrix.entries:
            if entry.requirement_id not in seen:
                seen.add(entry.requirement_id)
                result.append(entry.requirement_id)

        return result