from dataclasses import dataclass

from app.matrix.models import RequirementMatrix
from app.profiling.models import SubmissionProfile
from app.recommendation.models import RecommendationSet

from .models import BaseSelection


@dataclass(frozen=True)
class _SubmissionSignals:
    submission_id: str
    coverage: float
    evidence: float
    tests: float
    documentation: float
    architecture: float
    compatibility: float
    implementation_risk: float

    @property
    def score(self) -> float:
        return (
            self.coverage * 0.30
            + self.evidence * 0.15
            + self.tests * 0.15
            + self.documentation * 0.10
            + self.architecture * 0.10
            + self.compatibility * 0.15
            + self.implementation_risk * 0.05
        )


class BaseSubmissionSelector:
    """
    Selects the strongest runnable base submission for Code Mode.

    This selector deliberately does not use final challenge scores.
    """

    def select(
        self,
        challenge_id: str,
        matrix: RequirementMatrix,
        profiles: list[SubmissionProfile],
        recommendations: RecommendationSet,
    ) -> BaseSelection:

        if not profiles:
            return BaseSelection(
                challenge_id=challenge_id,
                selected_submission_id=None,
                status="no_suitable_base",
                score=0.0,
                confidence=0.0,
                reasoning="No submission profiles were provided.",
            )

        signals = [
            self._calculate_signals(
                profile=profile,
                matrix=matrix,
                recommendations=recommendations,
            )
            for profile in profiles
        ]

        signals.sort(key=lambda item: item.score, reverse=True)

        best = signals[0]

        if best.score <= 0:
            return BaseSelection(
                challenge_id=challenge_id,
                selected_submission_id=None,
                status="no_suitable_base",
                score=best.score,
                confidence=0.0,
                reasoning="No submission has sufficient evidence to serve as a base.",
                alternatives=[
                    signal.submission_id
                    for signal in signals[1:]
                ],
            )

        alternatives = [
            signal.submission_id
            for signal in signals
            if signal.submission_id != best.submission_id
        ]

        if len(signals) > 1:
            second = signals[1]

            if abs(best.score - second.score) <= 0.05:
                return BaseSelection(
                    challenge_id=challenge_id,
                    selected_submission_id=None,
                    status="tie",
                    score=best.score,
                    confidence=0.5,
                    reasoning=(
                        f"{best.submission_id} and {second.submission_id} "
                        "are too close to select a base automatically."
                    ),
                    alternatives=[
                        signal.submission_id
                        for signal in signals
                    ],
                )

        confidence = self._confidence(signals)

        risks = self._identify_risks(best)

        reasoning = self._build_reasoning(best)

        return BaseSelection(
            challenge_id=challenge_id,
            selected_submission_id=best.submission_id,
            status="selected",
            score=best.score,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            risks=risks,
        )

    def _calculate_signals(
        self,
        profile: SubmissionProfile,
        matrix: RequirementMatrix,
        recommendations: RecommendationSet,
    ) -> _SubmissionSignals:

        entries = matrix.for_submission(profile.submission_id)

        if entries:
            complete = sum(
                entry.assessment.assessment == "complete"
                for entry in entries
            )

            partial = sum(
                entry.assessment.assessment == "partial"
                for entry in entries
            )

            coverage = (
                (complete + 0.5 * partial) / len(entries)
            )
        else:
            coverage = 0.0

        evidence = self._evidence_score(entries)
        tests = self._test_score(profile)
        documentation = self._documentation_score(profile)
        architecture = self._architecture_score(profile)
        compatibility = self._compatibility_score(entries)
        implementation_risk = self._implementation_risk_score(
            profile,
            entries,
        )

        return _SubmissionSignals(
            submission_id=profile.submission_id,
            coverage=coverage,
            evidence=evidence,
            tests=tests,
            documentation=documentation,
            architecture=architecture,
            compatibility=compatibility,
            implementation_risk=implementation_risk,
        )

    @staticmethod
    def _evidence_score(entries) -> float:
        if not entries:
            return 0.0

        scores = [
            entry.assessment.confidence
            for entry in entries
        ]

        return sum(scores) / len(scores)

    @staticmethod
    def _test_score(profile: SubmissionProfile) -> float:
        if not profile.build_test.test_commands:
            return 0.0

        return min(
            1.0,
            len(profile.build_test.test_commands) / 2,
        )

    @staticmethod
    def _documentation_score(profile: SubmissionProfile) -> float:
        if not profile.documentation_files:
            return 0.0

        return min(
            1.0,
            len(profile.documentation_files) / 3,
        )

    @staticmethod
    def _architecture_score(profile: SubmissionProfile) -> float:
        structure = profile.repository_structure

        source_count = len(structure.source_files)

        if source_count == 0:
            return 0.0

        directory_count = len(structure.directories)

        if directory_count >= 5:
            return 1.0

        return min(1.0, directory_count / 5)

    @staticmethod
    def _compatibility_score(entries) -> float:
        if not entries:
            return 0.0

        values = []

        for entry in entries:
            risk = entry.assessment.compatibility_risk

            if risk == "low":
                values.append(1.0)
            elif risk == "medium":
                values.append(0.6)
            elif risk == "high":
                values.append(0.2)
            else:
                values.append(0.5)

        return sum(values) / len(values)

    @staticmethod
    def _implementation_risk_score(
        profile: SubmissionProfile,
        entries,
    ) -> float:
        score = 1.0

        score -= min(
            0.4,
            len(profile.risks) * 0.1,
        )

        unresolved = sum(
            len(entry.assessment.unresolved_conflicts)
            for entry in entries
        )

        score -= min(
            0.4,
            unresolved * 0.1,
        )

        return max(0.0, score)

    @staticmethod
    def _confidence(signals: list[_SubmissionSignals]) -> float:
        if len(signals) == 1:
            return 0.8

        gap = signals[0].score - signals[1].score

        return min(
            0.95,
            0.55 + gap * 2,
        )

    @staticmethod
    def _identify_risks(
        signal: _SubmissionSignals,
    ) -> list[str]:
        risks = []

        if signal.tests < 0.5:
            risks.append("limited_test_evidence")

        if signal.documentation < 0.5:
            risks.append("limited_documentation")

        if signal.compatibility < 0.5:
            risks.append("compatibility_risk")

        if signal.implementation_risk < 0.7:
            risks.append("implementation_risk")

        return risks

    @staticmethod
    def _build_reasoning(
        signal: _SubmissionSignals,
    ) -> str:
        return (
            f"{signal.submission_id} selected as the Code Mode base because "
            f"it has the strongest combined profile across requirement "
            f"coverage, evidence, testing, documentation, architecture, "
            f"compatibility, and implementation risk "
            f"(score={signal.score:.3f}). "
            "Final challenge score was not used."
        )