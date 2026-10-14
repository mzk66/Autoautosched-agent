import json
from pathlib import Path

from domain.conversation import Conversation

CONVERSATION_STORE = Path("data/conversations.json")


def load_conversations(path: Path = CONVERSATION_STORE) -> tuple[
    dict[str, dict],
    str | None,
]:
    if not path.exists():
        return {}, None

    try:
        raw = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        return {}, None

    conversations = {}

    for item in raw.get(
        "conversations",
        [],
    ):
        conversation = Conversation.model_validate(
            item
        )
        conversations[conversation.id] = (
            conversation.model_dump(
                mode="json"
            )
        )

    return (
        conversations,
        raw.get("active_conversation_id"),
    )


def save_conversations(conversations: dict[str, dict], active_id: str | None, path: Path = CONVERSATION_STORE):
    conversations = [
        Conversation.model_validate(
            item
        ).model_dump(
            mode="json"
        )
        for item in conversations.values()
    ]

    payload = {
        "active_conversation_id": active_id,
        "conversations": conversations,
    }

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
