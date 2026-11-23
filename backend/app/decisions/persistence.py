from __future__ import annotations

import json
from pathlib import Path

from app.decisions.models import Decision, DecisionSet


class DecisionPersistence:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def path_for(self, challenge_id: str) -> Path:
        return (
            self.workspace_root
            / challenge_id
            / "decisions.json"
        )

    def save(self, decisions: DecisionSet) -> Path:
        path = self.path_for(decisions.challenge_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = decisions.to_dict()
        path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        return path

    def load(self, challenge_id: str) -> DecisionSet | None:
        path = self.path_for(challenge_id)

        if not path.exists():
            return None

        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        decisions = [
            Decision(
                requirement_id=item["requirementId"],
                requirement_title=item["requirementTitle"],
                state=item["state"],
                selected_submission_id=item.get(
                    "selectedSubmissionId"
                ),
                recommended_submission_id=item.get(
                    "recommendedSubmissionId"
                ),
                reason=item.get("reason", ""),
                recommendation_score=item.get(
                    "recommendationScore"
                ),
                recommendation_confidence=item.get(
                    "recommendationConfidence"
                ),
                evidence_refs=item.get("evidenceRefs", []),
                alternatives=item.get("alternatives", []),
                alternative_submission_id=item.get(
                    "alternativeSubmissionId"
                ),
                reviewer=item.get("reviewer"),
            )
            for item in payload.get("decisions", [])
        ]

        return DecisionSet(
            challenge_id=payload["challengeId"],
            decisions=decisions,
        )
