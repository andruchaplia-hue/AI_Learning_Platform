from enum import Enum

from pydantic import BaseModel, Field


class CompletionMode(str, Enum):
    """Completion mode for text autocompletion."""

    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


class AutocompleteRequest(BaseModel):
    """Input payload for text completion request."""

    text: str = Field(
        ...,
        description="Initial text fragment to complete",
        examples=["Artificial Intelligence is"],
    )
    mode: CompletionMode = Field(
        default=CompletionMode.SENTENCE,
        description="Completion mode: 'sentence' or 'paragraph'",
        examples=[CompletionMode.SENTENCE, CompletionMode.PARAGRAPH],
    )


class AutocompleteResponse(BaseModel):
    """Output response containing completion results and execution metrics."""

    completion: str = Field(
        ...,
        description="Main generated text completion",
    )
    completions: list[str] = Field(
        default_factory=list,
        description="List of parsed completion options if multiple were generated",
    )
    execution_time_sec: float = Field(
        ...,
        description="Time taken to run the completion pipeline in seconds",
    )
