from __future__ import annotations

import hashlib
import time

from .models import LLMResponse, UsageReport


class MockProvider:
    """Deterministic, offline provider used by tests and local demos."""

    provider_name = "mock"

    def __init__(self, model: str = "deterministic-mock") -> None:
        self.model = model
        self.usage = UsageReport(
            provider=self.provider_name,
            model=model,
            approximate_cost=0.0,
        )

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        started = time.perf_counter()
        material = f"{system_prompt or ''}\n{prompt}".encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()
        response = LLMResponse(
            text=f"MOCK_RESPONSE_{digest[:16]}",
        )
        self.usage.record(
            input_tokens=None,
            output_tokens=None,
            processing_time_ms=_elapsed_ms(started),
            approximate_cost=0.0,
        )
        return response


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))
