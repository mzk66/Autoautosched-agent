from pathlib import Path

from streamlit.testing.v1 import AppTest

from domain.conversation import Conversation
from domain.input_bundle import InputBundle
from services.turns import process_turn
from storage.conversations import load_conversations, save_conversations
from tests.test_scheduling_workflow import make_input_file


def test_conversation_store_roundtrip(tmp_path):
    path = tmp_path / "nested" / "conversations.json"
    first = Conversation(title="排程测试")
    second = Conversation(title="独立会话")
    conversations = {item.id: item.model_dump(mode="json") for item in (first, second)}
    save_conversations(conversations, second.id, path)
    restored, active_id = load_conversations(path)
    assert active_id == second.id
    assert restored == conversations
    assert first.title == "排程测试"


def test_conversation_store_missing_and_invalid_json(tmp_path):
    path = tmp_path / "conversations.json"
    assert load_conversations(path) == ({}, None)
    path.write_text("{invalid", encoding="utf-8")
    assert load_conversations(path) == ({}, None)


def test_turns_inspect_then_solve_and_keep_versions():
    conversation = Conversation()
    process_turn(conversation, InputBundle(text="检查数据", files=[make_input_file()]), {}, 1)
    assert conversation.workflow_state["stage"] == "ready_for_confirmation"
    assert conversation.scenario_history == []
    assert len(conversation.file_contexts) == 1
    for version in (1, 2):
        reply = process_turn(conversation, InputBundle(text="开始排程"), {}, 1)
        assert f"方案 V{version}" in reply
        assert conversation.scenario_history[-1].verification_passed
        assert conversation.scenario_history[-1].version == version
    assert [message.role for message in conversation.messages] == ["user", "assistant"] * 3


def test_turn_blocks_missing_data():
    conversation = Conversation()
    process_turn(conversation, InputBundle(text="开始排程", files=[make_input_file(due_time=None)]), {}, 1)
    assert conversation.workflow_state["stage"] == "clarifying"
    assert conversation.scenario_history == []
    assert "solve_schedule" not in conversation.workflow_state["tool_calls"]


def test_turn_records_mock_chat_and_custom_title():
    conversation = Conversation(title="我的任务", title_is_custom=True)
    reply = process_turn(conversation, InputBundle(text="你好"), {"provider": "mock", "base_url": "", "model": "", "api_key": "", "ignore_proxy": True}, 1)
    assert "你好" in reply
    assert conversation.title == "我的任务"
    assert conversation.messages[-1].content == reply


def test_web_entry_chat_and_new_conversation(tmp_path, monkeypatch):
    from web import state

    path = tmp_path / "conversations.json"
    monkeypatch.setattr(state, "load_conversations", lambda: load_conversations(path))
    monkeypatch.setattr(state, "save_conversations", lambda items, active: save_conversations(items, active, path))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    entry = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entry), default_timeout=15).run()
    assert not app.exception
    app.chat_input[0].set_value("你好").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    restored, active_id = load_conversations(path)
    assert len(restored[active_id]["messages"]) == 2
    next(button for button in app.button if button.label == "新建对话").click().run()
    assert not app.exception
    restored, active_id = load_conversations(path)
    assert len(restored) == 2
    assert restored[active_id]["messages"] == []
