from __future__ import annotations

from typing import Protocol

from .models import LLMResponse, UsageReport


class LLMProvider(Protocol):
    provider_name: str
    model: str | None
    usage: UsageReport

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate text through the provider-specific adapter."""
