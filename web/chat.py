import streamlit as st

from domain.input_reader import build_input_bundle
from services.turns import process_turn
from web.files import SUPPORTED_UPLOAD_TYPES
from web.state import get_active_conversation, set_active_conversation


def get_chat_input_parts(
    chat_value,
):
    if chat_value is None:
        return "", []

    if isinstance(chat_value, str):
        return chat_value, []

    text = getattr(
        chat_value,
        "text",
        "",
    ) or ""

    files = getattr(
        chat_value,
        "files",
        [],
    ) or []

    if isinstance(chat_value, dict):
        text = chat_value.get(
            "text",
            text,
        ) or ""

        files = chat_value.get(
            "files",
            files,
        ) or []

    return text, list(files)


def render_chat_app(settings: dict):
    conversation = get_active_conversation()
    for message in conversation.messages:
        with st.chat_message(message.role):
            st.markdown(message.content)
            if message.files:
                st.caption("附件：" + ", ".join(message.files))

    chat_value = st.chat_input(
        "输入排程需求，或上传多个订单/设备文件后提问...",
        accept_file="multiple", file_type=SUPPORTED_UPLOAD_TYPES,
    )
    user_text, uploaded_files = get_chat_input_parts(chat_value)
    if not user_text.strip() and not uploaded_files:
        return
    if not user_text.strip():
        user_text = "我上传了文件。请先阅读并概括其中的排程相关信息，包括订单、设备、约束，以及还缺哪些信息。"
    bundle = build_input_bundle(text=user_text, uploaded_files=uploaded_files)
    with st.chat_message("user"):
        st.write(user_text)
        if bundle.files:
            st.caption("附件：" + ", ".join(item.name for item in bundle.files))
    with st.chat_message("assistant"):
        with st.spinner("正在处理..."):
            reply = process_turn(conversation, bundle, settings, len(st.session_state.conversations))
        st.markdown(reply)
    set_active_conversation(conversation)
    st.rerun()
