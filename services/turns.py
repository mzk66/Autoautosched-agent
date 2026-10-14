from agent.chat import build_llm_messages, create_llm_from_settings
from agent.llm.base import LLMError
from agent.routing import classify_scheduling_action, enforce_llm_boundary
from agent.workflow import run_scheduling_workflow
from domain.conversation import ChatMessage, Conversation, make_conversation_title
from domain.input_bundle import InputBundle
from domain.workflow_schema import ScenarioRecord


def process_turn(conversation: Conversation, bundle: InputBundle, settings: dict, fallback_index: int) -> str:
    """处理一轮消息，原地更新会话；持久化由调用方负责。"""
    attached_names = [item.name for item in bundle.files]
    conversation.add_input_bundle(bundle)
    conversation.messages.append(ChatMessage(role="user", content=bundle.text, files=attached_names))
    if not conversation.title_is_custom and len(conversation.messages) == 1:
        conversation.title = make_conversation_title(
            text=bundle.text, file_names=attached_names, fallback_index=fallback_index,
        )
    conversation.touch()

    action = classify_scheduling_action(bundle.text, has_new_files=bool(bundle.files))
    if action is not None:
        try:
            version = len(conversation.scenario_history) + 1
            result = run_scheduling_workflow(
                action=action, input_files=conversation.file_contexts, scenario_version=version,
            )
            reply = result.response_text
            conversation.workflow_state = result.model_dump(mode="json")
            if result.stage == "completed" and result.solver_result is not None:
                verification = result.verification_result
                conversation.record_scenario(ScenarioRecord(
                    version=version,
                    solver_status=result.solver_result.status,
                    verification_passed=verification.passed if verification is not None else False,
                    result=result.solver_result,
                ))
        except Exception as exc:
            reply = f"确定性工具链执行失败，未调用或未发布排程结果。\n\n{exc}"
    else:
        try:
            llm = create_llm_from_settings(settings)
            reply = enforce_llm_boundary(llm.chat(build_llm_messages(conversation)).text)
        except (LLMError, ValueError) as exc:
            reply = f"AI 连接失败。\n\n{exc}"

    conversation.messages.append(ChatMessage(role="assistant", content=reply))
    conversation.touch()
    return reply
