from dataclasses import dataclass

from app.core.config import settings


class AgentConfigurationError(ValueError):
    """Raised when the selected agent provider is not configured."""


@dataclass(frozen=True)
class AgentProvider:
    name: str
    api_key: str
    base_url: str


PROVIDER_ALIASES = {
    "volc": "ark",
    "volcengine": "ark",
    "doubao": "ark",
    "qwen": "dashscope",
    "glm": "zhipu",
}


def _provider_credentials(provider: str) -> tuple[str, str]:
    mapping = {
        "ark": (settings.ark_api_key, settings.ark_base_url),
        "zhipu": (settings.zhipu_api_key, settings.zhipu_base_url),
        "dashscope": (settings.dashscope_api_key, settings.dashscope_base_url),
        "deepseek": (settings.deepseek_api_key, settings.deepseek_base_url),
        "openai": (settings.openai_api_key, settings.openai_base_url),
        "openrouter": (
            settings.openrouter_api_key,
            settings.openrouter_base_url,
        ),
        "siliconflow": (
            settings.siliconflow_api_key,
            settings.siliconflow_base_url,
        ),
    }
    if provider not in mapping:
        supported = ", ".join(sorted(mapping))
        raise AgentConfigurationError(
            f"不支持的 Agent 模型供应商 {provider!r}，可选值：{supported}"
        )
    return mapping[provider]


def resolve_agent_provider() -> AgentProvider:
    provider = settings.agent_provider.strip().lower()
    provider = PROVIDER_ALIASES.get(provider, provider)
    provider_key, provider_url = _provider_credentials(provider)
    api_key = (settings.agent_api_key or provider_key).strip()
    base_url = (settings.agent_base_url or provider_url).strip().rstrip("/")
    if not api_key:
        raise AgentConfigurationError(
            f"Agent 供应商 {provider} 未配置 API Key"
        )
    if not base_url:
        raise AgentConfigurationError(
            f"Agent 供应商 {provider} 未配置 Base URL"
        )
    return AgentProvider(name=provider, api_key=api_key, base_url=base_url)

