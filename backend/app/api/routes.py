import shutil
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ingestion.starter_pack_scanner import StarterPackScanner
from app.decisions.persistence import DecisionPersistence
from app.code_mode.safe_workspace import resolve_safe_path
from app.workspace.writer import WorkspaceWriter

router = APIRouter(prefix="/api")


@router.get("/challenges")
def list_challenges():
    starter_pack = Path("../starter-pack").resolve()
    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    return {
        "challenges": [
            {
                "challengeId": item.challenge_id,
                "mode": item.mode,
                "submissionIds": item.submission_ids,
            }
            for item in inventories
        ]
    }


@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    context_path = inventory.challenge_context_path
    context = __import__("json").loads(
        context_path.read_text(encoding="utf-8")
    )

    return {
        "challengeId": inventory.challenge_id,
        "mode": inventory.mode,
        "submissionIds": inventory.submission_ids,
        "context": context,
    }


@router.get("/challenges/{challenge_id}/review-context")
def get_review_context_status(challenge_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if inventory.review_context_path is None:
        return {
            "challengeId": challenge_id,
            "status": "NOT_PROVIDED",
            "mode": "specification_derived",
        }

    try:
        context = __import__("json").loads(
            inventory.review_context_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load review context: {exc}",
        ) from exc

    return {
        "challengeId": challenge_id,
        "status": context.get("status"),
        "mode": context.get("mode"),
        "context": context,
    }


@router.get("/challenges/{challenge_id}/submissions/{submission_id}/profile")
def get_submission_profile(challenge_id: str, submission_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if submission_id not in inventory.submission_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Submission not found: {submission_id}",
        )

    profile = __import__(
        "app.profiling.submission_profiler",
        fromlist=["SubmissionProfiler"],
    ).SubmissionProfiler().profile(
        submission_id,
        inventory.root_path / "submissions" / submission_id,
    )

    return {
        "challengeId": challenge_id,
        "submissionId": submission_id,
        "profile": profile,
    }


@router.get("/challenges/{challenge_id}/requirement-matrix")
def get_requirement_matrix(challenge_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if inventory.mode != "code":
        raise HTTPException(
            status_code=400,
            detail="Requirement matrix is only available for code challenges",
        )

    from app.ingestion.challenge_context import ChallengeContextLoader
    from app.matrix.requirement_matrix import RequirementMatrixBuilder

    requirements = ChallengeContextLoader().load_requirements(
        inventory.challenge_context_path
    )

    matrix = RequirementMatrixBuilder(
        challenge_id=challenge_id,
        challenge_root=inventory.root_path,
    ).build(
        requirements=requirements,
        submission_ids=inventory.submission_ids,
    )

    return {
        "challengeId": challenge_id,
        "requirements": matrix,
    }


@router.get("/challenges/{challenge_id}/decisions")
def get_decisions(challenge_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if inventory.mode != "code":
        raise HTTPException(
            status_code=400,
            detail="Decisions endpoint currently targets code challenges",
        )

    persistence = DecisionPersistence(Path("../workspace").resolve())
    saved_decisions = persistence.load(challenge_id)

    if saved_decisions is not None:
        _write_code_workspace(inventory, saved_decisions)
        return saved_decisions.to_dict()

    from app.ingestion.challenge_context import ChallengeContextLoader
    from app.matrix.requirement_matrix import RequirementMatrixBuilder
    from app.profiling.submission_profiler import SubmissionProfiler
    from app.pipeline.recommendation_pipeline import RecommendationPipeline
    from app.recommendation.recommendation_engine import RecommendationEngine
    from app.recommendation.evidence_enrichment import RecommendationEvidenceEnricher
    from app.decisions.decision_engine import DecisionEngine
    from app.provenance.evidence_registration import EvidenceRegistrationService
    from app.provenance.provenance_ledger import ProvenanceLedgerBuilder

    requirements = ChallengeContextLoader().load_requirements(
        inventory.challenge_context_path
    )

    profiles = {
        submission_id: SubmissionProfiler().profile(
            submission_id,
            inventory.root_path / "submissions" / submission_id,
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

    result = RecommendationPipeline(
        recommendation_engine=RecommendationEngine(),
        decision_engine=DecisionEngine(),
        evidence_registration_service=EvidenceRegistrationService(),
        evidence_enricher=RecommendationEvidenceEnricher(),
    ).run(
        challenge_id=challenge_id,
        matrix=matrix,
        profiles=profiles,
        ledger_builder=ProvenanceLedgerBuilder(
            challenge_id=challenge_id
        ),
    )

    persistence.save(result.decisions)
    _write_code_workspace(inventory, result.decisions, result=result)

    return result.decisions.to_dict()


@router.get("/challenges/{challenge_id}/verification")
def get_verification(challenge_id: str):
    """Return the generated verification and trace artifacts for the workspace."""
    starter_pack = Path("../starter-pack").resolve()
    inventories = StarterPackScanner(starter_pack).scan()
    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )
    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if inventory.mode == "ideation":
        get_ideation_analysis(challenge_id)
    else:
        get_decisions(challenge_id)

    workspace = Path("../workspace").resolve() / challenge_id

    def read_artifact(name: str, default: dict) -> dict:
        path = workspace / name
        if not path.is_file():
            return default
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load workspace artifact: {name}",
            ) from exc
        return value if isinstance(value, dict) else default

    decisions = read_artifact("decisions.json", {"decisions": []})
    return {
        "challengeId": challenge_id,
        "mode": inventory.mode,
        "verification": read_artifact("verification.json", {}),
        "provenance": read_artifact("provenance.json", {}),
        "contradictions": read_artifact("contradictions.json", {}),
        "usage": read_artifact("llm-usage.json", {}),
        "decisions": decisions,
        "candidateStatus": read_artifact("candidate-status.json", {}),
        "baseSelection": read_artifact("base-selection.json", {}),
        "synthesis": read_artifact(
            "synthesized-concept/concept.json",
            {},
        ),
    }


def _write_code_workspace(inventory, decisions, result=None):
    """Materialize code-mode state from the current persisted decisions."""
    from app.ingestion.challenge_context import ChallengeContextLoader
    from app.matrix.requirement_matrix import RequirementMatrixBuilder
    from app.profiling.submission_profiler import SubmissionProfiler
    from app.pipeline.recommendation_pipeline import RecommendationPipeline
    from app.recommendation.recommendation_engine import RecommendationEngine
    from app.recommendation.evidence_enrichment import RecommendationEvidenceEnricher
    from app.decisions.decision_engine import DecisionEngine
    from app.provenance.evidence_registration import EvidenceRegistrationService
    from app.provenance.provenance_ledger import ProvenanceLedgerBuilder

    context = ChallengeContextLoader().load(inventory.challenge_context_path)
    requirements = ChallengeContextLoader().load_requirements(
        inventory.challenge_context_path
    )
    profiles = {
        submission_id: SubmissionProfiler().profile(
            submission_id,
            inventory.root_path / "submissions" / submission_id,
        )
        for submission_id in inventory.submission_ids
    }
    matrix = RequirementMatrixBuilder(
        challenge_id=inventory.challenge_id,
        challenge_root=inventory.root_path,
    ).build(
        requirements=requirements,
        submission_ids=inventory.submission_ids,
    )
    recommendation_result = result or RecommendationPipeline(
        recommendation_engine=RecommendationEngine(),
        decision_engine=DecisionEngine(),
        evidence_registration_service=EvidenceRegistrationService(),
        evidence_enricher=RecommendationEvidenceEnricher(),
    ).run(
        challenge_id=inventory.challenge_id,
        matrix=matrix,
        profiles=profiles,
        ledger_builder=ProvenanceLedgerBuilder(
            challenge_id=inventory.challenge_id
        ),
    )
    plan = None
    execution = None
    if not any(item.state in {"pending", "manual_review", "unresolved", "blocked"}
               for item in decisions.decisions):
        from app.code_mode.pipeline import CodeModePipeline
        from app.code_mode.base_selector import BaseSubmissionSelector
        from app.ingestion.verification_config import VerificationConfigLoader
        from app.code_mode.verification_runner import VerificationCommand

        base_selection = BaseSubmissionSelector().select(
            challenge_id=inventory.challenge_id,
            matrix=matrix,
            profiles=list(profiles.values()),
            recommendations=recommendation_result.recommendations,
        )
        if base_selection.selected_submission_id is None:
            WorkspaceWriter(Path("../workspace")).write_code(
                inventory=inventory,
                context=context,
                matrix=matrix,
                recommendations=recommendation_result.recommendations,
                decisions=decisions,
                provenance=recommendation_result.provenance,
                base_selection=base_selection,
            )
            return
        plan = CodeModePipeline().plan(
            challenge_id=inventory.challenge_id,
            matrix=matrix,
            profiles=profiles,
            recommendations=recommendation_result.recommendations,
            decisions=decisions,
            ledger=recommendation_result.provenance,
        )
        workspace_root = Path("../workspace").resolve()
        candidate_root = resolve_safe_path(
            workspace_root,
            f"{inventory.challenge_id}/.candidate",
        )
        expected_parent = workspace_root / inventory.challenge_id
        if candidate_root.parent != expected_parent:
            raise ValueError("Invalid candidate workspace path.")
        if candidate_root.exists():
            shutil.rmtree(candidate_root)
        source_root = (
            inventory.root_path
            / "submissions"
            / plan.base_selection.selected_submission_id
        ).resolve()
        if any(path.is_symlink() for path in source_root.rglob("*")):
            raise ValueError("Source submission contains a symlink.")
        shutil.copytree(source_root, candidate_root, symlinks=False)
        verification_config = VerificationConfigLoader().load_from_verification_path(
            inventory.verification_path
        )
        commands = [
            VerificationCommand(stage=name, command=command)
            for name, command in sorted(verification_config["commands"].items())
            if name in {"install", "build", "test", "smokeTest"}
        ]
        execution = CodeModePipeline().execute(
            challenge_id=inventory.challenge_id,
            plan=plan,
            submissions_root=inventory.root_path / "submissions",
            candidate_root=candidate_root,
            verification_commands=commands,
        )
        provenance = execution.provenance
    else:
        provenance = recommendation_result.provenance
    WorkspaceWriter(Path("../workspace")).write_code(
        inventory=inventory,
        context=context,
        matrix=matrix,
        recommendations=recommendation_result.recommendations,
        decisions=decisions,
        provenance=provenance,
        base_selection=plan.base_selection if plan else None,
        transplant_plan=plan.transplant_plan if plan else None,
        execution=execution,
    )


class DecisionUpdateRequest(BaseModel):
    action: str
    reason: str = ""
    alternativeSubmissionId: str | None = None
    reviewer: str | None = None


@router.post("/challenges/{challenge_id}/decisions/{requirement_id}")
def update_decision(
    challenge_id: str,
    requirement_id: str,
    request: DecisionUpdateRequest,
):
    persistence = DecisionPersistence(Path("../workspace").resolve())
    decisions = persistence.load(challenge_id)

    if decisions is None:
        raise HTTPException(
            status_code=404,
            detail=f"No decisions found for challenge: {challenge_id}",
        )

    from app.decisions.decision_engine import DecisionEngine

    engine = DecisionEngine()

    try:
        if request.action == "accept":
            updated = engine.accept(
                decisions,
                requirement_id,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        elif request.action == "reject":
            updated = engine.reject(
                decisions,
                requirement_id,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        elif request.action == "alternative_selected":
            if not request.alternativeSubmissionId:
                raise ValueError(
                    "alternativeSubmissionId is required."
                )
            updated = engine.select_alternative(
                decisions,
                requirement_id,
                request.alternativeSubmissionId,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        elif request.action == "blocked":
            updated = engine.block(
                decisions,
                requirement_id,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        elif request.action == "manual_review":
            updated = engine.manual_review(
                decisions,
                requirement_id,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        elif request.action == "unresolved":
            updated = engine.unresolved(
                decisions,
                requirement_id,
                reason=request.reason,
                reviewer=request.reviewer,
            )
        else:
            raise ValueError(
                f"Unsupported decision action: {request.action}"
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    persistence.save(updated)
    inventories = StarterPackScanner(Path("../starter-pack").resolve()).scan()
    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )
    if inventory is not None:
        if inventory.mode == "ideation":
            # Rebuild dependent artifacts from the saved decision state.
            from app.ideation.pipeline import IdeationPipeline
            from app.ideation.synthesis import IdeationSynthesizer
            from app.ideation.verification import IdeationVerifier
            from app.ideation.provenance import IdeationProvenanceBuilder

            result = IdeationPipeline().plan(
                challenge_id=challenge_id,
                submissions_root=inventory.root_path / "submissions",
                submission_ids=inventory.submission_ids,
                persisted_decisions=updated,
            )
            result = result.__class__(
                challenge_id=result.challenge_id,
                ideas=result.ideas,
                evaluation=result.evaluation,
                recommendations=result.recommendations,
                decisions=updated,
                synthesized_concept=IdeationSynthesizer().synthesize(
                    challenge_id=challenge_id,
                    ideas=result.ideas,
                    decisions=updated,
                ),
                verification=IdeationVerifier().verify(
                    ideas=result.ideas,
                    evaluation=result.evaluation,
                    decisions=updated,
                    synthesized_concept=IdeationSynthesizer().synthesize(
                        challenge_id=challenge_id,
                        ideas=result.ideas,
                        decisions=updated,
                    ),
                ),
                provenance=IdeationProvenanceBuilder().build(
                    challenge_id=challenge_id,
                    ideas=result.ideas,
                    evaluation=result.evaluation,
                    recommendations=result.recommendations,
                    decisions=updated,
                ),
            )
            WorkspaceWriter(Path("../workspace")).write_ideation(
                inventory=inventory,
                result=result,
                decisions=updated,
            )
        else:
            _write_code_workspace(inventory, updated)
    return updated.to_dict()


@router.get("/challenges/{challenge_id}/ideation-analysis")
def get_ideation_analysis(challenge_id: str):
    starter_pack = Path("../starter-pack").resolve()

    try:
        inventories = StarterPackScanner(starter_pack).scan()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan starter pack: {exc}",
        ) from exc

    inventory = next(
        (item for item in inventories if item.challenge_id == challenge_id),
        None,
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge not found: {challenge_id}",
        )

    if inventory.mode != "ideation":
        raise HTTPException(
            status_code=400,
            detail="Ideation analysis is only available for ideation challenges",
        )

    decision_persistence = DecisionPersistence(
        Path("../workspace").resolve()
    )
    saved_decisions = decision_persistence.load(challenge_id)

    from app.ideation.pipeline import IdeationPipeline

    result = IdeationPipeline().plan(
        challenge_id=challenge_id,
        submissions_root=inventory.root_path / "submissions",
        submission_ids=inventory.submission_ids,
        persisted_decisions=saved_decisions,
    )

    decisions = result.decisions

    decision_persistence.save(decisions)

    from app.ideation.synthesis import IdeationSynthesizer
    from app.ideation.verification import IdeationVerifier
    from app.ideation.provenance import IdeationProvenanceBuilder

    result = result.__class__(
        challenge_id=result.challenge_id,
        ideas=result.ideas,
        evaluation=result.evaluation,
        recommendations=result.recommendations,
        decisions=decisions,
        synthesized_concept=IdeationSynthesizer().synthesize(
            challenge_id=challenge_id,
            ideas=result.ideas,
            decisions=decisions,
        ),
        verification=IdeationVerifier().verify(
            ideas=result.ideas,
            evaluation=result.evaluation,
            decisions=decisions,
            synthesized_concept=IdeationSynthesizer().synthesize(
                challenge_id=challenge_id,
                ideas=result.ideas,
                decisions=decisions,
            ),
        ),
        provenance=IdeationProvenanceBuilder().build(
            challenge_id=challenge_id,
            ideas=result.ideas,
            evaluation=result.evaluation,
            recommendations=result.recommendations,
            decisions=decisions,
        ),
    )

    WorkspaceWriter(Path("../workspace")).write_ideation(
        inventory=inventory,
        result=result,
        decisions=decisions,
    )

    return {
        "challengeId": challenge_id,
        "ideas": [idea.to_dict() for idea in result.ideas],
        "evaluation": result.evaluation.to_dict(),
        "recommendations": result.recommendations.to_dict(),
        "decisions": decision_persistence.load(challenge_id).to_dict(),
        "verification": result.verification.to_dict(),
        "synthesizedConcept": result.synthesized_concept.to_dict(),
        "provenance": result.provenance.to_dict(),
    }
