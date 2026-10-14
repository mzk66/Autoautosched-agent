import json

from agent.llm.base import LLMMessage
from agent.llm.factory import create_llm_client
from agent.prompts import CHAT_SYSTEM_PROMPT
from domain.conversation import Conversation


def create_llm_from_settings(
    settings: dict,
):
    return create_llm_client(
        provider=settings["provider"],
        base_url=settings["base_url"],
        api_key=settings["api_key"],
        model=settings["model"],
        ignore_proxy=settings["ignore_proxy"],
    )



def build_llm_messages(conversation: Conversation):
    messages = [
        LLMMessage(
            role="system",
            content=CHAT_SYSTEM_PROMPT,
        ),
        LLMMessage(
            role="system",
            content=(
                "本轮没有向你提供原始文件内容或 Solver Result。"
                "不得输出任何具体排程、机器分配、生产时间、"
                "可行性结论或 KPI。"
            ),
        ),
    ]

    task_context = conversation.workflow_state.get(
        "task_context"
    )
    if task_context:
        safe_context = {
            "stage": conversation.workflow_state.get("stage"),
            "data_summary": task_context.get("data_summary", {}),
            "goals": task_context.get("goals", []),
            "unresolved_issues": [
                item.get("message", "")
                for item in task_context.get(
                    "unresolved_issues",
                    [],
                )
            ],
            "completed_scenarios": len(
                conversation.scenario_history
            ),
        }
        messages.append(
            LLMMessage(
                role="system",
                content=(
                    "以下是程序生成的安全任务摘要，仅用于回答任务阶段、"
                    "目标和待确认事项，不得据此生成排程结果：\n"
                    + json.dumps(
                        safe_context,
                        ensure_ascii=False,
                    )
                ),
            )
        )

    for message in conversation.messages:
        if message.role in {
            "user",
            "assistant",
        }:
            messages.append(
                LLMMessage(
                    role=message.role,
                    content=message.content,
                )
            )

    return messages
