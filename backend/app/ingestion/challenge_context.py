from __future__ import annotations

import json
from pathlib import Path

from app.analysis.models import Requirement


class ChallengeContextError(ValueError):
    pass


class ChallengeContextLoader:
    def load(self, context_path: Path) -> dict:
        context_path = context_path.resolve()

        if not context_path.is_file():
            raise ChallengeContextError(
                f"Challenge context does not exist: {context_path}"
            )

        try:
            data = json.loads(context_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ChallengeContextError(
                f"Invalid JSON in {context_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ChallengeContextError(
                f"Expected JSON object in {context_path}"
            )

        return data

    def load_requirements(self, context_path: Path) -> list[Requirement]:
        data = self.load(context_path)

        requirements = data.get("requirements", [])

        if not isinstance(requirements, list):
            raise ChallengeContextError(
                f"requirements must be a list in {context_path}"
            )

        result: list[Requirement] = []

        for item in requirements:
            if not isinstance(item, dict):
                raise ChallengeContextError(
                    f"Requirement entry must be an object in {context_path}"
                )

            requirement_id = item.get("id")
            title = item.get("title")
            priority = item.get("priority", "medium")
            constraints = item.get("constraints", [])

            if not requirement_id or not title:
                raise ChallengeContextError(
                    f"Requirement is missing id or title in {context_path}"
                )

            constraint_texts = []

            for constraint in constraints:
                if isinstance(constraint, dict):
                    text = constraint.get("text")
                    if text:
                        constraint_texts.append(text)
                elif isinstance(constraint, str):
                    constraint_texts.append(constraint)

            result.append(
                Requirement(
                    requirement_id=requirement_id,
                    title=title,
                    priority=priority,
                    constraints=constraint_texts,
                )
            )

        return result
