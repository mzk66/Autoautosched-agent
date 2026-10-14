from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    text: str
    raw: dict | None = None


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    def chat(
        self,
        messages: list[LLMMessage],
    ) -> LLMResponse:
        ...

    def extract_json(
        self,
        messages: list[LLMMessage],
        schema_hint: str,
    ) -> dict:
        ...
