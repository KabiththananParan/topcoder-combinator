from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.ingestion.starter_pack_scanner import StarterPackScanner

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

    return {
        "challengeId": challenge_id,
        "decisions": result.decisions.decisions,
    }
