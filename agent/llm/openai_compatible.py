import json
from urllib.parse import urljoin

import requests

from agent.llm.base import LLMClient, LLMError, LLMMessage, LLMResponse


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 120,
        ignore_proxy: bool = False,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.trust_env = not ignore_proxy

    def chat(
        self,
        messages: list[LLMMessage],
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = self.session.post(
                urljoin(self.base_url, "chat/completions"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise LLMError(
                f"LLM request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise LLMError(
                "LLM request failed with "
                f"HTTP {response.status_code}: {response.text}"
            )

        data = response.json()

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Unexpected LLM response: {data}"
            ) from exc

        return LLMResponse(
            text=text,
            raw=data,
        )

    def extract_json(
        self,
        messages: list[LLMMessage],
        schema_hint: str,
    ) -> dict:
        json_messages = [
            LLMMessage(
                role="system",
                content=(
                    "You must return valid JSON only. "
                    "Do not wrap it in markdown fences. "
                    "Do not add explanations.\n\n"
                    f"Schema hint:\n{schema_hint}"
                ),
            ),
            *messages,
        ]

        response = self.chat(
            json_messages
        )

        return parse_json_object(
            response.text
        )


def parse_json_object(
    text: str,
) -> dict:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()

        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise

        value = json.loads(
            cleaned[start:end + 1]
        )

    if not isinstance(value, dict):
        raise LLMError(
            "Expected a JSON object from LLM."
        )

    return value
