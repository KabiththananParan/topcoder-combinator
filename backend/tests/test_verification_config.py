from pathlib import Path

from app.ingestion.verification_config import VerificationConfigLoader


def test_load_code_verification_config():
    config_path = (
        Path(__file__).resolve().parents[2]
        / "starter-pack"
        / "challenges"
        / "AI_DEAL_SCOPING_ASSISTANT"
        / "verification"
        / "verification-config.json"
    )

    config = VerificationConfigLoader().load(config_path)

    assert config["status"] == "complete after source insertion"
    assert "source integrity before and after processing" in config["requiredChecks"]
    assert config["commands"] == {}
    assert config["source"] == str(config_path.resolve())
