from agent.llm.base import LLMClient, LLMMessage, LLMResponse


class MockLLMClient(LLMClient):
    def __init__(
        self,
        reply: str = "演示模式：未连接真实大模型。",
    ):
        self.reply = reply

    def chat(
        self,
        messages: list[LLMMessage],
    ) -> LLMResponse:
        last_user_message = next(
            (
                message.content
                for message in reversed(messages)
                if message.role == "user"
            ),
            "",
        )

        return LLMResponse(
            text=(
                f"{self.reply}\n\n"
                f"你刚才说：{last_user_message}"
            ),
            raw=None,
        )

    def extract_json(
        self,
        messages: list[LLMMessage],
        schema_hint: str,
    ) -> dict:
        return {
            "mock": True,
            "schema_hint": schema_hint,
            "message_count": len(messages),
        }
