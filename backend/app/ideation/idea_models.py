from dataclasses import dataclass, field
from typing import Literal


IdeaAssessment = Literal[
    "complete",
    "partial",
    "missing",
    "not_verifiable",
    "manual_review_required",
]


@dataclass(frozen=True)
class IdeaEvidence:
    evidence_id: str
    submission_id: str
    source_path: str

    page: int | None = None
    slide: int | None = None
    section: str | None = None
    content_block: str | None = None

    description: str = ""


@dataclass(frozen=True)
class IdeaComponent:
    idea_id: str
    submission_id: str
    title: str

    problem: str = ""
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

    assessment: IdeaAssessment = "not_verifiable"

    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ideaId": self.idea_id,
            "submissionId": self.submission_id,
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
            "assessment": self.assessment,
            "evidenceRefs": self.evidence_refs,
        }
