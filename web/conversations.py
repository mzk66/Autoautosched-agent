import streamlit as st

from domain.conversation import Conversation
from web.state import (
    create_new_conversation, delete_conversation, get_active_conversation,
    rename_conversation, save_conversations_to_disk, sorted_conversations,
)


def render_conversation_sidebar():
    with st.sidebar:
        st.subheader("对话")

        if st.button(
            "新建对话",
            icon=":material/add:",
            use_container_width=True,
        ):
            st.session_state.pop(
                "pending_delete_conversation_id",
                None,
            )
            create_new_conversation()
            st.rerun()

        for conversation in sorted_conversations():
            prefix = (
                "● "
                if conversation.id == st.session_state.active_conversation_id
                else ""
            )

            title_column, delete_column = st.columns(
                [3.5, 1.5],
                gap="small",
            )

            with title_column:
                if st.button(
                    prefix + conversation.title,
                    key=f"conversation_{conversation.id}",
                    use_container_width=True,
                ):
                    st.session_state.active_conversation_id = (
                        conversation.id
                    )
                    st.session_state.pop(
                        "pending_delete_conversation_id",
                        None,
                    )
                    save_conversations_to_disk()
                    st.rerun()

            with delete_column:
                if st.button(
                    "删除",
                    key=f"delete_conversation_{conversation.id}",
                    icon=":material/delete:",
                    help=f"删除对话：{conversation.title}",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_conversation_id = (
                        conversation.id
                    )

        pending_id = st.session_state.get(
            "pending_delete_conversation_id"
        )

        if pending_id in st.session_state.conversations:
            pending = Conversation.model_validate(
                st.session_state.conversations[
                    pending_id
                ]
            )
            st.warning(
                f"确定删除“{pending.title}”及其全部消息和资料吗？"
            )
            confirm_column, cancel_column = st.columns(2)

            with confirm_column:
                if st.button(
                    "确认删除",
                    key="confirm_delete_conversation",
                    type="primary",
                    use_container_width=True,
                ):
                    delete_conversation(pending_id)
                    st.session_state.pop(
                        "pending_delete_conversation_id",
                        None,
                    )
                    st.rerun()

            with cancel_column:
                if st.button(
                    "取消",
                    key="cancel_delete_conversation",
                    use_container_width=True,
                ):
                    st.session_state.pop(
                        "pending_delete_conversation_id",
                        None,
                    )
                    st.rerun()

        active = get_active_conversation()
        revision = int(
            active.updated_at.timestamp()
            * 1_000_000
        )

        with st.form(
            key=f"rename_conversation_{active.id}_{revision}",
            border=False,
        ):
            new_title = st.text_input(
                "当前对话名称",
                value=active.title,
                max_chars=80,
            )

            if st.form_submit_button(
                "保存名称",
                icon=":material/edit:",
                use_container_width=True,
            ):
                try:
                    rename_conversation(
                        active.id,
                        new_title,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

        st.divider()
