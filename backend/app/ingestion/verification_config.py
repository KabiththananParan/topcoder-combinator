from __future__ import annotations

import json
from pathlib import Path


class VerificationConfigError(ValueError):
    pass


class VerificationConfigLoader:
    def load(self, config_path: Path) -> dict:
        config_path = config_path.resolve()

        if not config_path.is_file():
            raise VerificationConfigError(
                f"Verification config does not exist: {config_path}"
            )

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise VerificationConfigError(
                f"Invalid JSON in {config_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise VerificationConfigError(
                f"Expected JSON object in {config_path}"
            )

        commands = data.get("commands", {})

        if not isinstance(commands, dict):
            raise VerificationConfigError(
                f"commands must be an object in {config_path}"
            )

        normalized_commands = {
            name: value
            for name, value in commands.items()
            if isinstance(value, str) and value.strip() and value.strip().upper() != "TBD"
        }

        return {
            "status": data.get("status"),
            "requiredChecks": data.get("requiredChecks", []),
            "commands": normalized_commands,
            "source": str(config_path),
        }


    def load_from_verification_path(self, verification_path: Path) -> dict:
        return self.load(verification_path / "verification-config.json")
