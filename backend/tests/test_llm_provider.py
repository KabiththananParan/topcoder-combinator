from app.core.config import Settings
from app.llm.bedrock_provider import BedrockProvider
from app.llm.factory import create_provider
from app.llm.mock_provider import MockProvider
from app.pipeline.challenge_orchestrator import ChallengeOrchestrator


def test_mock_provider_is_deterministic_without_credentials():
    first = MockProvider().generate("same prompt")
    second = MockProvider().generate("same prompt")

    assert first == second
    assert first.text.startswith("MOCK_RESPONSE_")


def test_mock_provider_reports_unknown_tokens_and_zero_cost():
    provider = MockProvider()

    provider.generate("prompt")

    assert provider.usage.to_dict() == {
        "provider": "mock",
        "model": "deterministic-mock",
        "calls": 1,
        "inputTokens": None,
        "outputTokens": None,
        "totalTokens": None,
        "approximateCost": 0.0,
        "retries": 0,
        "failures": 0,
        "processingTimeMs": provider.usage.processing_time_ms,
    }


def test_orchestrator_uses_configured_provider_adapter():
    provider = MockProvider()
    orchestrator = ChallengeOrchestrator(provider=provider)

    assert orchestrator.provider is provider


def test_bedrock_configuration_loads_without_credentials():
    configuration = Settings(
        llm_provider="bedrock",
        aws_region="us-east-1",
        bedrock_model_id="configured-model",
    )

    assert configuration.aws_region == "us-east-1"
    assert configuration.bedrock_model_id == "configured-model"


def test_bedrock_adapter_reports_provider_usage():
    configuration = Settings(
        llm_provider="bedrock",
        aws_region="us-east-1",
        bedrock_model_id="configured-model",
    )
    with patch("boto3.client") as client:
        client.return_value.converse.return_value = {
            "output": {"message": {"content": [{"text": "answer"}]}},
            "usage": {"inputTokens": 4, "outputTokens": 6},
        }
        provider = BedrockProvider(configuration)
        response = provider.generate("prompt")

    assert response.text == "answer"
    assert provider.usage.to_dict()["totalTokens"] == 10
    assert provider.usage.to_dict()["approximateCost"] is None


def test_factory_selects_mock_from_configuration():
    provider = create_provider(Settings(llm_provider="mock"))

    assert isinstance(provider, MockProvider)
from unittest.mock import patch

