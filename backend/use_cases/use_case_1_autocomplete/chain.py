from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from backend.domain.exceptions import ConfigurationError


def load_prompt_template() -> str:
    """Load text prompt template from file."""
    prompt_file = Path(__file__).resolve().parent / "prompts" / "autocomplete_prompt.txt"
    if not prompt_file.exists():
        raise ConfigurationError(f"Prompt template file not found at {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


def create_autocomplete_chain(llm: BaseChatModel) -> Runnable[dict[str, Any], str]:
    """Create LCEL autocomplete chain (prompt | llm | parser).

    Args:
        llm: Initialized BaseChatModel instance.

    Returns:
        LCEL Runnable chain.
    """
    raw_prompt = load_prompt_template()
    prompt = ChatPromptTemplate.from_template(raw_prompt)
    parser = StrOutputParser()

    # LCEL composition using pipe operator
    chain = prompt | llm | parser
    return chain
