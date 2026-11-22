from app.ideation.evaluation_models import (
    CriterionEvaluation,
    IdeationCriterion,
    IdeationEvaluation,
)
from app.ideation.idea_models import IdeaComponent


class IdeationEvaluationEngine:
    """
    Deterministic criterion-level evaluation for Ideation Mode.

    The challenge specification supplies five evaluation criteria.
    It does not supply criterion weights, so this engine does not
    invent weighted scoring.
    """

    CRITERIA: tuple[IdeationCriterion, ...] = (
        "Originality",
        "Feasibility",
        "Scalability",
        "Impact Potential",
        "Alignment with Scope",
    )

    def evaluate(
        self,
        challenge_id: str,
        ideas: list[IdeaComponent],
    ) -> IdeationEvaluation:
        evaluations: list[CriterionEvaluation] = []

        for idea in ideas:
            for criterion in self.CRITERIA:
                evaluations.append(
                    self._evaluate_criterion(
                        idea=idea,
                        criterion=criterion,
                    )
                )

        return IdeationEvaluation(
            challenge_id=challenge_id,
            evaluations=evaluations,
        )

    def _evaluate_criterion(
        self,
        idea: IdeaComponent,
        criterion: IdeationCriterion,
    ) -> CriterionEvaluation:
        if criterion == "Originality":
            return self._evaluate_originality(idea)

        if criterion == "Feasibility":
            return self._evaluate_feasibility(idea)

        if criterion == "Scalability":
            return self._evaluate_scalability(idea)

        if criterion == "Impact Potential":
            return self._evaluate_impact(idea)

        if criterion == "Alignment with Scope":
            return self._evaluate_alignment(idea)

        raise NotImplementedError(
            f"Criterion evaluation is not implemented yet: {criterion}"
        )

    @staticmethod
    def _evaluate_originality(
        idea: IdeaComponent,
    ) -> CriterionEvaluation:
        evidence_refs = list(idea.evidence_refs)

        if not idea.differentiators:
            return CriterionEvaluation(
                idea_id=idea.idea_id,
                submission_id=idea.submission_id,
                criterion="Originality",
                status="missing",
                score=0.0,
                confidence=0.0,
                reasoning="No differentiator evidence was extracted.",
                evidence_refs=evidence_refs,
            )

        strength = len(idea.differentiators)

        if strength >= 3:
            status = "complete"
            score = 1.0
            confidence = 0.85
        else:
            status = "partial"
            score = 0.6
            confidence = 0.65

        return CriterionEvaluation(
            idea_id=idea.idea_id,
            submission_id=idea.submission_id,
            criterion="Originality",
            status=status,
            score=score,
            confidence=confidence,
            reasoning=(
                "Originality is supported by extracted differentiators "
                "that distinguish the proposed concept."
            ),
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _evaluate_alignment(
        idea: IdeaComponent,
    ) -> CriterionEvaluation:
        evidence_refs = list(idea.evidence_refs)

        if not idea.problem.strip():
            return CriterionEvaluation(
                idea_id=idea.idea_id,
                submission_id=idea.submission_id,
                criterion="Alignment with Scope",
                status="missing",
                score=0.0,
                confidence=0.0,
                reasoning="No problem statement evidence was extracted.",
                evidence_refs=evidence_refs,
            )

        supporting_fields = sum(
            bool(value)
            for value in (
                idea.problem,
                idea.proposed_agents,
                idea.sdlc_phases,
                idea.users,
                idea.workflow,
            )
        )

        if supporting_fields >= 4:
            status = "complete"
            score = 1.0
            confidence = 0.85
        else:
            status = "partial"
            score = 0.6
            confidence = 0.65

        return CriterionEvaluation(
            idea_id=idea.idea_id,
            submission_id=idea.submission_id,
            criterion="Alignment with Scope",
            status=status,
            score=score,
            confidence=confidence,
            reasoning=(
                "Alignment with scope is supported by the extracted "
                "problem, agent, SDLC, user, and workflow signals."
            ),
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _evaluate_impact(
        idea: IdeaComponent,
    ) -> CriterionEvaluation:
        evidence_refs = list(idea.evidence_refs)

        if not idea.impact.strip():
            return CriterionEvaluation(
                idea_id=idea.idea_id,
                submission_id=idea.submission_id,
                criterion="Impact Potential",
                status="missing",
                score=0.0,
                confidence=0.0,
                reasoning="No impact evidence was extracted.",
                evidence_refs=evidence_refs,
            )

        supporting_fields = sum(
            bool(value)
            for value in (
                idea.users,
                idea.beneficiaries,
                idea.workflow,
                idea.differentiators,
            )
        )

        if supporting_fields >= 3:
            status = "complete"
            score = 1.0
            confidence = 0.85
        else:
            status = "partial"
            score = 0.6
            confidence = 0.65

        return CriterionEvaluation(
            idea_id=idea.idea_id,
            submission_id=idea.submission_id,
            criterion="Impact Potential",
            status=status,
            score=score,
            confidence=confidence,
            reasoning=(
                "Impact potential is supported by the extracted impact "
                "assessment and concrete user, beneficiary, workflow, "
                "or differentiation signals."
            ),
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _evaluate_scalability(
        idea: IdeaComponent,
    ) -> CriterionEvaluation:
        evidence_refs = list(idea.evidence_refs)

        if not idea.scalability.strip():
            return CriterionEvaluation(
                idea_id=idea.idea_id,
                submission_id=idea.submission_id,
                criterion="Scalability",
                status="missing",
                score=0.0,
                confidence=0.0,
                reasoning="No scalability evidence was extracted.",
                evidence_refs=evidence_refs,
            )

        supporting_fields = sum(
            bool(value)
            for value in (
                idea.proposed_agents,
                idea.workflow,
                idea.integrations,
            )
        )

        if supporting_fields >= 3:
            status = "complete"
            score = 1.0
            confidence = 0.85
        else:
            status = "partial"
            score = 0.6
            confidence = 0.65

        return CriterionEvaluation(
            idea_id=idea.idea_id,
            submission_id=idea.submission_id,
            criterion="Scalability",
            status=status,
            score=score,
            confidence=confidence,
            reasoning=(
                "Scalability is supported by the extracted scalability "
                "assessment and concrete expansion signals."
            ),
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _evaluate_feasibility(
        idea: IdeaComponent,
    ) -> CriterionEvaluation:
        evidence_refs = list(idea.evidence_refs)

        if not idea.feasibility.strip():
            return CriterionEvaluation(
                idea_id=idea.idea_id,
                submission_id=idea.submission_id,
                criterion="Feasibility",
                status="missing",
                score=0.0,
                confidence=0.0,
                reasoning="No feasibility evidence was extracted.",
                evidence_refs=evidence_refs,
            )

        supporting_fields = sum(
            bool(value)
            for value in (
                idea.proposed_agents,
                idea.workflow,
                idea.data,
                idea.integrations,
                idea.security,
            )
        )

        if supporting_fields >= 3:
            status = "complete"
            score = 1.0
            confidence = 0.85
        else:
            status = "partial"
            score = 0.6
            confidence = 0.65

        return CriterionEvaluation(
            idea_id=idea.idea_id,
            submission_id=idea.submission_id,
            criterion="Feasibility",
            status=status,
            score=score,
            confidence=confidence,
            reasoning=(
                "Feasibility is supported by the extracted feasibility "
                "assessment and concrete implementation signals."
            ),
            evidence_refs=evidence_refs,
        )
