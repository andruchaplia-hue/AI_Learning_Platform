from typing import Any, Literal
from pydantic import BaseModel, Field


class CodeGenerationRequest(BaseModel):
    """Request DTO for code generation and refactoring."""

    prompt: str = Field(..., min_length=3, description="Natural language requirements or edit instructions.")
    model_mode: Literal["base", "tuned"] = Field(default="base", description="Model mode selection: 'base' or 'tuned'.")
    target_filename: str | None = Field(default=None, description="Optional target file name for contextual diff.")
    target_file_content: str | None = Field(default=None, description="Optional existing file content for contextual refactor.")
    session_id: str | None = Field(default="default_session", description="Optional session tracking ID.")


class CodeGenerationResponse(BaseModel):
    """Response DTO containing generated code, review, suggestions, and diff."""

    status: str = Field(default="success")
    generated_code: str
    diff: str | None = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    review_comments: str
    suggestions: list[str] = Field(default_factory=list)
    model_used: str
    execution_time_sec: float
    is_tuned_fallback: bool = False


class DatasetEntry(BaseModel):
    """Single training pair item in the fine-tuning dataset."""

    id: int
    user_prompt: str
    expected_code: str


class DatasetListResponse(BaseModel):
    """List response for dataset inspector UI."""

    status: str = Field(default="success")
    total_entries: int
    entries: list[DatasetEntry]


class AddDatasetEntryRequest(BaseModel):
    """Request DTO to add a new pair to fine-tuning dataset."""

    user_prompt: str = Field(..., min_length=5, description="User requirement prompt.")
    expected_code: str = Field(..., min_length=5, description="Expected Python / target code solution.")


class FineTuneJobResponse(BaseModel):
    """Response DTO for fine-tuning status / trigger API."""

    status: str = Field(default="success")
    message: str
    dataset_size: int
    tuned_model_id: str
