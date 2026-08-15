from typing import Any
from pydantic import BaseModel, Field

from backend.domain.models.faq import FAQItem


class RetrievedFAQ(FAQItem):
    """FAQ item retrieved with similarity match score."""
    score: float = Field(..., description="Cosine similarity score (0.0 - 1.0)")



class FAQQueryRequest(BaseModel):
    """Input payload for FAQ chatbot query."""

    query: str = Field(
        ...,
        description="User question or query text",
        examples=["How do I reset my password?"],
    )
    session_id: str | None = Field(
        default="default_session",
        description="Unique session identifier for chat history memory",
        examples=["session_123"],
    )
    user_friendly: bool = Field(
        default=True,
        description="If True, synthesizes a smooth LLM answer. If False, returns direct raw FAQ text.",
        examples=[True],
    )
    sk_filtering: bool = Field(
        default=True,
        description="If True, filters candidate FAQs using Semantic Kernel Agent selection. If False, bypasses selection filter.",
        examples=[True],
    )


class FAQRawTextRequest(BaseModel):
    """DTO for submitting raw text to parse into FAQ entries."""
    raw_text: str = Field(..., min_length=5, description="Unstructured text containing Q&A pairs")



class QueryDecompositionResult(BaseModel):
    """Output model for query decomposition analysis."""
    original_query: str
    decomposed_questions: list[str] = Field(default_factory=list)
    is_compound: bool = False


class CoverageAnalysisResult(BaseModel):
    """Evaluation of how well retrieved FAQs cover decomposed questions."""
    coverage_score: float = Field(..., ge=0.0, le=1.0)
    covered_questions: list[str] = Field(default_factory=list)
    missing_questions: list[str] = Field(default_factory=list)


class ExecutionDetails(BaseModel):
    """Metadata and debugging metrics for UI inspection."""
    decomposed_queries: list[str] = Field(default_factory=list)
    retrieved_faqs: list[RetrievedFAQ] = Field(default_factory=list)
    max_similarity_score: float = 0.0
    coverage_score: float = 0.0
    missing_questions: list[str] = Field(default_factory=list)
    is_fallback: bool = False
    sk_filtering: bool = True
    selected_faq_ids: list[int] = Field(default_factory=list)
    decomposer_fallback: bool = False
    coverage_fallback: bool = False
    pipeline_error: str | None = None
    execution_time_seconds: float = 0.0



class FAQQueryResponse(BaseModel):
    """Response DTO for client."""
    status: str = Field(default="success")
    answer: str
    found: bool = True
    session_id: str
    execution_details: ExecutionDetails | None = None
