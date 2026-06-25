from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class PromptBudget:
    max_context_chars: int
    chars_per_token: int = 4

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // self.chars_per_token)

    def estimate_cost_usd(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        prompt_cost_per_1k: float = 0.00015,
        completion_cost_per_1k: float = 0.0006,
    ) -> float:
        return round((prompt_tokens / 1000.0) * prompt_cost_per_1k + (completion_tokens / 1000.0) * completion_cost_per_1k, 6)

    def fit_texts(self, texts: Sequence[str]) -> list[str]:
        kept: list[str] = []
        used = 0
        for text in texts:
            if used >= self.max_context_chars:
                break
            remaining = self.max_context_chars - used
            piece = text[:remaining]
            if piece:
                kept.append(piece)
                used += len(piece)
        return kept
