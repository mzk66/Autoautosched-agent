from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

from agent.llm.factory import create_llm_client
from agent.llm.mock import MockLLMClient
from domain.input_bundle import InputBundle
from tests.test_scheduling_workflow import make_input_file


def test_first_run_without_env_or_model_server(tmp_path, monkeypatch):
    # Use a fresh working directory so no developer configuration or conversations are read.
    monkeypatch.chdir(tmp_path)
    for name in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "LLM_IGNORE_PROXY"):
        monkeypatch.delenv(name, raising=False)

    def forbid_model_request(*args, **kwargs):
        raise AssertionError("First-run demo must not contact a model server")

    monkeypatch.setattr(requests.Session, "post", forbid_model_request)
    assert isinstance(create_llm_client(), MockLLMClient)
    entry = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(entry), default_timeout=15).run()
    assert not app.exception
    assert app.selectbox[0].value == "mock"
    assert any("演示模式" in item.value for item in app.info)
    app.chat_input[0].set_value("你好").run()
    assert not app.exception
    assert "未连接真实大模型" in app.chat_message[-1].markdown[0].value

    from domain.conversation import Conversation

    active_id = app.session_state.active_conversation_id
    conversation = Conversation.model_validate(app.session_state.conversations[active_id])
    conversation.add_input_bundle(InputBundle(files=[make_input_file()]))
    app.session_state.conversations[active_id] = conversation.model_dump(mode="json")
    app.chat_input[0].set_value("开始排程").run()
    assert not app.exception
    restored = Conversation.model_validate(app.session_state.conversations[active_id])
    assert restored.scenario_history[-1].verification_passed
    assert restored.workflow_state["stage"] == "completed"
