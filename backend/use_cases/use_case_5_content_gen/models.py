from typing import Any
from pydantic import BaseModel, Field


# Auth Models
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str


class DevLoginRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=100, description="Email or username for fast dev auth")


class DevUserItem(BaseModel):
    id: str
    username: str
    email: str
    profession: str = ""
    industry: str = ""
    writing_tone: str = ""
    created_at: str = ""


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str


# Profile Models
class UserProfileDTO(BaseModel):
    user_id: str
    username: str
    email: str
    profession: str = ""
    industry: str = ""
    age: int = 30
    gender: str = "Male"
    preferred_language: str = "English"
    hobbies: list[str] = Field(default_factory=list)
    bio: str = ""
    updated_at: str = ""


class UserProfileUpdateRequest(BaseModel):
    profession: str = ""
    industry: str = ""
    age: int = 30
    gender: str = "Male"
    preferred_language: str = "English"
    hobbies: list[str] = Field(default_factory=list)
    bio: str = ""


# Content Generation Models
class ContentGenerationRequest(BaseModel):
    content_type: str = Field(..., description="blog_post | linkedin_post | marketing_email")
    prompt: str = Field(..., min_length=5, max_length=5000)
    image_base64: str | None = None
    image_mime_type: str | None = None
    use_personalization_dataset: bool = True


class ContentGenerationResponse(BaseModel):
    id: str
    content_type: str
    prompt: str
    generated_content: str
    plan_breakdown: str
    image_path: str = ""
    decision_chain: list[dict[str, Any]] = Field(default_factory=list)
    visual_context_used: bool
    few_shot_examples_count: int
    execution_time: float
    created_at: str


class ContentHistoryItem(BaseModel):
    id: str
    user_id: str
    content_type: str
    prompt: str
    image_path: str = ""
    generated_content: str
    plan_breakdown: str = ""
    rating: int = 0
    saved_to_dataset: bool = False
    created_at: str


class ContentSubmitRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    content_type: str = Field(...)
    generated_content: str = Field(..., min_length=1)
    plan_breakdown: str = ""
    image_path: str = ""
    rating: int = Field(5, ge=1, le=5)
    save_to_dataset: bool = False


class ContentFeedbackRequest(BaseModel):
    history_id: str
    rating: int = Field(..., ge=1, le=5)
    save_to_dataset: bool = False


# Writing Sample & Personalization Dataset Models
class WritingSampleCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    content_type: str = Field(..., description="blog_post | linkedin_post | marketing_email | other")
    content: str = Field(..., min_length=10)
    tags: list[str] = Field(default_factory=list)


class WritingSampleResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content_type: str
    content: str
    tags: list[str]
    created_at: str


class WritingSampleListResponse(BaseModel):
    samples: list[WritingSampleResponse]
    total_count: int
