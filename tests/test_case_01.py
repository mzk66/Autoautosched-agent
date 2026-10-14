from agent.extractor import extract_draft_from_text
from agent.llm.base import LLMMessage, LLMResponse
from agent.llm.factory import parse_default_gateway
from agent.llm.openai_compatible import parse_json_object
from domain.conversation import (
    ChatMessage,
    Conversation,
    make_conversation_title,
)
from domain.draft_schema import ExtractedDraft
from domain.input_bundle import InputBundle, InputFile
from domain.input_reader import build_input_bundle, input_file_to_prompt


class FakeUpload:
    def __init__(
        self,
        name: str,
        content: bytes,
    ):
        self.name = name
        self._content = content

    def getvalue(self):
        return self._content


class FakeLLMClient:
    def chat(
        self,
        messages: list[LLMMessage],
    ) -> LLMResponse:
        return LLMResponse(
            text="{}"
        )

    def extract_json(
        self,
        messages: list[LLMMessage],
        schema_hint: str,
    ) -> dict:
        return {
            "jobs": [
                {
                    "id": "O01",
                    "product": "A",
                    "quantity": 120,
                    "due_time": "2026-09-17 18:00",
                    "priority": "high",
                    "customer_type": "VIP",
                }
            ],
            "machines": [],
            "maintenance": [],
            "objectives": [],
            "constraints": [],
            "assumptions": [],
            "missing_questions": [
                {
                    "field": "machines",
                    "question": "请补充设备信息。",
                }
            ],
        }


def test_parse_json_object_from_markdown_fence():
    assert parse_json_object(
        '```json\n{"ok": true}\n```'
    ) == {
        "ok": True
    }


def test_parse_wsl_default_gateway():
    route_table = (
        "Iface Destination Gateway Flags RefCnt Use Metric Mask\n"
        "eth0 00000000 013017AC 0003 0 0 0 00000000\n"
    )

    assert parse_default_gateway(
        route_table
    ) == "172.23.48.1"


def test_extracted_draft_schema_defaults():
    draft = ExtractedDraft.model_validate(
        {
            "jobs": [
                {
                    "id": "O01",
                    "product": "A",
                    "quantity": 120,
                }
            ]
        }
    )

    assert draft.jobs[0].id == "O01"
    assert draft.jobs[0].quantity == 120
    assert draft.machines == []
    assert draft.missing_questions == []


def test_extract_draft_from_text_with_fake_llm():
    draft = extract_draft_from_text(
        llm=FakeLLMClient(),
        user_text="O01 产品 A 数量 120。",
    )

    assert draft.jobs[0].id == "O01"
    assert draft.jobs[0].customer_type == "VIP"
    assert draft.missing_questions[0].field == "machines"


def test_build_input_bundle_from_text_file():
    bundle = build_input_bundle(
        text="请理解这个订单文件。",
        uploaded_files=[
            FakeUpload(
                name="orders.txt",
                content="O01,A,120".encode("utf-8"),
            )
        ],
    )

    assert bundle.text == "请理解这个订单文件。"
    assert bundle.files[0].name == "orders.txt"
    assert bundle.files[0].file_type == "txt"
    assert "O01,A,120" in input_file_to_prompt(
        bundle.files[0]
    )


def test_make_conversation_title_from_text():
    assert make_conversation_title(
        text="请读取订单文件并告诉我缺什么",
        file_names=[],
        fallback_index=1,
    ) == "请读取订单文件并告诉我缺什么"


def test_conversation_keeps_independent_memory():
    conversation = Conversation(
        title="订单分析"
    )
    conversation.messages.append(
        ChatMessage(
            role="user",
            content="第一轮",
        )
    )

    dumped = conversation.model_dump(
        mode="json"
    )
    restored = Conversation.model_validate(
        dumped
    )

    assert restored.title == "订单分析"
    assert restored.messages[0].content == "第一轮"


def test_conversation_can_rename_and_remove_one_resource():
    first = InputFile(
        name="orders.csv",
        file_type="csv",
        size_bytes=10,
    )
    second = InputFile(
        name="orders.csv",
        file_type="csv",
        size_bytes=10,
    )
    conversation = Conversation()
    conversation.add_input_bundle(
        InputBundle(
            files=[first, second]
        )
    )

    conversation.rename("  九月  订单排程  ")
    removed = conversation.remove_file(
        first.id
    )

    assert conversation.title == "九月 订单排程"
    assert conversation.title_is_custom is True
    assert removed is not None
    assert removed.id == first.id
    assert [
        item.id
        for item in conversation.file_contexts
    ] == [second.id]
    assert [
        item.id
        for item in conversation.input_bundles[0].files
    ] == [second.id]


def test_conversation_migrates_legacy_resource_ids():
    legacy_file = {
        "name": "orders.txt",
        "file_type": "txt",
        "size_bytes": 12,
        "text_excerpt": "O01,A,120",
    }
    conversation = Conversation.model_validate(
        {
            "file_contexts": [legacy_file],
            "input_bundles": [
                {
                    "text": "读取订单",
                    "files": [legacy_file],
                }
            ],
        }
    )

    assert conversation.file_contexts[0].id
    assert (
        conversation.input_bundles[0].files[0].id
        == conversation.file_contexts[0].id
    )
