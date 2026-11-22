from __future__ import annotations

from dataclasses import dataclass, field

from app.decisions.models import DecisionSet
from app.ideation.idea_models import IdeaComponent


@dataclass(frozen=True)
class SynthesizedConcept:
    challenge_id: str
    title: str
    problem: str
    proposed_agents: list[str] = field(default_factory=list)
    sdlc_phases: list[str] = field(default_factory=list)
    users: list[str] = field(default_factory=list)
    beneficiaries: list[str] = field(default_factory=list)
    workflow: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    human_oversight: list[str] = field(default_factory=list)
    security: list[str] = field(default_factory=list)
    feasibility: str = ""
    scalability: str = ""
    impact: str = ""
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    differentiators: list[str] = field(default_factory=list)
    source_idea_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    synthesis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "title": self.title,
            "problem": self.problem,
            "proposedAgents": self.proposed_agents,
            "sdlcPhases": self.sdlc_phases,
            "users": self.users,
            "beneficiaries": self.beneficiaries,
            "workflow": self.workflow,
            "data": self.data,
            "integrations": self.integrations,
            "humanOversight": self.human_oversight,
            "security": self.security,
            "feasibility": self.feasibility,
            "scalability": self.scalability,
            "impact": self.impact,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "differentiators": self.differentiators,
            "sourceIdeaIds": self.source_idea_ids,
            "evidenceRefs": self.evidence_refs,
            "synthesisNotes": self.synthesis_notes,
        }


class IdeationSynthesizer:
    """Build one coherent concept from Copilot-approved idea components."""

    def synthesize(
        self,
        challenge_id: str,
        ideas: list[IdeaComponent],
        decisions: DecisionSet,
    ) -> SynthesizedConcept:
        selected_submission_ids: set[str] = set()
        pending_criteria: list[str] = []
        rejected_criteria: list[str] = []

        for decision in decisions.decisions:
            if decision.state == "accepted" and decision.selected_submission_id:
                selected_submission_ids.add(decision.selected_submission_id)
            elif (
                decision.state == "alternative_selected"
                and decision.alternative_submission_id
            ):
                selected_submission_ids.add(decision.alternative_submission_id)
            elif decision.state in {"pending", "unresolved", "manual_review"}:
                pending_criteria.append(decision.requirement_id)
            elif decision.state in {"rejected", "blocked"}:
                rejected_criteria.append(decision.requirement_id)

        # Do not synthesize from unresolved ideas. A pending Copilot decision
        # means the corresponding source has not yet been approved.
        selected = [
            idea
            for idea in ideas
            if idea.submission_id in selected_submission_ids
        ]

        def merge(field: str) -> list[str]:
            values: list[str] = []
            for idea in selected:
                for value in getattr(idea, field):
                    if value and value not in values:
                        values.append(value)
            return values

        problems = [idea.problem for idea in selected if idea.problem]

        notes = [
            "Synthesis combines only Copilot-approved source components.",
            "Pending, unresolved, manual-review, rejected, and blocked decisions are excluded.",
            "Fields without supporting source evidence are not invented.",
            "Source submissions remain unchanged.",
        ]

        if pending_criteria:
            notes.append(
                "Synthesis is incomplete because decisions remain pending: "
                + ", ".join(pending_criteria)
                + "."
            )

        if rejected_criteria:
            notes.append(
                "Rejected or blocked criteria were excluded: "
                + ", ".join(rejected_criteria)
                + "."
            )

        if not selected:
            notes.append(
                "No source components are currently approved; generate a concept "
                "after Copilot resolves the required decisions."
            )

        return SynthesizedConcept(
            challenge_id=challenge_id,
            title="Unified Agentic SDLC Community Enablement Platform",
            problem=(
                " ".join(dict.fromkeys(problems))
                if problems
                else "Enable the Topcoder community with agentic AI across SDLC workflows."
            ),
            proposed_agents=merge("proposed_agents"),
            sdlc_phases=merge("sdlc_phases"),
            users=merge("users"),
            beneficiaries=merge("beneficiaries"),
            workflow=merge("workflow"),
            data=merge("data"),
            integrations=merge("integrations"),
            human_oversight=merge("human_oversight"),
            security=merge("security"),
            feasibility=(
                "Synthesized from selected source evidence."
                if selected
                else ""
            ),
            scalability=(
                "Synthesized from selected source evidence."
                if selected
                else ""
            ),
            impact=(
                "Synthesized from selected source evidence."
                if selected
                else ""
            ),
            risks=merge("risks"),
            assumptions=merge("assumptions"),
            differentiators=merge("differentiators"),
            source_idea_ids=[idea.idea_id for idea in selected],
            evidence_refs=list(
                dict.fromkeys(
                    evidence_ref
                    for idea in selected
                    for evidence_ref in idea.evidence_refs
                )
            ),
            synthesis_notes=notes,
        )
