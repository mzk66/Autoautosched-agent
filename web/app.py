import streamlit as st

from web.chat import render_chat_app
from web.conversations import render_conversation_sidebar
from web.files import render_sidebar_file_list
from web.results import render_agent_debug
from web.settings import render_llm_settings
from web.state import get_active_conversation, init_conversations


def main():
    st.set_page_config(page_title="AutoSched Agent", layout="wide")
    st.title("AutoSched Agent")
    st.caption("LLM 负责理解与编排，确定性工具处理数据，Solver 生成排程。")
    init_conversations()
    render_conversation_sidebar()
    conversation = get_active_conversation()
    st.caption(f"当前对话：{conversation.title}")
    stage = conversation.workflow_state.get("stage")
    if stage:
        st.caption(f"任务阶段：{stage.upper()} · 已完成方案：{len(conversation.scenario_history)}")
    render_sidebar_file_list()
    render_agent_debug()
    render_chat_app(render_llm_settings())
