from datetime import date

from pydantic import ValidationError

from agent.llm.base import LLMClient, LLMMessage
from agent.prompts import (
    EXTRACT_DRAFT_SCHEMA_HINT,
    EXTRACT_DRAFT_SYSTEM_PROMPT,
)
from domain.draft_schema import ExtractedDraft


def extract_draft_from_text(
    llm: LLMClient,
    user_text: str,
    current_date: date | None = None,
) -> ExtractedDraft:
    if not user_text.strip():
        raise ValueError(
            "User text cannot be empty."
        )

    resolved_date = (
        current_date
        or date.today()
    )

    data = llm.extract_json(
        messages=[
            LLMMessage(
                role="system",
                content=EXTRACT_DRAFT_SYSTEM_PROMPT,
            ),
            LLMMessage(
                role="user",
                content=(
                    f"current_date: {resolved_date.isoformat()}\n\n"
                    "user_input:\n"
                    f"{user_text}"
                ),
            ),
        ],
        schema_hint=EXTRACT_DRAFT_SCHEMA_HINT,
    )

    try:
        return ExtractedDraft.model_validate(
            data
        )
    except ValidationError:
        raise
