from dataclasses import dataclass, field
from typing import Literal

from app.decisions.models import Decision, DecisionSet
from app.matrix.models import RequirementMatrix
from app.profiling.models import SubmissionProfile
from app.provenance.models import ProvenanceLedger

from .models import FileTransplant


TransplantAction = Literal[
    "transplant",
    "keep_base",
    "blocked",
    "manual_review",
]


@dataclass(frozen=True)
class TransplantItem:
    requirement_id: str
    requirement_title: str
    source_submission_id: str | None
    target_submission_id: str
    action: TransplantAction
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    file_transplants: list[FileTransplant] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requirementId": self.requirement_id,
            "requirementTitle": self.requirement_title,
            "sourceSubmissionId": self.source_submission_id,
            "targetSubmissionId": self.target_submission_id,
            "action": self.action,
            "reason": self.reason,
            "evidenceRefs": list(self.evidence_refs),
            "fileTransplants": [
                transplant.to_dict()
                for transplant in self.file_transplants
            ],
        }


@dataclass(frozen=True)
class TransplantPlan:
    challenge_id: str
    base_submission_id: str
    items: list[TransplantItem] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def transplant_items(self) -> list[TransplantItem]:
        return [
            item
            for item in self.items
            if item.action == "transplant"
        ]

    def to_dict(self) -> dict:
        return {
            "challengeId": self.challenge_id,
            "baseSubmissionId": self.base_submission_id,
            "items": [
                item.to_dict()
                for item in self.items
            ],
            "risks": list(self.risks),
        }


class TransplantPlanBuilder:
    """
    Converts approved Copilot decisions into an explicit Code Mode plan.

    This class does not modify files.

    File mappings are derived only from:
    - evidence attached to the selected requirement/submission
    - files that actually exist in the selected submission profile
    """

    def build(
        self,
        challenge_id: str,
        base_submission_id: str,
        decisions: DecisionSet,
        submission_ids: list[str],
        matrix: RequirementMatrix | None = None,
        profiles: dict[str, SubmissionProfile] | None = None,
        provenance: ProvenanceLedger | None = None,
    ) -> TransplantPlan:

        valid_submission_ids = set(submission_ids)

        if base_submission_id not in valid_submission_ids:
            raise ValueError(
                f"Base submission does not belong to challenge: "
                f"{base_submission_id}"
            )

        items: list[TransplantItem] = []
        risks: list[str] = []

        for decision in decisions.decisions:
            item = self._build_item(
                decision=decision,
                base_submission_id=base_submission_id,
                valid_submission_ids=valid_submission_ids,
                matrix=matrix,
                profiles=profiles,
                provenance=provenance,
            )

            items.append(item)

            if item.action in {"blocked", "manual_review"}:
                risks.append(
                    f"{item.action}:{item.requirement_id}"
                )

            if (
                item.action == "transplant"
                and not item.file_transplants
            ):
                risks.append(
                    f"no_file_mapping:{item.requirement_id}"
                )

        return TransplantPlan(
            challenge_id=challenge_id,
            base_submission_id=base_submission_id,
            items=items,
            risks=risks,
        )

    def _build_item(
        self,
        decision: Decision,
        base_submission_id: str,
        valid_submission_ids: set[str],
        matrix: RequirementMatrix,
        profiles: dict[str, SubmissionProfile],
        provenance: ProvenanceLedger | None,
    ) -> TransplantItem:

        evidence_refs = list(decision.evidence_refs)

        if decision.state == "accepted":
            selected = decision.selected_submission_id

            if selected is None:
                return TransplantItem(
                    requirement_id=decision.requirement_id,
                    requirement_title=decision.requirement_title,
                    source_submission_id=None,
                    target_submission_id=base_submission_id,
                    action="manual_review",
                    reason=(
                        "Accepted decision has no selected submission."
                    ),
                    evidence_refs=evidence_refs,
                )

            self._validate_submission(
                selected,
                valid_submission_ids,
            )

            if selected == base_submission_id:
                return TransplantItem(
                    requirement_id=decision.requirement_id,
                    requirement_title=decision.requirement_title,
                    source_submission_id=base_submission_id,
                    target_submission_id=base_submission_id,
                    action="keep_base",
                    reason=(
                        "Approved source is already the selected base."
                    ),
                    evidence_refs=evidence_refs,
                )

            file_transplants = []

            if matrix is not None and profiles is not None:
                file_transplants = self._build_file_transplants(
                    decision.requirement_id,
                    selected,
                    matrix,
                    profiles,
                )

            return TransplantItem(
                requirement_id=decision.requirement_id,
                requirement_title=decision.requirement_title,
                source_submission_id=selected,
                target_submission_id=base_submission_id,
                action="transplant",
                reason=(
                    "Approved decision selects a different submission "
                    "for this requirement."
                ),
                evidence_refs=evidence_refs,
                file_transplants=file_transplants,
            )

        if decision.state in {"rejected", "blocked"}:
            return TransplantItem(
                requirement_id=decision.requirement_id,
                requirement_title=decision.requirement_title,
                source_submission_id=None,
                target_submission_id=base_submission_id,
                action="blocked",
                reason=(
                    f"Decision state '{decision.state}' does not permit "
                    "automatic transplantation."
                ),
                evidence_refs=evidence_refs,
            )

        if decision.state in {
            "manual_review",
            "unresolved",
            "pending",
        }:
            return TransplantItem(
                requirement_id=decision.requirement_id,
                requirement_title=decision.requirement_title,
                source_submission_id=None,
                target_submission_id=base_submission_id,
                action="manual_review",
                reason=(
                    f"Decision state '{decision.state}' requires "
                    "human resolution before transplantation."
                ),
                evidence_refs=evidence_refs,
            )

        if decision.state == "alternative_selected":
            selected = decision.alternative_submission_id

            if selected is None:
                return TransplantItem(
                    requirement_id=decision.requirement_id,
                    requirement_title=decision.requirement_title,
                    source_submission_id=None,
                    target_submission_id=base_submission_id,
                    action="manual_review",
                    reason=(
                        "Alternative-selected decision has no "
                        "alternative submission."
                    ),
                    evidence_refs=evidence_refs,
                )

            self._validate_submission(
                selected,
                valid_submission_ids,
            )

            if selected == base_submission_id:
                return TransplantItem(
                    requirement_id=decision.requirement_id,
                    requirement_title=decision.requirement_title,
                    source_submission_id=base_submission_id,
                    target_submission_id=base_submission_id,
                    action="keep_base",
                    reason=(
                        "Approved alternative is already the selected base."
                    ),
                    evidence_refs=evidence_refs,
                )

            file_transplants = []

            if matrix is not None and profiles is not None:
                file_transplants = self._build_file_transplants(
                    decision.requirement_id,
                    selected,
                    matrix,
                    profiles,
                )

            return TransplantItem(
                requirement_id=decision.requirement_id,
                requirement_title=decision.requirement_title,
                source_submission_id=selected,
                target_submission_id=base_submission_id,
                action="transplant",
                reason=(
                    "Approved alternative submission will be used "
                    "for this requirement."
                ),
                evidence_refs=evidence_refs,
                file_transplants=file_transplants,
            )

        raise ValueError(
            f"Unsupported decision state: {decision.state}"
        )

    @staticmethod
    def _build_file_transplants(
        requirement_id: str,
        source_submission_id: str,
        matrix: RequirementMatrix,
        profiles: dict[str, SubmissionProfile],
    ) -> list[FileTransplant]:

        if source_submission_id not in profiles:
            raise ValueError(
                f"Profile does not exist for submission: "
                f"{source_submission_id}"
            )

        source_profile = profiles[source_submission_id]

        entries = matrix.for_requirement(
            requirement_id
        )

        evidence_paths: list[str] = []

        for entry in entries:
            if entry.submission_id != source_submission_id:
                continue

            for evidence in entry.assessment.evidence:
                path = evidence.get("path")

                if (
                    isinstance(path, str)
                    and path
                    and path not in evidence_paths
                ):
                    evidence_paths.append(path)

        available_files = set(
            source_profile.repository_structure.source_files
            + source_profile.repository_structure.test_files
        )

        file_transplants: list[FileTransplant] = []

        for path in evidence_paths:
            if path not in available_files:
                continue

            file_transplants.append(
                FileTransplant(
                    source_path=path,
                    target_path=path,
                    reason=(
                        f"Evidence for requirement "
                        f"{requirement_id} identifies "
                        f"'{path}' in the selected submission."
                    ),
                )
            )

        return file_transplants

    @staticmethod
    def _validate_submission(
        submission_id: str,
        valid_submission_ids: set[str],
    ) -> None:

        if submission_id not in valid_submission_ids:
            raise ValueError(
                f"Submission does not belong to challenge: "
                f"{submission_id}"
            )