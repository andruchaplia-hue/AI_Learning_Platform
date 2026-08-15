from pydantic import BaseModel, Field


class ImageCaptionResponse(BaseModel):
    """Response model for image captioning containing generated texts and image processing metadata."""

    short_caption: str = Field(
        ...,
        description="Single sentence caption summarizing the image content",
    )
    full_description: str = Field(
        ...,
        description="Detailed multi-paragraph or multi-sentence scene description",
    )
    action_description: str = Field(
        ...,
        description="Detailed description of actions, activities, and interactions occurring in the image",
    )

    execution_time_sec: float = Field(
        ...,
        description="Execution time in seconds",
    )
    resized: bool = Field(
        default=False,
        description="Indicates whether the image was auto-downscaled",
    )
    original_resolution: str | None = Field(
        default=None,
        description="Original width x height resolution string, e.g. '4032x3024'",
    )
    processed_resolution: str | None = Field(
        default=None,
        description="Processed width x height resolution string, e.g. '2048x1536'",
    )
    image_id: str = Field(
        ...,
        description="Unique stored file identifier",
    )
