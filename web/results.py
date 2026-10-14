import streamlit as st

from web.state import get_active_conversation


def render_agent_debug():
    conversation = get_active_conversation()
    state = conversation.workflow_state

    with st.expander(
        "Agent Debug",
        expanded=False,
    ):
        if not state and not conversation.scenario_history:
            st.caption(
                "当前对话还没有运行数据工具链。"
            )
            return

        labels = [
            "Task Context",
            "Parsed Data",
            "Problem IR",
            "Validation Report",
            "Tool Calls",
            "Solver Result",
            "Verification Result",
            "Scenario History",
        ]
        tabs = st.tabs(labels)
        values = [
            state.get("task_context"),
            state.get("parsed_data"),
            state.get("problem_ir"),
            state.get("validation_report"),
            state.get("tool_calls"),
            state.get("solver_result"),
            state.get("verification_result"),
            [
                item.model_dump(mode="json")
                for item in conversation.scenario_history
            ],
        ]

        for tab, value in zip(
            tabs,
            values,
        ):
            with tab:
                st.json(
                    value
                    if value is not None
                    else {}
                )
