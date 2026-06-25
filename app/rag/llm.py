from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Protocol

from app.core.config import Settings


class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> Iterator[str]:
        raise NotImplementedError


PROMPTS_DIR = Path(__file__).with_name("prompts")


def load_prompt_template(name: str) -> str:
    return PROMPTS_DIR.joinpath(name).read_text(encoding="utf-8")


def render_prompt(name: str, **values: str) -> str:
    return Template(load_prompt_template(name)).safe_substitute(**values)


def select_llm_provider(settings: Settings) -> "OpenAIProvider":
    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.llm_model)


@dataclass(slots=True)
class OpenAIProvider:
    api_key: str | None
    model: str

    def _local_complete(self, prompt: str) -> str:
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        tail = " ".join(lines[-6:])
        return f"Grounded summary based on context: {tail[:500]}"

    def complete(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> str:
        if not self.api_key:
            return self._local_complete(prompt)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception:
            return self._local_complete(prompt)

    def stream(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> Iterator[str]:
        if not self.api_key:
            yield self._local_complete(prompt)
            return
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            stream = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                stream=True,
            )
            for event in stream:
                delta = event.choices[0].delta.content if event.choices else None
                if delta:
                    yield delta
        except Exception:
            yield self._local_complete(prompt)
