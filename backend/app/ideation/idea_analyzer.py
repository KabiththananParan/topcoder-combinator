import re
from dataclasses import dataclass

from .models import DocumentProfile
from .evidence import DocumentEvidenceRef


@dataclass(frozen=True)
class IdeaCandidate:
    idea_id: str
    submission_id: str
    title: str
    problem: str
    proposed_agents: list[str]
    sdlc_phases: list[str]
    users: list[str]
    beneficiaries: list[str]
    workflow: list[str]
    data: list[str]
    integrations: list[str]
    human_oversight: list[str]
    security: list[str]
    feasibility: str
    scalability: str
    impact: str
    risks: list[str]
    assumptions: list[str]
    differentiators: list[str]
    evidence_block_ids: list[str]


class IdeationAnalyzer:
    def analyze(
        self,
        submission_id: str,
        profiles: list[DocumentProfile],
    ) -> list[IdeaCandidate]:
        candidates: list[IdeaCandidate] = []

        for index, profile in enumerate(profiles, start=1):
            non_empty_blocks = [
                block for block in profile.blocks
                if block.text.strip()
            ]

            if not non_empty_blocks:
                continue

            title = self._extract_title(
                non_empty_blocks[0].text,
                profile.source_path.stem,
            )

            candidates.append(
                IdeaCandidate(
                    idea_id=f"{submission_id}-IDEA-{index:03d}",
                    submission_id=submission_id,
                    title=title,
                    problem=self._extract_problem(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    proposed_agents=self._extract_proposed_agents(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    sdlc_phases=self._extract_sdlc_phases(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    users=self._extract_users(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    beneficiaries=self._extract_beneficiaries(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    workflow=self._extract_workflow(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    data=self._extract_data(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    integrations=self._extract_integrations(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    human_oversight=self._extract_human_oversight(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    security=self._extract_security(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    feasibility=self._extract_feasibility(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    scalability=self._extract_scalability(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    impact=self._extract_impact(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    risks=self._extract_risks(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    assumptions=self._extract_assumptions(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    differentiators=self._extract_differentiators(
                        '\n'.join(block.text for block in non_empty_blocks)
                    ),
                    evidence_block_ids=[
                        block.block_id for block in non_empty_blocks
                    ],
                )
            )

        return candidates

    @staticmethod
    def to_evidence_refs(
        candidate: IdeaCandidate,
        profiles: list[DocumentProfile],
    ) -> list[DocumentEvidenceRef]:
        refs: list[DocumentEvidenceRef] = []

        for profile in profiles:
            for block in profile.blocks:
                if block.block_id not in candidate.evidence_block_ids:
                    continue

                refs.append(
                    DocumentEvidenceRef(
                        evidence_id=f"{candidate.submission_id}:{profile.source_path.name}:{block.block_id}",
                        submission_id=candidate.submission_id,
                        source_path=str(profile.source_path),
                        page=block.location.page,
                        slide=block.location.slide,
                        section=block.location.section,
                        content_block=block.location.content_block,
                        description=block.text[:200].strip(),
                    )
                )

        return refs

    @staticmethod
    def to_component(
        candidate: IdeaCandidate,
        evidence_refs: list[DocumentEvidenceRef] | None = None,
    ):
        from .idea_models import IdeaComponent

        evidence_refs = evidence_refs or []

        return IdeaComponent(
            idea_id=candidate.idea_id,
            submission_id=candidate.submission_id,
            title=candidate.title,
            problem=candidate.problem,
            proposed_agents=candidate.proposed_agents,
            sdlc_phases=candidate.sdlc_phases,
            users=candidate.users,
            beneficiaries=candidate.beneficiaries,
            workflow=candidate.workflow,
            data=candidate.data,
            integrations=candidate.integrations,
            human_oversight=candidate.human_oversight,
            security=candidate.security,
            feasibility=candidate.feasibility,
            scalability=candidate.scalability,
            impact=candidate.impact,
            risks=candidate.risks,
            assumptions=candidate.assumptions,
            differentiators=candidate.differentiators,
            assessment="complete" if candidate.evidence_block_ids else "not_verifiable",
            evidence_refs=[
                ref.evidence_id for ref in evidence_refs
            ],
        )

    @staticmethod
    def _extract_title(text: str, fallback: str) -> str:
        match = re.search(
            r"(Idea\d+:.*?)(?=\nOverview\b)",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return " ".join(match.group(1).split())

        return fallback

    @staticmethod
    def _evidence_sentences(text: str, terms: list[str]) -> list[str]:
        normalized_text = re.sub(r"[ \\t]+", " ", text)
        sentences = re.split(
            r"(?<=[.!?])\s+|(?<=[.!?])(?=[A-Z][a-z])|\n+",
            normalized_text,
        )
        matches: list[str] = []

        for sentence in sentences:
            lowered = sentence.lower()
            if any(term.lower() in lowered for term in terms):
                if sentence not in matches:
                    matches.append(sentence)

        return matches

    @staticmethod
    def _extract_problem(text: str) -> str:
        if "Overview" not in text:
            return ""

        overview = text.split("Overview", 1)[1]

        if "The Model Context Protocol" in overview:
            overview = overview.split("The Model Context Protocol", 1)[0]

        return " ".join(overview.split())

    @staticmethod
    def _extract_proposed_agents(text: str) -> list[str]:
        agents: list[str] = []

        normalized_text = " ".join(text.split())

        if "complete forms" in normalized_text:
            agents.append(
                "Agent for completing forms and retrieving database data"
            )

        if "challenge data" in normalized_text and "Intent Recognition and Decomposition" in normalized_text:
            agents.append(
                "Agent for natural-language challenge analysis and data retrieval"
            )

        if (
            "challenge data" in normalized_text
            and (
                "natural language challenge analysis" in normalized_text.lower()
                or "natural-language challenge analysis" in normalized_text.lower()
            )
            and "Agent for natural-language challenge analysis and data retrieval" not in agents
        ):
            agents.append(
                "Agent for natural-language challenge analysis and data retrieval"
            )

        if (
            "review feedback" in normalized_text
            and "java" in normalized_text
        ):
            agents.append(
                "Agent for analyzing Java submissions using Topcoder review feedback"
            )

        if "multi-agent" in normalized_text or "multi agent" in normalized_text:
            agents.append("Multi-agent workflow")

        if "code review" in normalized_text or "code reviewer" in normalized_text:
            agents.append("AI-powered code review agent")

        return agents

    @staticmethod
    def _extract_sdlc_phases(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        phases: list[str] = []

        phase_terms = [
            "requirements gathering",
            "requirement gathering",
            "code reviews",
            "code review",
            "submitting solutions",
            "project workflows",
            "challenge creation",
            "challenge posting",
            "submission evaluation",
        ]

        for phase in phase_terms:
            if phase.lower() in normalized_text.lower():
                phases.append(phase)

        return phases

    @staticmethod
    def _extract_users(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        users: list[str] = []

        user_terms = [
            "developers",
            "development teams",
            "project managers",
            "customers",
            "community members",
        ]

        for user in user_terms:
            if user.lower() in normalized_text.lower():
                users.append(user)

        return users

    @staticmethod
    def _extract_beneficiaries(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        beneficiaries: list[str] = []

        beneficiary_terms = [
            "developers",
            "development teams",
            "project managers",
            "customers",
            "community members",
            "Topcoder community",
        ]

        for beneficiary in beneficiary_terms:
            if beneficiary.lower() in normalized_text.lower():
                beneficiaries.append(beneficiary)

        return beneficiaries

    @staticmethod
    def _extract_workflow(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        workflow: list[str] = []

        workflow_terms = [
            "natural language challenge analysis",
            "retrieve data",
            "retrieve challenge data",
            "analyzing Java submissions",
            "review feedback",
            "submit solutions",
            "tool discovery",
            "challenge specification",
            "post the challenge",
            "evaluate submissions",
            "scorecard",
            "human review",
            "code review",
        ]

        for step in workflow_terms:
            if step.lower() in normalized_text.lower():
                workflow.append(step)

        return workflow

    @staticmethod
    def _extract_data(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        data: list[str] = []

        data_terms = [
            "challenge data",
            "challenge details",
            "challenge listings",
            "submission data",
            "review feedback",
            "customer data",
            "project workflows",
        ]

        for item in data_terms:
            if item.lower() in normalized_text.lower():
                data.append(item)

        return data

    @staticmethod
    def _extract_integrations(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        integrations: list[str] = []

        if "model context protocol" in normalized_text.lower() or "mcp" in normalized_text.lower():
            integrations.append("Model Context Protocol (MCP)")

        integration_terms = [
            "Topcoder API",
            "Topcoder APIs",
            "external tools",
            "MCP servers",
            "OpenAI",
            "AWS Bedrock",
            "vector embeddings",
            "RAG",
            "function calling",
        ]

        for integration in integration_terms:
            if integration.lower() in normalized_text.lower():
                evidence = IdeationAnalyzer._evidence_sentences(
                    text,
                    [integration],
                )
                if evidence:
                    integrations.append(
                        f"{integration}: {evidence[0][:180]}"
                    )

        return integrations

    @staticmethod
    def _extract_human_oversight(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        oversight: list[str] = []

        oversight_terms = [
            "human oversight",
            "human in the loop",
            "human review",
            "review feedback",
            "approval",
            "manually reviewed",
            "manually review",
            "human reviewers",
            "ability to adjust",
        ]

        for term in oversight_terms:
            if term.lower() in normalized_text.lower():
                oversight.append(term)

        return oversight

    @staticmethod
    def _extract_security(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        security: list[str] = []

        security_terms = [
            "security",
            "token authentication",
            "RBAC",
            "HTTPS",
            "audit",
            "rate limiting",
            "IP whitelisting",
        ]

        for term in security_terms:
            if term.lower() in normalized_text.lower():
                security.append(term)

        return security

    @staticmethod
    def _extract_feasibility(text: str) -> str:
        normalized_text = " ".join(text.split())

        evidence_terms = [
            "proof of concept",
            "POC",
            "technology",
            "framework",
            "prototype",
            "RAG",
            "function calling",
            "tool calling",
            "multi-agent",
        ]

        matches = [
            term
            for term in evidence_terms
            if term.lower() in normalized_text.lower()
        ]

        if matches:
            return "Evidence mentions: " + ", ".join(matches)

        return ""

    @staticmethod
    def _extract_scalability(text: str) -> str:
        normalized_text = " ".join(text.split())

        evidence_terms = [
            "scalable",
            "scalability",
            "deploy new agents",
            "community sharing",
            "modular",
            "modular design",
            "separates concerns",
            "real time",
        ]

        matches = [
            term
            for term in evidence_terms
            if term.lower() in normalized_text.lower()
        ]

        if matches:
            return "Evidence mentions: " + ", ".join(matches)

        return ""

    @staticmethod
    def _extract_impact(text: str) -> str:
        normalized_text = " ".join(text.split())

        evidence_terms = [
            "improve",
            "enable",
            "assist",
            "automate",
            "community",
        ]

        matches = [
            term
            for term in evidence_terms
            if term.lower() in normalized_text.lower()
        ]

        if matches:
            return "Evidence mentions: " + ", ".join(matches)

        return ""

    @staticmethod
    def _extract_risks(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        risks: list[str] = []

        risk_terms = [
            "security risk",
            "privacy risk",
            "authentication risk",
            "authorization risk",
            "scalability risk",
            "integration risk",
            "dependency risk",
            "performance risk",
        ]

        for term in risk_terms:
            if term.lower() in normalized_text.lower():
                risks.append(term)

        return risks

    @staticmethod
    def _extract_assumptions(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        assumptions: list[str] = []

        assumption_terms = [
            "requires",
            "depends on",
            "must support",
            "needs access to",
            "requires access to",
        ]

        for term in assumption_terms:
            if term.lower() in normalized_text.lower():
                assumptions.append(term)

        return assumptions

    @staticmethod
    def _extract_differentiators(text: str) -> list[str]:
        normalized_text = " ".join(text.split())
        differentiators: list[str] = []

        differentiator_terms = [
            "Model Context Protocol",
            "custom agents",
            "community sharing",
            "vendor/provider compatibility",
            "multi-agent approach",
            "Retrieval-Augmented Generation",
            "prompt engineering",
            "tool calling",
            "self-service challenges",
        ]

        for term in differentiator_terms:
            if term.lower() in normalized_text.lower():
                differentiators.append(term)

        return differentiators
