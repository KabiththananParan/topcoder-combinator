from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.code_mode.safe_workspace import resolve_safe_path


class WorkspaceWriter:
    """Persist generated challenge analysis without modifying source artifacts."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def write_ideation(
        self,
        *,
        inventory: Any,
        result: Any,
        decisions: Any | None = None,
    ) -> Path:
        challenge_id = inventory.challenge_id
        challenge_root = (
            self.workspace_root / challenge_id
        ).resolve()

        if self.workspace_root not in challenge_root.parents:
            raise ValueError("Invalid challenge workspace path.")

        challenge_root.mkdir(parents=True, exist_ok=True)

        active_decisions = decisions or result.decisions
        review_context = self._review_context(inventory)
        context = self._load_json(inventory.challenge_context_path)
        review_status, active_context, reconciliation = (
            self._reconcile_review_context(
                inventory=inventory,
                context=context,
                supplied=review_context,
            )
        )
        source_map = self._ideation_source_map(result)
        contradictions = self._ideation_contradictions(
            result=result,
            decisions=active_decisions,
            reconciliation=reconciliation,
        )

        self._write_json(
            challenge_root / "workspace-manifest.json",
            {
                "challengeId": challenge_id,
                "mode": "ideation",
                "submissionIds": inventory.submission_ids,
                "sourceRoot": str(inventory.root_path),
                "generatedArtifacts": [
                    "review-context-status.json",
                    "active-review-context.json",
                    "review-context-reconciliation.json",
                    "source-location-map.json",
                    "overview.md",
                    "submissions/",
                    "ideas.json",
                    "evaluation.json",
                    "recommendations.json",
                    "decisions.json",
                    "synthesized-concept/concept.json",
                    "verification.json",
                    "provenance.json",
                    "contradictions.json",
                    "review-ui/",
                ],
            },
        )

        self._write_json(challenge_root / "review-context-status.json", review_status)
        self._write_json(challenge_root / "active-review-context.json", active_context)
        self._write_json(
            challenge_root / "review-context-reconciliation.json",
            reconciliation,
        )
        self._write_json(challenge_root / "source-location-map.json", source_map)

        self._write_json(
            challenge_root / "ideas.json",
            {"ideas": [item.to_dict() for item in result.ideas]},
        )

        self._write_json(
            challenge_root / "evaluation.json",
            result.evaluation.to_dict(),
        )

        self._write_json(
            challenge_root / "recommendations.json",
            result.recommendations.to_dict(),
        )

        self._write_json(
            challenge_root / "decisions.json",
            active_decisions.to_dict(),
        )

        self._write_json(
            challenge_root / "synthesized-concept" / "concept.json",
            result.synthesized_concept.to_dict(),
        )

        self._write_json(
            challenge_root / "verification.json",
            result.verification.to_dict(),
        )

        self._write_json(
            challenge_root / "provenance.json",
            result.provenance.to_dict(),
        )
        self._write_json(challenge_root / "contradictions.json", contradictions)
        self._write_text(
            challenge_root / "overview.md",
            self._ideation_overview(
                inventory=inventory,
                result=result,
                decisions=active_decisions,
                review_status=review_status,
                contradictions=contradictions,
            ),
        )
        self._copy_submissions(inventory.root_path / "submissions", challenge_root)
        (challenge_root / "review-ui").mkdir(parents=True, exist_ok=True)

        return challenge_root

    def write_code(
        self,
        *,
        inventory: Any,
        context: dict[str, Any],
        matrix: Any,
        recommendations: Any,
        decisions: Any,
        provenance: Any,
        base_selection: Any | None = None,
        transplant_plan: Any | None = None,
        execution: Any | None = None,
    ) -> Path:
        """Persist a code-mode analysis without ever writing to the starter pack."""
        challenge_root = self._challenge_root(inventory.challenge_id)
        challenge_root.mkdir(parents=True, exist_ok=True)
        supplied = self._review_context(inventory)
        review_status, active_context, reconciliation = (
            self._reconcile_review_context(
                inventory=inventory,
                context=context,
                supplied=supplied,
            )
        )
        self._write_json(
            challenge_root / "workspace-manifest.json",
            {
                "challengeId": inventory.challenge_id,
                "mode": "code",
                "submissionIds": sorted(inventory.submission_ids),
                "sourceRoot": str(inventory.root_path),
                "generatedArtifacts": [
                    "review-context-status.json",
                    "active-review-context.json",
                    "review-context-reconciliation.json",
                    "source-location-map.json",
                    "overview.md",
                    "submissions/",
                    "requirements.json",
                    "requirement-matrix.json",
                    "recommendations.json",
                    "decisions.json",
                    "base-selection.json",
                    "transplant-plan.json",
                    "candidate-status.json",
                    "verification.json",
                    "provenance.json",
                    "contradictions.json",
                    "combined-solution/",
                    "review-ui/",
                ],
            },
        )
        self._write_json(challenge_root / "review-context-status.json", review_status)
        self._write_json(challenge_root / "active-review-context.json", active_context)
        self._write_json(
            challenge_root / "review-context-reconciliation.json",
            reconciliation,
        )
        self._write_json(
            challenge_root / "requirements.json",
            {"requirements": context.get("requirements", [])},
        )
        self._write_json(challenge_root / "requirement-matrix.json", matrix.to_dict())
        self._write_json(
            challenge_root / "recommendations.json",
            recommendations.to_dict(),
        )
        self._write_json(challenge_root / "decisions.json", decisions.to_dict())
        self._write_json(
            challenge_root / "base-selection.json",
            base_selection.to_dict() if base_selection else {"status": "pending"},
        )
        self._write_json(
            challenge_root / "transplant-plan.json",
            transplant_plan.to_dict() if transplant_plan else {"status": "pending"},
        )
        self._write_json(
            challenge_root / "candidate-status.json",
            (
                {
                    "challengeId": execution.challenge_id,
                    "candidatePath": execution.execution.candidate_path,
                    "status": execution.execution.status,
                    "results": [
                        item.to_dict() for item in execution.execution.results
                    ],
                    "errors": list(execution.execution.errors),
                }
                if execution
                else {"status": "pending"}
            ),
        )
        verification = (
            {"status": "not_run", "reason": "Decisions are not fully resolved."}
            if execution is None
            else {
                "status": execution.execution.status,
                "results": [
                    item.to_dict() for item in execution.execution.results
                ],
                "errors": list(execution.execution.errors),
            }
        )
        self._write_json(challenge_root / "verification.json", verification)
        self._write_json(challenge_root / "provenance.json", provenance.to_dict())
        self._write_json(
            challenge_root / "source-location-map.json",
            self._code_source_map(inventory, context, matrix, recommendations),
        )
        self._write_json(
            challenge_root / "contradictions.json",
            self._code_contradictions(matrix, recommendations, decisions),
        )
        self._write_text(
            challenge_root / "overview.md",
            self._code_overview(
                inventory, context, decisions, review_status, verification
            ),
        )
        self._copy_submissions(inventory.root_path / "submissions", challenge_root)
        (challenge_root / "review-ui").mkdir(parents=True, exist_ok=True)
        if (
            execution is not None
            and execution.execution.status in {"success", "partial"}
        ):
            candidate = Path(execution.execution.candidate_path)
            combined = challenge_root / "combined-solution"
            if candidate.is_dir() and candidate.resolve() != combined.resolve():
                self._copy_tree(candidate, combined)
        return challenge_root

    def _challenge_root(self, challenge_id: str) -> Path:
        root = resolve_safe_path(self.workspace_root, challenge_id)
        if root.parent != self.workspace_root:
            raise ValueError("Invalid challenge workspace path.")
        return root

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to load JSON source: {path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object: {path}")
        return data

    @staticmethod
    def _review_context(inventory: Any) -> dict[str, Any] | None:
        path = inventory.review_context_path
        return WorkspaceWriter._load_json(path) if path else None

    @staticmethod
    def _reconcile_review_context(
        *, inventory: Any, context: dict[str, Any], supplied: dict[str, Any] | None
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        spec_requirements = context.get("requirements", [])
        supplied_requirements = (supplied or {}).get("requirements", [])
        findings: list[dict[str, Any]] = []
        if supplied is None or supplied.get("status") == "NOT_PROVIDED":
            active = {
                "challengeId": inventory.challenge_id,
                "status": "DERIVED",
                "mode": "specification_derived",
                "requirements": spec_requirements,
                "source": str(inventory.challenge_context_path),
            }
            if not spec_requirements:
                active["requirements"] = [
                    {
                        "id": criterion,
                        "title": criterion,
                        "source": str(inventory.challenge_context_path),
                    }
                    for criterion in (
                        "Originality",
                        "Feasibility",
                        "Scalability",
                        "Impact Potential",
                        "Alignment with Scope",
                    )
                ]
            status = "derived"
        else:
            active = dict(supplied)
            active["mode"] = "provided_with_spec_reconciliation"
            status = "supplied"
            if supplied.get("challengeId") not in {None, inventory.challenge_id}:
                findings.append(
                    {
                        "type": "conflicting",
                        "field": "challengeId",
                        "supplied": supplied.get("challengeId"),
                        "specification": inventory.challenge_id,
                    }
                )
            spec_by_id = {item.get("id"): item for item in spec_requirements}
            supplied_by_id = {item.get("id"): item for item in supplied_requirements}
            for requirement_id in sorted(set(spec_by_id) ^ set(supplied_by_id)):
                findings.append(
                    {
                        "type": "stale" if requirement_id in supplied_by_id else "missing",
                        "requirementId": requirement_id,
                    }
                )
            for requirement_id in sorted(set(spec_by_id) & set(supplied_by_id)):
                if spec_by_id[requirement_id].get("title") != supplied_by_id[requirement_id].get("title"):
                    findings.append(
                        {
                            "type": "conflicting",
                            "requirementId": requirement_id,
                            "field": "title",
                            "supplied": supplied_by_id[requirement_id].get("title"),
                            "specification": spec_by_id[requirement_id].get("title"),
                        }
                    )
        reconciliation = {
            "challengeId": inventory.challenge_id,
            "status": "conflicting" if any(
                item["type"] == "conflicting" for item in findings
            ) else status,
            "findings": findings,
            "supplied": supplied is not None,
            "derived": status == "derived",
            "sourceLocations": [
                str(inventory.challenge_context_path),
                *([str(inventory.review_context_path)] if inventory.review_context_path else []),
            ],
        }
        return (
            {
                "challengeId": inventory.challenge_id,
                "status": reconciliation["status"],
                "mode": active.get("mode"),
                "supplied": supplied is not None,
                "derived": status == "derived",
                "findings": findings,
            },
            active,
            reconciliation,
        )

    @staticmethod
    def _ideation_source_map(result: Any) -> dict[str, Any]:
        locations = []
        for idea in sorted(result.ideas, key=lambda item: item.idea_id):
            for ref in sorted(set(idea.evidence_refs)):
                parts = ref.split(":", 2)
                locations.append(
                    {
                        "claimId": idea.idea_id,
                        "evidenceRef": ref,
                        "submissionId": idea.submission_id,
                        "sourcePath": parts[1] if len(parts) > 1 else ref,
                        "contentBlock": parts[2] if len(parts) > 2 else None,
                    }
                )
        return {"locations": locations}

    @staticmethod
    def _ideation_contradictions(*, result: Any, decisions: Any, reconciliation: dict[str, Any]) -> dict[str, Any]:
        contradictions = list(reconciliation.get("findings", []))
        for recommendation in result.recommendations.recommendations:
            if recommendation.unresolved_conflicts:
                contradictions.extend(
                    {
                        "type": "conflicting",
                        "criterion": recommendation.criterion,
                        "description": conflict,
                    }
                    for conflict in recommendation.unresolved_conflicts
                )
        return {"contradictions": contradictions}

    @staticmethod
    def _code_source_map(inventory: Any, context: dict[str, Any], matrix: Any, recommendations: Any) -> dict[str, Any]:
        locations = [
            {
                "claimId": item.get("id"),
                "sourceType": "section",
                "sourcePath": str(inventory.challenge_context_path),
                "section": item.get("title"),
            }
            for item in context.get("requirements", [])
        ]
        return {"locations": locations}

    @staticmethod
    def _code_contradictions(matrix: Any, recommendations: Any, decisions: Any) -> dict[str, Any]:
        contradictions = []
        for entry in matrix.entries:
            contradictions.extend(
                {
                    "type": "conflicting",
                    "requirementId": entry.requirement_id,
                    "submissionId": entry.submission_id,
                    "description": conflict,
                }
                for conflict in entry.assessment.unresolved_conflicts
            )
        for decision in decisions.decisions:
            if decision.state in {"manual_review", "unresolved", "blocked"}:
                contradictions.append(
                    {
                        "type": "missing",
                        "requirementId": decision.requirement_id,
                        "description": f"Decision state is {decision.state}.",
                    }
                )
        return {"contradictions": contradictions}

    @staticmethod
    def _ideation_overview(*, inventory: Any, result: Any, decisions: Any, review_status: dict[str, Any], contradictions: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"# {inventory.challenge_id}",
                "",
                "```json",
                json.dumps(
                    {
                        "challengeId": inventory.challenge_id,
                        "mode": inventory.mode,
                        "submissionsAnalyzed": sorted(inventory.submission_ids),
                        "reviewContext": review_status,
                        "ideaCount": len(result.ideas),
                        "decisionStates": [item.state for item in decisions.decisions],
                        "verification": result.verification.to_dict(),
                        "contradictionCount": len(contradictions["contradictions"]),
                    },
                    indent=2,
                    sort_keys=True,
                ),
                "```",
            ]
        ) + "\n"

    @staticmethod
    def _code_overview(inventory: Any, context: dict[str, Any], decisions: Any, review_status: dict[str, Any], verification: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"# {context.get('title', inventory.challenge_id)}",
                "",
                "```json",
                json.dumps(
                    {
                        "challengeId": inventory.challenge_id,
                        "mode": inventory.mode,
                        "submissionsAnalyzed": sorted(inventory.submission_ids),
                        "reviewContext": review_status,
                        "requirementCount": len(context.get("requirements", [])),
                        "decisionStates": [item.state for item in decisions.decisions],
                        "verification": verification,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                "```",
            ]
        ) + "\n"

    @staticmethod
    def _copy_submissions(source: Path, challenge_root: Path) -> None:
        destination = challenge_root / "submissions"
        if destination.exists():
            shutil.rmtree(destination)
        WorkspaceWriter._copy_tree(source, destination)

    @staticmethod
    def _copy_tree(source: Path, destination: Path) -> None:
        if not source.is_dir():
            raise ValueError(f"Source directory does not exist: {source}")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source,
            destination,
            symlinks=False,
            ignore=shutil.ignore_patterns(".DS_Store", ".transplant-snapshots"),
        )

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")

        temporary_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(path)

    @staticmethod
    def _write_text(path: Path, data: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(data, encoding="utf-8")
        temporary_path.replace(path)
