import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from agent.llm.base import LLMClient
from agent.llm.mock import MockLLMClient
from agent.llm.openai_compatible import OpenAICompatibleLLMClient

DEFAULT_LLM_PROVIDER = "mock"


def parse_default_gateway(
    route_table: str,
) -> str | None:
    for line in route_table.splitlines()[1:]:
        fields = line.split()

        if len(fields) < 4:
            continue

        destination = fields[1]
        gateway = fields[2]
        flags = fields[3]

        try:
            is_gateway = int(flags, 16) & 0x2
            gateway_bytes = bytes.fromhex(
                gateway
            )[::-1]
        except ValueError:
            continue

        if destination == "00000000" and is_gateway:
            return str(
                ip_address(gateway_bytes)
            )

    return None


def get_wsl_windows_host() -> str | None:
    if not os.getenv("WSL_DISTRO_NAME"):
        try:
            kernel_release = Path(
                "/proc/sys/kernel/osrelease"
            ).read_text()
        except OSError:
            return None

        if "microsoft" not in kernel_release.lower():
            return None

    try:
        route_table = Path(
            "/proc/net/route"
        ).read_text()
    except OSError:
        return None

    return parse_default_gateway(
        route_table
    )


def get_default_ollama_base_url() -> str:
    host = get_wsl_windows_host() or "localhost"
    return f"http://{host}:11434/v1"


def create_llm_client(
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    ignore_proxy: bool | None = None,
) -> LLMClient:
    load_env_file()

    resolved_provider = (
        provider
        or os.getenv("LLM_PROVIDER")
        or DEFAULT_LLM_PROVIDER
    )

    if resolved_provider == "mock":
        return MockLLMClient()

    if resolved_provider != "openai_compatible":
        raise ValueError(
            f"Unknown LLM_PROVIDER: {resolved_provider}"
        )

    resolved_base_url = (
        base_url
        or os.getenv("LLM_BASE_URL")
        or get_default_ollama_base_url()
    )

    resolved_api_key = (
        api_key
        or os.getenv("LLM_API_KEY")
        or "ollama"
    )

    resolved_model = (
        model
        or os.getenv("LLM_MODEL")
        or "qwen2.5:7b"
    )

    resolved_ignore_proxy = (
        ignore_proxy
        if ignore_proxy is not None
        else should_ignore_proxy(
            resolved_base_url
        )
    )

    return OpenAICompatibleLLMClient(
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        model=resolved_model,
        ignore_proxy=resolved_ignore_proxy,
    )


def should_ignore_proxy(
    base_url: str,
) -> bool:
    env_value = os.getenv("LLM_IGNORE_PROXY")

    if env_value is not None:
        return env_value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

    host = urlparse(base_url).hostname

    if host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        return True

    if not host:
        return False

    try:
        return ip_address(host).is_private
    except ValueError:
        return False


def load_env_file(
    path: str = ".env",
) -> None:
    env_path = Path(path)

    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith("#")
            or "=" not in stripped
        ):
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()

        if key in os.environ:
            continue

        os.environ[key] = value.strip().strip("\"'")
