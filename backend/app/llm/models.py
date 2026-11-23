from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageReport:
    provider: str
    model: str | None
    calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    approximate_cost: float | None = None
    retries: int = 0
    failures: int = 0
    processing_time_ms: int = 0

    def record(
        self,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
        processing_time_ms: int,
        retries: int = 0,
        failed: bool = False,
        approximate_cost: float | None = None,
    ) -> None:
        had_calls = self.calls > 0
        self.calls += 1
        self.retries += retries
        self.failures += int(failed)
        self.processing_time_ms += processing_time_ms
        self.input_tokens = (
            input_tokens
            if not had_calls
            else _sum_optional(self.input_tokens, input_tokens)
        )
        self.output_tokens = (
            output_tokens
            if not had_calls
            else _sum_optional(self.output_tokens, output_tokens)
        )
        if approximate_cost is not None:
            self.approximate_cost = (
                (self.approximate_cost or 0.0) + approximate_cost
            )

    def to_dict(self) -> dict[str, object]:
        total_tokens = (
            self.input_tokens + self.output_tokens
            if self.input_tokens is not None
            and self.output_tokens is not None
            else None
        )
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": self.calls,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": total_tokens,
            "approximateCost": self.approximate_cost,
            "retries": self.retries,
            "failures": self.failures,
            "processingTimeMs": self.processing_time_ms,
        }


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def _sum_optional(
    current: int | None,
    value: int | None,
) -> int | None:
    if current is None or value is None:
        return None
    return current + value
