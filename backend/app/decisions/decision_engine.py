from dataclasses import replace

from app.recommendation.models import Recommendation
from app.recommendation.models import RecommendationSet

from .models import (
    Decision,
    DecisionSet,
    DecisionState,
)


class DecisionEngine:
    """
    Creates and applies explicit Copilot decisions.

    Recommendation != decision.

    The recommendation engine proposes a source.
    This component records what the user/Copilot actually decided.
    """

    def create_pending_decisions(
        self,
        recommendations: RecommendationSet,
    ) -> DecisionSet:
        decisions: list[Decision] = []

        for recommendation in recommendations.recommendations:
            decisions.append(
                Decision(
                    requirement_id=recommendation.requirement_id,
                    requirement_title=(
                        recommendation.requirement_title
                    ),
                    state="pending",
                    recommended_submission_id=(
                        recommendation.recommended_submission_id
                    ),
                    recommendation_score=(
                        recommendation.score
                    ),
                    recommendation_confidence=(
                        recommendation.confidence
                    ),
                    evidence_refs=self._evidence_refs(
                        recommendation
                    ),
                )
            )

        return DecisionSet(
            challenge_id=recommendations.challenge_id,
            decisions=decisions,
        )

    def accept(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        *,
        reason: str = "",
        reviewer: str | None = None,
    ) -> DecisionSet:
        decision = self._get(
            decisions,
            requirement_id,
        )

        self._require_recommendation(
            decision
        )

        updated = replace(
            decision,
            state="accepted",
            selected_submission_id=(
                decision.recommended_submission_id
            ),
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    def reject(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        *,
        reason: str,
        reviewer: str | None = None,
    ) -> DecisionSet:
        if not reason.strip():
            raise ValueError(
                "A reason is required when rejecting a recommendation."
            )

        decision = self._get(
            decisions,
            requirement_id,
        )

        updated = replace(
            decision,
            state="rejected",
            selected_submission_id=None,
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    def select_alternative(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        alternative_submission_id: str,
        *,
        reason: str,
        reviewer: str | None = None,
    ) -> DecisionSet:
        if not reason.strip():
            raise ValueError(
                "A reason is required when selecting an alternative."
            )

        decision = self._get(
            decisions,
            requirement_id,
        )

        if (
            alternative_submission_id
            == decision.recommended_submission_id
        ):
            raise ValueError(
                "Alternative submission must differ from "
                "the recommended submission."
            )

        updated = replace(
            decision,
            state="alternative_selected",
            selected_submission_id=(
                alternative_submission_id
            ),
            alternative_submission_id=(
                alternative_submission_id
            ),
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    def block(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        *,
        reason: str,
        reviewer: str | None = None,
    ) -> DecisionSet:
        if not reason.strip():
            raise ValueError(
                "A reason is required when blocking a decision."
            )

        decision = self._get(
            decisions,
            requirement_id,
        )

        updated = replace(
            decision,
            state="blocked",
            selected_submission_id=None,
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    def manual_review(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        *,
        reason: str,
        reviewer: str | None = None,
    ) -> DecisionSet:
        if not reason.strip():
            raise ValueError(
                "A reason is required for manual review."
            )

        decision = self._get(
            decisions,
            requirement_id,
        )

        updated = replace(
            decision,
            state="manual_review",
            selected_submission_id=None,
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    def unresolved(
        self,
        decisions: DecisionSet,
        requirement_id: str,
        *,
        reason: str,
        reviewer: str | None = None,
    ) -> DecisionSet:
        if not reason.strip():
            raise ValueError(
                "A reason is required for an unresolved decision."
            )

        decision = self._get(
            decisions,
            requirement_id,
        )

        updated = replace(
            decision,
            state="unresolved",
            selected_submission_id=None,
            reason=reason,
            reviewer=reviewer,
        )

        return self._replace(
            decisions,
            updated,
        )

    @staticmethod
    def _evidence_refs(
        recommendation: Recommendation,
    ) -> list[str]:
        """
        Preserve evidence references from the recommendation.

        The actual provenance layer will later convert these
        into richer structured evidence records.
        """

        return list(
            recommendation.evidence_summary
        )

    @staticmethod
    def _get(
        decisions: DecisionSet,
        requirement_id: str,
    ) -> Decision:
        decision = decisions.for_requirement(
            requirement_id
        )

        if decision is None:
            raise KeyError(
                f"No decision exists for requirement: "
                f"{requirement_id}"
            )

        return decision

    @staticmethod
    def _require_recommendation(
        decision: Decision,
    ) -> None:
        if not decision.recommended_submission_id:
            raise ValueError(
                "Cannot accept a recommendation without "
                "a recommended submission."
            )

    @staticmethod
    def _replace(
        decisions: DecisionSet,
        updated: Decision,
    ) -> DecisionSet:
        result: list[Decision] = []

        for decision in decisions.decisions:
            if (
                decision.requirement_id
                == updated.requirement_id
            ):
                result.append(updated)
            else:
                result.append(decision)

        return DecisionSet(
            challenge_id=decisions.challenge_id,
            decisions=result,
        )