import streamlit as st

from domain.input_bundle import InputFile
from domain.input_reader import build_input_bundle
from web.state import add_input_bundle_to_context, get_active_conversation, remove_file_from_context

SUPPORTED_UPLOAD_TYPES = ["xlsx", "xls", "csv", "txt"]


def render_sidebar_file_list():
    conversation = get_active_conversation()
    file_contexts = conversation.file_contexts

    with st.sidebar:
        st.subheader("资料")

        upload_version_key = (
            f"resource_upload_version_{conversation.id}"
        )
        upload_version = st.session_state.get(
            upload_version_key,
            0,
        )
        pending_files = st.file_uploader(
            "添加文件",
            type=SUPPORTED_UPLOAD_TYPES,
            accept_multiple_files=True,
            key=(
                f"resource_upload_{conversation.id}_{upload_version}"
            ),
        )

        if st.button(
            "添加到当前对话",
            icon=":material/upload_file:",
            disabled=not pending_files,
            key=f"add_resources_{conversation.id}_{upload_version}",
            use_container_width=True,
        ):
            bundle = build_input_bundle(
                text="",
                uploaded_files=pending_files,
            )
            add_input_bundle_to_context(bundle)
            st.session_state[upload_version_key] = (
                upload_version + 1
            )
            st.rerun()

        if not file_contexts:
            st.caption(
                "当前对话还没有资料。"
            )
            return

        for item in file_contexts:
            input_file = InputFile.model_validate(item)
            name_column, delete_column = st.columns(
                [3.5, 1.5],
                gap="small",
            )

            with name_column:
                st.write(input_file.name)
                st.caption(
                    f"{input_file.file_type.upper()} · "
                    f"{input_file.size_bytes / 1024:.1f} KB"
                )

            with delete_column:
                if st.button(
                    "删除",
                    key=f"delete_resource_{input_file.id}",
                    icon=":material/delete:",
                    help=f"移除资料：{input_file.name}",
                    use_container_width=True,
                ):
                    remove_file_from_context(
                        input_file.id
                    )
                    st.rerun()
