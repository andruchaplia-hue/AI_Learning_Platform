from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda

from backend.domain.exceptions import ConfigurationError


def load_prompt_template() -> str:
    """Load image caption prompt template from file."""
    prompt_file = Path(__file__).resolve().parent / "prompts" / "image_caption_prompt.txt"
    if not prompt_file.exists():
        raise ConfigurationError(f"Prompt template file not found at {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


def format_multimodal_message(inputs: dict[str, Any]) -> list[Any]:
    """Format prompt instructions and base64 image into LangChain message structure."""
    prompt_text = inputs.get("prompt") or load_prompt_template()
    base64_str = inputs["image_base64"]
    mime_type = inputs.get("mime_type", "image/jpeg")

    messages = [
        SystemMessage(content="You are an expert AI vision assistant. Describe images accurately."),
        HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_str}"},
                },
            ]
        ),
    ]
    return messages


def create_image_caption_chain(llm: BaseChatModel) -> Runnable[dict[str, Any], str]:
    """Create LCEL vision chain (formatter | llm | parser).

    Args:
        llm: Initialized BaseChatModel instance.

    Returns:
        LCEL Runnable chain.
    """
    formatter = RunnableLambda(format_multimodal_message)
    parser = StrOutputParser()

    chain = formatter | llm | parser
    return chain
