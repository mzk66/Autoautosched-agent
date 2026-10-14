import os

import streamlit as st

from agent.llm.factory import DEFAULT_LLM_PROVIDER, get_default_ollama_base_url, should_ignore_proxy


def render_llm_settings():
    provider_options = [
        "openai_compatible",
        "mock",
    ]

    default_provider = os.getenv(
        "LLM_PROVIDER",
        DEFAULT_LLM_PROVIDER,
    )

    default_provider_index = (
        provider_options.index(default_provider)
        if default_provider in provider_options
        else provider_options.index(DEFAULT_LLM_PROVIDER)
    )

    with st.sidebar:
        st.subheader("模型设置")

        provider = st.selectbox(
            "Provider",
            options=provider_options,
            index=default_provider_index,
        )

        if provider == "mock":
            st.info("演示模式：未连接真实大模型，可上传样例检查数据、执行本地排程。")

        base_url = st.text_input(
            "Base URL",
            disabled=provider == "mock",
            value=os.getenv(
                "LLM_BASE_URL",
                get_default_ollama_base_url(),
            ),
        )

        model = st.text_input(
            "Model",
            disabled=provider == "mock",
            value=os.getenv(
                "LLM_MODEL",
                "qwen2.5:7b",
            ),
        )

        api_key = st.text_input(
            "API Key",
            disabled=provider == "mock",
            value=os.getenv(
                "LLM_API_KEY",
                "ollama",
            ),
            type="password",
        )

        ignore_proxy = st.checkbox(
            "Ignore proxy",
            disabled=provider == "mock",
            value=should_ignore_proxy(base_url),
        )

    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "ignore_proxy": ignore_proxy,
    }
