from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Topcoder Combinator"
    app_version: str = "0.1.0"
    app_env: str = "development"

    starter_pack_path: Path = PROJECT_ROOT / "starter-pack"
    workspace_path: Path = PROJECT_ROOT / "workspace"

    llm_provider: str = "mock"
    combinator_ai_mode: str | None = None
    llm_model_id: str | None = None
    llm_endpoint_url: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 0
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    openai_api_key: str | None = None

    aws_region: str | None = None
    bedrock_model_id: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()