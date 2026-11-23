from __future__ import annotations

import time
from typing import Any

from app.core.config import Settings

from .models import LLMResponse, UsageReport


class BedrockProvider:
    """Small adapter around Bedrock Runtime Converse.

    boto3 is imported lazily so deterministic mode and tests do not require
    AWS credentials or a network connection.
    """

    provider_name = "amazon-bedrock"

    def __init__(self, settings: Settings) -> None:
        if not settings.aws_region:
            raise ValueError("AWS_REGION is required for Bedrock.")
        if not settings.bedrock_model_id and not settings.llm_model_id:
            raise ValueError(
                "BEDROCK_MODEL_ID or LLM_MODEL_ID is required for Bedrock."
            )

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required only when LLM_PROVIDER=bedrock."
            ) from exc

        self.model = settings.bedrock_model_id or settings.llm_model_id
        self.usage = UsageReport(
            provider=self.provider_name,
            model=self.model,
        )
        self._settings = settings
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            endpoint_url=settings.llm_endpoint_url,
            config=Config(
                connect_timeout=settings.llm_timeout_seconds,
                read_timeout=settings.llm_timeout_seconds,
                retries={"max_attempts": 0},
            ),
        )

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        started = time.perf_counter()
        retries = 0
        request: dict[str, Any] = {
            "modelId": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "inferenceConfig": {
                "temperature": self._settings.llm_temperature,
                "maxTokens": self._settings.llm_max_tokens,
            },
        }
        if system_prompt:
            request["system"] = [{"text": system_prompt}]

        for attempt in range(self._settings.llm_max_retries + 1):
            try:
                response = self._client.converse(**request)
                usage = response.get("usage", {})
                text = response["output"]["message"]["content"][0]["text"]
                result = LLMResponse(
                    text=text,
                    input_tokens=usage.get("inputTokens"),
                    output_tokens=usage.get("outputTokens"),
                )
                self.usage.record(
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    processing_time_ms=_elapsed_ms(started),
                    retries=retries,
                )
                return result
            except Exception:
                if attempt < self._settings.llm_max_retries:
                    retries += 1
                    continue
                self.usage.record(
                    input_tokens=None,
                    output_tokens=None,
                    processing_time_ms=_elapsed_ms(started),
                    retries=retries,
                    failed=True,
                )
                raise


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
