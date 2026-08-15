# 🖼️ Use Case 3: Image Captioning — Architecture & Implementation

## 1. Overview
**Image Captioning** provides multimodal vision analysis of user-uploaded images, generating descriptive short captions, detailed scene descriptions, and a separate action and activity analysis using LangChain LCEL pipelines and Google Gemini (or Mock) vision capabilities.

---

## 2. Technology Stack
- **Framework**: LangChain Vision (`ChatGoogleGenerativeAI` with multimodal image message payloads)
- **LLM Provider**: Google Gemini (`gemini-3.1-flash-lite`) / Mock Provider via `LLMGateway`
- **File Storage**: Local Storage Manager (`backend/infrastructure/storage/local_storage.py`) storing files in `data/uploads/`
- **Image Processing**: Pillow (`PIL`) for format validation, RGB color space normalization, and proportional auto-downscaling (max 2048px)

---

## 3. Architecture & Endpoints
- **Upload & Caption Endpoint**: `POST /api/v1/image-caption` (multipart form upload)
- **Retrieve Image Endpoint**: `GET /api/v1/image-caption/image/{image_id}` (serves saved/resized images)
- **Controller**: `backend/api/routes/image_caption.py`
- **Service**: `backend/use_cases/use_case_3_image_captioning/service.py`
- **UI Page**: `frontend/pages/03_Image_Captioning.py`

---

## 4. Architectural Structure

```text
backend/use_cases/use_case_3_image_captioning/
├── __init__.py
├── models.py              # ImageCaptionResponse DTO
├── service.py             # ImageCaptionService orchestrating validation, processing, and invoke
├── chain.py               # Formulates HumanMessage base64 lists and LCEL vision chain
├── validators.py          # Size (<50MB), extension, and Pillow corruption checks
├── image_processor.py     # normalizes colors and downscales to max 2048px
└── prompts/
    └── image_caption_prompt.txt  # System prompt defining JSON response structure
```

---

## 5. Data Transfer Objects (`ImageCaptionResponse`)

```python
class ImageCaptionResponse(BaseModel):
    short_caption: str           # Single sentence summary caption
    full_description: str        # Detailed scene & objects description
    action_description: str      # Detailed description of actions & activities
    execution_time_sec: float    # Pipeline processing duration in seconds
    resized: bool                # True if the image was auto-downscaled
    original_resolution: str     # Width x Height string (e.g. '4032x3024')
    processed_resolution: str    # Width x Height string (e.g. '2048x1536')
    image_id: str                # Unique identifier in local storage
```

---

## 6. Image Downscaling & Warnings
* If either the width or height of the uploaded image exceeds **2048px**, the backend downscales it proportionally while maintaining the aspect ratio.
* The Streamlit UI displays a notification if downscaling occurred:
  `⚠️ For resource optimization, the image was automatically resized from {original} to {processed}.`
* The downscaled image is cached on disk, and the Streamlit UI displays the processed version.
