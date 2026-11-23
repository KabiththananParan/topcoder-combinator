from dataclasses import dataclass

from app.decisions.models import DecisionSet
from app.ideation.decision_adapter import IdeationDecisionAdapter
from app.ideation.evaluation_engine import IdeationEvaluationEngine
from app.ideation.recommendation_engine import IdeationRecommendationEngine
from app.ideation.evaluation_models import IdeationEvaluation
from app.ideation.recommendation_models import IdeationRecommendationSet
from app.ideation.idea_analyzer import IdeationAnalyzer
from app.ideation.idea_models import IdeaComponent
from app.ideation.submission_profiler import IdeationSubmissionProfiler
from app.ideation.synthesis import IdeationSynthesizer, SynthesizedConcept
from app.ideation.provenance import IdeationProvenanceBuilder
from app.provenance.models import ProvenanceLedger
from app.ideation.verification import IdeationVerificationResult, IdeationVerifier


@dataclass(frozen=True)
class IdeationPlanResult:
    challenge_id: str
    ideas: list[IdeaComponent]
    evaluation: IdeationEvaluation
    recommendations: IdeationRecommendationSet
    decisions: DecisionSet
    verification: IdeationVerificationResult
    synthesized_concept: SynthesizedConcept
    provenance: ProvenanceLedger


class IdeationPipeline:
    """Orchestrates Ideation Mode analysis and criterion evaluation."""

    def __init__(self) -> None:
        self.profiler = IdeationSubmissionProfiler()
        self.analyzer = IdeationAnalyzer()
        self.evaluation_engine = IdeationEvaluationEngine()
        self.recommendation_engine = IdeationRecommendationEngine()
        self.decision_adapter = IdeationDecisionAdapter()

    def plan(
        self,
        challenge_id: str,
        submissions_root,
        submission_ids: list[str],
        persisted_decisions: DecisionSet | None = None,
    ) -> IdeationPlanResult:
        ideas: list[IdeaComponent] = []

        for submission_id in submission_ids:
            profiles = self.profiler.profile(
                submission_id,
                submissions_root / submission_id,
            )
            ideas.extend(
                self.analyzer.to_component(
                    candidate,
                    self.analyzer.to_evidence_refs(candidate, profiles),
                )
                for candidate in self.analyzer.analyze(
                    submission_id,
                    profiles,
                )
            )

        evaluation = self.evaluation_engine.evaluate(
            challenge_id=challenge_id,
            ideas=ideas,
        )

        recommendations = self.recommendation_engine.recommend(
            challenge_id=challenge_id,
            evaluation=evaluation,
        )

        decisions = self.decision_adapter.create_pending_decisions(
            recommendations
        )
        if persisted_decisions is not None:
            decisions = self.decision_adapter.reconcile_persisted_decisions(
                recommendations,
                persisted_decisions,
            )

        synthesized_concept = IdeationSynthesizer().synthesize(
            challenge_id=challenge_id,
            ideas=ideas,
            decisions=decisions,
        )

        verification = IdeationVerifier().verify(
            ideas=ideas,
            evaluation=evaluation,
            decisions=decisions,
            synthesized_concept=synthesized_concept,
        )

        provenance = IdeationProvenanceBuilder().build(
            challenge_id=challenge_id,
            ideas=ideas,
            evaluation=evaluation,
            recommendations=recommendations,
            decisions=decisions,
        )

        return IdeationPlanResult(
            challenge_id=challenge_id,
            ideas=ideas,
            evaluation=evaluation,
            recommendations=recommendations,
            decisions=decisions,
            verification=verification,
            synthesized_concept=synthesized_concept,
            provenance=provenance,
        )
