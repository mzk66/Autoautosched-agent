import streamlit as st

from domain.conversation import Conversation, make_conversation_title
from storage.conversations import load_conversations, save_conversations


def save_conversations_to_disk():
    save_conversations(st.session_state.conversations, st.session_state.active_conversation_id)


def init_conversations():
    if "conversations" in st.session_state:
        return

    conversations, stored_active_id = (
        load_conversations()
    )

    if not conversations:
        conversation = Conversation()
        conversations[conversation.id] = (
            conversation.model_dump(
                mode="json"
            )
        )

    st.session_state.conversations = conversations

    active_id = st.session_state.get(
        "active_conversation_id"
    )

    if active_id not in conversations:
        st.session_state.active_conversation_id = (
            stored_active_id
            if stored_active_id in conversations
            else next(iter(conversations))
        )


def get_active_conversation() -> Conversation:
    init_conversations()

    conversation_id = st.session_state.active_conversation_id

    return Conversation.model_validate(
        st.session_state.conversations[
            conversation_id
        ]
    )


def set_active_conversation(
    conversation: Conversation,
):
    st.session_state.conversations[
        conversation.id
    ] = conversation.model_dump(
        mode="json"
    )
    st.session_state.active_conversation_id = (
        conversation.id
    )
    save_conversations_to_disk()


def create_new_conversation():
    conversation = Conversation(
        title=make_conversation_title(
            text="",
            file_names=[],
            fallback_index=len(st.session_state.conversations) + 1,
        )
    )
    set_active_conversation(
        conversation
    )


def rename_conversation(
    conversation_id: str,
    title: str,
):
    conversation = Conversation.model_validate(
        st.session_state.conversations[
            conversation_id
        ]
    )
    conversation.rename(title)
    set_active_conversation(conversation)


def delete_conversation(
    conversation_id: str,
):
    conversations = st.session_state.conversations

    if conversation_id not in conversations:
        return

    del conversations[conversation_id]

    if not conversations:
        replacement = Conversation(
            title="新对话 1"
        )
        conversations[replacement.id] = (
            replacement.model_dump(
                mode="json"
            )
        )
        st.session_state.active_conversation_id = (
            replacement.id
        )
    elif (
        st.session_state.active_conversation_id
        == conversation_id
    ):
        st.session_state.active_conversation_id = (
            sorted_conversations()[0].id
        )

    save_conversations_to_disk()


def sorted_conversations():
    return sorted(
        [
            Conversation.model_validate(
                item
            )
            for item in st.session_state.conversations.values()
        ],
        key=lambda item: item.updated_at,
        reverse=True,
    )


def add_input_bundle_to_context(
    bundle,
):
    conversation = get_active_conversation()
    conversation.add_input_bundle(bundle)
    set_active_conversation(
        conversation
    )

    return [
        input_file.name
        for input_file in bundle.files
    ]


def remove_file_from_context(
    file_id: str,
):
    conversation = get_active_conversation()
    conversation.remove_file(file_id)
    set_active_conversation(conversation)
