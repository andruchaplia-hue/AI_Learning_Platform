from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from backend.infrastructure.llm.providers.base_provider import BaseProvider, FrameworkType


class MockChatModel(BaseChatModel):
    """Custom LangChain BaseChatModel implementation for testing without live API keys."""

    model_name: str = "mock-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        full_text = str([m.content for m in messages]) if messages else ""
        content = self._generate_completion(full_text)
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    def _generate_completion(self, text: str) -> str:
        lower_text = text.lower()
        if "editorial strategy" in lower_text or "planner" in lower_text or "content strategist" in lower_text or "strategic plan" in lower_text:
            return (
                "**1. Core Value Proposition**: Unified enterprise generative AI platform with clean architecture.\n"
                "**2. Key Sections**:\n- Architecture Overview\n- Clean Layer Separation\n- Personalization Vector RAG\n"
                "**3. Tone Calibration**: Professional, clear, and inspiring.\n"
                "**4. Call to Action**: Check out the project documentation and demo!"
            )
        elif "content specification" in lower_text or "personalized content writer" in lower_text or "author persona" in lower_text or "target content format" in lower_text:
            return (
                "# 🚀 Building Unified Generative AI Platforms\n\n"
                "Developing production-grade AI systems requires robust architectural discipline.\n\n"
                "### Key Highlights:\n"
                "- **Layered Architecture**: Decoupled Streamlit UI and FastAPI endpoints.\n"
                "- **Multi-Agent Pipelines**: LangChain LCEL chains combined with Semantic Kernel agents.\n"
                "- **Personalized RAG**: In-context few-shot grounding via ChromaDB.\n\n"
                "Explore the open repository and build your AI modules today!"
            )
        elif "short_caption" in lower_text or "image" in lower_text or "caption" in lower_text or "visual" in lower_text:
            return (
                '{"short_caption": "A scenic view of a city street with parked bicycles under a clear blue sky.", '
                '"full_description": "The image displays a quiet city street in an urban neighborhood. A vintage bicycle is parked near a brick sidewalk, with architectural buildings visible under a clear, bright sky.", '
                '"action_description": "A person is walking along the sidewalk past the parked bicycle, carrying a backpack and enjoying a morning walk."}'
            )
        elif "artificial intelligence" in lower_text:
            return "is rapidly transforming software engineering by automating routine tasks, improving developer productivity, and enabling intelligent system automation."
        elif "machine learning" in lower_text:
            return "is a subset of AI focusing on algorithms that learn patterns directly from data to make accurate predictions and automated decisions."
        elif "python" in lower_text:
            return "is an exceptionally readable, powerful programming language widely celebrated for data science, web services, and machine learning workflows."
        else:
            return "continues to play a pivotal role in modern technology, offering valuable insights and scalable solutions across diverse domains."


class MockProvider(BaseProvider):
    """Mock LLM Provider implementing BaseProvider for multiple frameworks."""

    def __init__(self, model_name: str = "mock-model") -> None:
        self._llm = MockChatModel(model_name=model_name)

    def get_llm(self, framework: FrameworkType = FrameworkType.LANGCHAIN) -> Any:
        if framework == FrameworkType.LANGCHAIN:
            return self._llm
        elif framework == FrameworkType.SEMANTIC_KERNEL:
            try:
                import semantic_kernel as sk
                from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
                from semantic_kernel.contents import ChatMessageContent, StreamingChatMessageContent, AuthorRole
                from collections.abc import AsyncGenerator

                class MockChatCompletion(ChatCompletionClientBase):
                    ai_model_id: str = "mock-model"

                    async def _inner_get_chat_message_contents(
                        self,
                        chat_history: Any,
                        settings: Any,
                    ) -> list[ChatMessageContent]:
                        last_msg = chat_history.messages[-1].content if chat_history.messages else ""
                        content = self._generate_completion(str(last_msg))
                        return [
                            ChatMessageContent(
                                role=AuthorRole.ASSISTANT,
                                content=content,
                                ai_model_id=self.ai_model_id,
                            )
                        ]

                    async def _inner_get_streaming_chat_message_contents(
                        self,
                        chat_history: Any,
                        settings: Any,
                    ) -> AsyncGenerator[list[StreamingChatMessageContent], Any]:
                        last_msg = chat_history.messages[-1].content if chat_history.messages else ""
                        content = self._generate_completion(str(last_msg))
                        yield [
                            StreamingChatMessageContent(
                                role=AuthorRole.ASSISTANT,
                                content=content,
                                ai_model_id=self.ai_model_id,
                                choice_index=0,
                            )
                        ]

                    def _generate_completion(self, text: str) -> str:
                        lower_text = text.lower()
                        if "artificial intelligence" in lower_text:
                            return "is rapidly transforming software engineering by automating routine tasks, improving developer productivity, and enabling intelligent system automation."
                        elif "machine learning" in lower_text:
                            return "is a subset of AI focusing on algorithms that learn patterns directly from data to make accurate predictions and automated decisions."
                        elif "python" in lower_text:
                            return "is an exceptionally readable, powerful programming language widely celebrated for data science, web services, and machine learning workflows."
                        elif "decomposition" in lower_text or "decompose" in lower_text:
                            return '{"questions": ["How do I reset my password?"]}'
                        elif "synthesis" in lower_text or "faq" in lower_text or "answer" in lower_text:
                            return "Click forgot password."
                        elif "exec_analyzer" in lower_text or "software requirements analyzer" in lower_text:
                            return '{"language": "python", "framework": "fastapi", "key_functions": ["main"], "constraints": ["PEP8"]}'
                        elif "exec_reviewer" in lower_text or "senior code reviewer" in lower_text:
                            return "**Code Review Audit Report**:\n- **Structure**: Clean function layout and PEP8 compliance.\n- **Security**: Safe parameter handling."
                        elif "exec_advisor" in lower_text or "software improvement advisor" in lower_text:
                            return "- Add type hints for input arguments.\n- Add docstrings explaining function behavior.\n- Include unit test coverage."
                        elif "exec_generator" in lower_text or "ai code generator" in lower_text or "generate code" in lower_text or "code snippet" in lower_text:
                            if "castle" in lower_text or "hello world" in lower_text:
                                return (
                                    "def print_castle():\n"
                                    "    \"\"\"Print a simple castle using 'Hello World!' bricks.\"\"\"\n"
                                    "    brick = '[Hello World!]'\n"
                                    "    print('      /\\\\           /\\\\      ')\n"
                                    "    print(f'   {brick}   {brick}')\n"
                                    "    print(f'   {brick}{brick}{brick}')\n"
                                    "    print(f'   {brick}   |  |   {brick}')\n"
                                    "    print(f'   {brick}{brick}{brick}')\n\n"
                                    "if __name__ == '__main__':\n"
                                    "    print_castle()\n"
                                )
                            elif "fastapi" in lower_text or "health" in lower_text:
                                return (
                                    "from fastapi import APIRouter\n"
                                    "from datetime import datetime\n\n"
                                    "router = APIRouter()\n"
                                    "start_time = datetime.utcnow()\n\n"
                                    "@router.get('/health')\n"
                                    "async def health():\n"
                                    "    return {'status': 'ok', 'uptime_sec': (datetime.utcnow() - start_time).total_seconds()}\n"
                                )
                            else:
                                return (
                                    "def execute_task():\n"
                                    "    \"\"\"Implementation generated based on requirement.\"\"\"\n"
                                    "    print('Executing code generation task...')\n"
                                    "    return {'status': 'success'}\n"
                                )
                        else:
                            return "Mocked response for prompt: " + text[:50]


                kernel = sk.Kernel()
                kernel.add_service(
                    MockChatCompletion(
                        service_id="mock-chat-completion",
                        ai_model_id=self._llm.model_name
                    )
                )
                return kernel
            except ImportError:
                return self._llm
        return self._llm


