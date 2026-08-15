from backend.infrastructure.config.settings import load_settings
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType


def test_gateway_mock_provider_frameworks():
    settings = load_settings()
    settings.provider = "mock"

    langchain_llm = LLMGateway.get_llm(settings, framework=FrameworkType.LANGCHAIN)
    assert langchain_llm is not None

    sk_kernel = LLMGateway.get_llm(settings, framework=FrameworkType.SEMANTIC_KERNEL)
    assert sk_kernel is not None
