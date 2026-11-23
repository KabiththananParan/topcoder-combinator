from app.core.config import Settings, settings

from .bedrock_provider import BedrockProvider
from .mock_provider import MockProvider
from .provider import LLMProvider


def create_provider(configuration: Settings | None = None) -> LLMProvider:
    active = configuration or settings
    provider = (
        active.combinator_ai_mode or active.llm_provider
    ).strip().lower()
    if provider == "mock":
        return MockProvider(active.llm_model_id or "deterministic-mock")
    if provider in {"bedrock", "amazon-bedrock"}:
        return BedrockProvider(active)
    raise ValueError(f"Unsupported LLM_PROVIDER: {active.llm_provider}")
