from dataclasses import dataclass
from pathlib import Path

from app.decisions.models import DecisionSet
from app.matrix.models import RequirementMatrix
from app.profiling.models import SubmissionProfile
from app.provenance.execution_provenance import (
    ExecutionProvenanceRecorder,
)
from app.provenance.models import ProvenanceLedger
from app.recommendation.models import RecommendationSet

from .base_selector import BaseSubmissionSelector
from .candidate_orchestrator import (
    CandidateExecutionResult,
    CandidateOrchestrator,
)
from .models import BaseSelection
from .transplant_plan import TransplantPlan, TransplantPlanBuilder
from .verification_runner import VerificationCommand


@dataclass(frozen=True)
class CodeModePlanResult:
    challenge_id: str
    base_selection: BaseSelection
    transplant_plan: TransplantPlan
    provenance: ProvenanceLedger


@dataclass(frozen=True)
class CodeModeExecutionResult:
    challenge_id: str
    base_selection: BaseSelection
    transplant_plan: TransplantPlan
    execution: CandidateExecutionResult
    provenance: ProvenanceLedger


class CodeModePipeline:
    """
    Orchestrates Code Mode after Copilot decisions exist.

    Flow:

        recommendations
              ↓
        approved decisions
              ↓
        base selection
              ↓
        transplant plan
              ↓
        candidate execution
              ↓
        verification / rollback
              ↓
        execution provenance

    This class does not modify source submissions directly.
    """

    def __init__(
        self,
        base_selector: BaseSubmissionSelector | None = None,
        transplant_plan_builder: TransplantPlanBuilder | None = None,
        candidate_orchestrator: CandidateOrchestrator | None = None,
    ):
        self.base_selector = (
            base_selector or BaseSubmissionSelector()
        )
        self.transplant_plan_builder = (
            transplant_plan_builder
            or TransplantPlanBuilder()
        )
        self.candidate_orchestrator = (
            candidate_orchestrator
            or CandidateOrchestrator()
        )

    def plan(
        self,
        challenge_id: str,
        matrix: RequirementMatrix,
        profiles: dict[str, SubmissionProfile],
        recommendations: RecommendationSet,
        decisions: DecisionSet,
        ledger: ProvenanceLedger,
    ) -> CodeModePlanResult:

        if matrix.challenge_id != challenge_id:
            raise ValueError(
                "Matrix challenge does not match Code Mode challenge."
            )

        if recommendations.challenge_id != challenge_id:
            raise ValueError(
                "Recommendations challenge does not match "
                "Code Mode challenge."
            )

        if decisions.challenge_id != challenge_id:
            raise ValueError(
                "Decisions challenge does not match "
                "Code Mode challenge."
            )

        profile_list = list(profiles.values())

        base_selection = self.base_selector.select(
            challenge_id=challenge_id,
            matrix=matrix,
            profiles=profile_list,
            recommendations=recommendations,
        )

        if base_selection.selected_submission_id is None:
            raise ValueError(
                "Code Mode cannot create a transplant plan without "
                "a selected base submission."
            )

        submission_ids = list(profiles.keys())

        transplant_plan = self.transplant_plan_builder.build(
            challenge_id=challenge_id,
            base_submission_id=(
                base_selection.selected_submission_id
            ),
            decisions=decisions,
            submission_ids=submission_ids,
            matrix=matrix,
            profiles=profiles,
            provenance=ledger,
        )

        recorder = ExecutionProvenanceRecorder(ledger)

        for item in transplant_plan.items:
            if item.action == "transplant":
                recorder.record_transplant_planned(
                    requirement_id=item.requirement_id,
                    source_submission_id=(
                        item.source_submission_id
                    ),
                    target_submission_id=(
                        item.target_submission_id
                    ),
                    reason=item.reason,
                    evidence_ids=item.evidence_refs,
                )

        return CodeModePlanResult(
            challenge_id=challenge_id,
            base_selection=base_selection,
            transplant_plan=transplant_plan,
            provenance=recorder.get_ledger(),
        )

    def execute(
        self,
        challenge_id: str,
        plan: CodeModePlanResult,
        submissions_root: Path,
        candidate_root: Path,
        verification_commands: list[VerificationCommand],
    ) -> CodeModeExecutionResult:

        execution = self.candidate_orchestrator.execute(
            challenge_id=challenge_id,
            plan=plan.transplant_plan,
            submissions_root=submissions_root,
            candidate_root=candidate_root,
            verification_commands=verification_commands,
        )

        recorder = ExecutionProvenanceRecorder(
            plan.provenance
        )

        planned_events = {
            event.requirement_id: event
            for event in recorder.get_ledger().events
            if event.event_type == "transplant_planned"
        }

        for result in execution.results:
            requirement_id = result.requirement_id

            planned_event = planned_events.get(
                requirement_id
            )

            related_event_ids = (
                [planned_event.event_id]
                if planned_event is not None
                else []
            )

            if result.final_status == "kept":
                applied = recorder.record_transplant_applied(
                    requirement_id=requirement_id,
                    source_submission_id=(
                        result.transplant.source_submission_id
                    ),
                    target_submission_id=(
                        result.transplant.target_submission_id
                    ),
                    source_path=result.transplant.source_path,
                    target_path=result.transplant.target_path,
                    related_event_ids=related_event_ids,
                )

                verification_started = (
                    recorder.record_verification_started(
                        requirement_id=requirement_id,
                        related_event_ids=[
                            applied.event_id
                        ],
                    )
                )

                recorder.record_verification_completed(
                    requirement_id=requirement_id,
                    related_event_ids=[
                        verification_started.event_id
                    ],
                    metadata={
                        "finalStatus": result.final_status,
                    },
                )

            elif result.final_status == "rolled_back":
                applied = recorder.record_transplant_applied(
                    requirement_id=requirement_id,
                    source_submission_id=(
                        result.transplant.source_submission_id
                    ),
                    target_submission_id=(
                        result.transplant.target_submission_id
                    ),
                    source_path=result.transplant.source_path,
                    target_path=result.transplant.target_path,
                    related_event_ids=related_event_ids,
                )

                verification_started = (
                    recorder.record_verification_started(
                        requirement_id=requirement_id,
                        related_event_ids=[
                            applied.event_id
                        ],
                    )
                )

                verification_failed = (
                    recorder.record_verification_failed(
                        requirement_id=requirement_id,
                        related_event_ids=[
                            verification_started.event_id
                        ],
                        metadata={
                            "errors": (
                                result.verification.errors
                            ),
                        },
                    )
                )

                recorder.record_rollback(
                    requirement_id=requirement_id,
                    related_event_ids=[
                        verification_failed.event_id
                    ],
                )

            elif result.final_status == "failed":
                recorder.record_verification_failed(
                    requirement_id=requirement_id,
                    related_event_ids=related_event_ids,
                    metadata={
                        "errors": (
                            result.verification.errors
                        ),
                    },
                )

        return CodeModeExecutionResult(
            challenge_id=challenge_id,
            base_selection=plan.base_selection,
            transplant_plan=plan.transplant_plan,
            execution=execution,
            provenance=recorder.get_ledger(),
        )