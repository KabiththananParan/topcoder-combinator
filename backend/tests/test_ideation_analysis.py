from pathlib import Path

from app.ideation.extractor import DocumentExtractor
from app.ideation.idea_analyzer import IdeationAnalyzer
from app.ideation.idea_models import IdeaComponent
from app.ideation.submission_profiler import IdeationSubmissionProfiler


FIXTURE_ROOT = Path(
    "../starter-pack/challenges/"
    "AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC/submissions"
)


def test_ideation_analysis_fixture_profiles_have_extractable_content():
    profiler = IdeationSubmissionProfiler()
    profiles = profiler.profile(
        "SUB_001",
        FIXTURE_ROOT / "SUB_001",
    )

    assert len(profiles) == 3
    assert all(profile.blocks for profile in profiles)

    combined_text = "\n".join(
        block.text
        for profile in profiles
        for block in profile.blocks
    )

    assert "MCP" in combined_text
    assert "Topcoder" in combined_text
    assert "agent" in combined_text.lower()


def test_ideation_analyzer_produces_idea_components_with_evidence():
    profiler = IdeationSubmissionProfiler()
    profiles = profiler.profile(
        "SUB_001",
        FIXTURE_ROOT / "SUB_001",
    )

    candidates = IdeationAnalyzer().analyze("SUB_001", profiles)

    assert len(candidates) == 3

    components = [
        IdeaComponent(
            idea_id=candidate.idea_id,
            submission_id=candidate.submission_id,
            title=candidate.title,
            evidence_refs=candidate.evidence_block_ids,
        )
        for candidate in candidates
    ]

    assert all(isinstance(component, IdeaComponent) for component in components)
    assert all(component.evidence_refs for component in components)
    assert components[0].title.startswith("Idea1:")
    assert components[1].title.startswith("Idea2:")
    assert components[2].title.startswith("Idea3:")

    assert candidates[0].problem
    assert candidates[0].proposed_agents
    assert any(
        "challenge analysis" in agent.lower()
        for agent in candidates[0].proposed_agents
    )


def test_ideation_pipeline_creates_shared_pending_decisions():
    from app.ideation.pipeline import IdeationPipeline
    from app.ideation.synthesis import IdeationSynthesizer
    from app.ideation.verification import IdeationVerifier

    pipeline = IdeationPipeline()

    result = pipeline.plan(
        challenge_id="AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC",
        submissions_root=FIXTURE_ROOT,
        submission_ids=["SUB_001", "SUB_002", "SUB_003"],
    )

    assert len(result.decisions.decisions) == 5

    decision_ids = {
        decision.requirement_id
        for decision in result.decisions.decisions
    }

    assert decision_ids == {
        "Originality",
        "Feasibility",
        "Scalability",
        "Impact Potential",
        "Alignment with Scope",
    }

    assert all(
        decision.state == "pending"
        for decision in result.decisions.decisions
    )

    assert all(
        decision.recommendation_score is not None
        for decision in result.decisions.decisions
    )

    assert all(
        decision.evidence_refs
        for decision in result.decisions.decisions
    )


def test_ideation_decision_engine_accepts_recommendation():
    from app.decisions.decision_engine import DecisionEngine
    from app.ideation.pipeline import IdeationPipeline

    pipeline = IdeationPipeline()

    result = pipeline.plan(
        challenge_id="AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC",
        submissions_root=FIXTURE_ROOT,
        submission_ids=["SUB_001", "SUB_002", "SUB_003"],
    )

    engine = DecisionEngine()

    updated = engine.accept(
        result.decisions,
        "Originality",
        reason="Copilot approved the recommended idea after reviewing the evidence.",
        reviewer="copilot",
    )

    decision = updated.for_requirement("Originality")

    assert decision is not None
    assert decision.state == "accepted"
    assert decision.selected_submission_id == decision.recommended_submission_id
    assert decision.evidence_refs

def test_ideation_pipeline_synthesizes_approved_ideas_and_verifies_provenance():
    from app.decisions.decision_engine import DecisionEngine
    from app.ideation.pipeline import IdeationPipeline
    from app.ideation.synthesis import IdeationSynthesizer
    from app.ideation.verification import IdeationVerifier

    pipeline = IdeationPipeline()

    result = pipeline.plan(
        challenge_id="AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC",
        submissions_root=FIXTURE_ROOT,
        submission_ids=["SUB_001", "SUB_002", "SUB_003"],
    )

    engine = DecisionEngine()

    updated_decisions = result.decisions

    for requirement_id in [
        "Originality",
        "Feasibility",
        "Scalability",
        "Impact Potential",
        "Alignment with Scope",
    ]:
        decision = updated_decisions.for_requirement(requirement_id)

        if decision is not None and decision.recommended_submission_id:
            updated_decisions = engine.accept(
                updated_decisions,
                requirement_id,
                reason="Copilot approved the recommended source after reviewing the evidence.",
                reviewer="copilot",
            )

    synthesized = IdeationSynthesizer().synthesize(
        challenge_id="AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC",
        ideas=result.ideas,
        decisions=updated_decisions,
    )

    verification = IdeationVerifier().verify(
        ideas=result.ideas,
        evaluation=result.evaluation,
        decisions=updated_decisions,
        synthesized_concept=synthesized,
    )

    assert synthesized.challenge_id == "AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC"
    assert synthesized.source_idea_ids
    assert synthesized.evidence_refs
    assert synthesized.proposed_agents
    assert synthesized.workflow
    assert synthesized.integrations

    assert verification.status == "passed"
    assert verification.checks["synthesis_is_consistent"]
    assert verification.checks["synthesis_sources_are_known"]
    assert verification.checks["synthesis_evidence_present"]

    event_types = [
        event.event_type
        for event in result.provenance.events
    ]

    assert "assessment_created" in event_types
    assert "recommendation_created" in event_types
    assert "decision_created" in event_types
    assert "source_selected" in event_types
