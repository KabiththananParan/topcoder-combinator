from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.code_mode.pipeline import CodeModePipeline
from app.ideation.pipeline import IdeationPipeline, IdeationPlanResult
from app.ingestion.challenge_context import ChallengeContextLoader
from app.ingestion.models import ChallengeInventory
from app.ingestion.starter_pack_scanner import StarterPackScanner
from app.matrix.requirement_matrix import RequirementMatrixBuilder
from app.profiling.submission_profiler import SubmissionProfiler
from app.provenance.provenance_ledger import ProvenanceLedgerBuilder
from app.pipeline.recommendation_pipeline import RecommendationPipeline
from app.recommendation.evidence_enrichment import RecommendationEvidenceEnricher
from app.recommendation.recommendation_engine import RecommendationEngine
from app.decisions.decision_engine import DecisionEngine
from app.provenance.evidence_registration import EvidenceRegistrationService
from app.llm.factory import create_provider
from app.llm.provider import LLMProvider


@dataclass(frozen=True)
class ChallengeRunResult:
    challenge_id: str
    mode: str
    inventory: ChallengeInventory
    result: object


class ChallengeOrchestrator:
    """Top-level orchestration for one challenge at a time."""

    def __init__(
        self,
        starter_pack_path: Path | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.scanner = StarterPackScanner(starter_pack_path)
        self.provider = provider or create_provider()
        self.context_loader = ChallengeContextLoader()
        self.profiler = SubmissionProfiler()
        self.ideation_pipeline = IdeationPipeline()
        self.code_mode_pipeline = CodeModePipeline()

    def run(
        self,
        challenge_id: str,
        starter_pack_path: Path | None = None,
    ) -> ChallengeRunResult:
        inventories = self.scanner.scan(starter_pack_path)

        inventory = next(
            (
                item
                for item in inventories
                if item.challenge_id == challenge_id
            ),
            None,
        )

        if inventory is None:
            raise ValueError(
                f"Challenge not found: {challenge_id}"
            )

        context = self.context_loader.load(
            inventory.challenge_context_path
        )

        if inventory.mode == "ideation":
            result = self.ideation_pipeline.plan(
                challenge_id=challenge_id,
                submissions_root=inventory.root_path / "submissions",
                submission_ids=inventory.submission_ids,
            )

            return ChallengeRunResult(
                challenge_id=challenge_id,
                mode=inventory.mode,
                inventory=inventory,
                result=result,
            )

        if inventory.mode == "code":
            requirements = self.context_loader.load_requirements(
                inventory.challenge_context_path
            )

            profiles = {
                submission_id: self.profiler.profile(
                    submission_id,
                    inventory.root_path
                    / "submissions"
                    / submission_id,
                )
                for submission_id in inventory.submission_ids
            }

            matrix = RequirementMatrixBuilder(
                challenge_id=challenge_id,
                challenge_root=inventory.root_path,
            ).build(
                requirements=requirements,
                submission_ids=inventory.submission_ids,
            )

            recommendation_pipeline = RecommendationPipeline(
                recommendation_engine=RecommendationEngine(),
                decision_engine=DecisionEngine(),
                evidence_registration_service=(
                    EvidenceRegistrationService()
                ),
                evidence_enricher=RecommendationEvidenceEnricher(),
            )

            recommendation_result = recommendation_pipeline.run(
                challenge_id=challenge_id,
                matrix=matrix,
                profiles=profiles,
                ledger_builder=ProvenanceLedgerBuilder(
                    challenge_id=challenge_id
                ),
            )

            if any(
                decision.state == "pending"
                for decision in recommendation_result.decisions.decisions
            ):
                return ChallengeRunResult(
                    challenge_id=challenge_id,
                    mode=inventory.mode,
                    inventory=inventory,
                    result=recommendation_result,
                )

            code_plan = self.code_mode_pipeline.plan(
                challenge_id=challenge_id,
                matrix=matrix,
                profiles=profiles,
                recommendations=(
                    recommendation_result.recommendations
                ),
                decisions=recommendation_result.decisions,
                ledger=recommendation_result.provenance,
            )

            return ChallengeRunResult(
                challenge_id=challenge_id,
                mode=inventory.mode,
                inventory=inventory,
                result=code_plan,
            )

        raise ValueError(
            f"Unsupported challenge mode: {context.get('challengeMode')}"
        )
