# 🎯 Use Case 5: Personalized Content Studio — Specification & Implementation

## 1. Overview
**Personalized Content Studio** is the flagship use case and culmination of the AI Learning Platform, synthesizing capabilities developed across Use Cases 1–4:
- **LangChain Agent Framework** & Structured LCEL Chains (UC 1 & UC 4)
- **Conversational Memory & Semantic Vector Search** (UC 2 — SQLite + ChromaDB RAG for personal writing samples)
- **Multimodal Vision Understanding** (UC 3 — contextual scene extraction)
- **Multi-Step Pipeline & Quality Review** (UC 4 — Planner → Generator → Reviewer)
- **Dedicated Authentication & User Profile Management** (JWT + SQLite repository)

> [!NOTE]
> Authentication is strictly enforced for **Use Case 5** endpoints (`/api/v1/auth`, `/api/v1/profile`, `/api/v1/content-generation`, `/api/v1/content-generation/examples`). Use Cases 1–4 remain open and unauthenticated.

## 2. Supported Content Formats & Templates

The platform supports 4 distinct content formats, with dedicated modular prompt templates located in `backend/use_cases/use_case_5_content_gen/prompts/formats/`:

| Format Key | Display Name | Template File | Style & Framing Focus |
| :--- | :--- | :--- | :--- |
| `blog_post` | **Blog Post** | `blog_post.txt` | In-depth technical/thought leadership narrative, structured `##` headings, code snippets, takeaways |
| `linkedin_post` | **LinkedIn Post** | `linkedin_post.txt` | High-impact hook, bulleted insights, career/industry takeaways, 3–5 relevant hashtags, engaging CTA |
| `marketing_email` | **Marketing Email** | `marketing_email.txt` | Compelling subject line options, personalized greeting, value proposition, scannable body, clear CTA button |
| `social_media_post` | **Social Media Post** | `social_media_post.txt` | Punchy viral hook, conversational tone, emojis, concise message, 2–3 hashtags, discussion starter |

---

## 3. Technology Stack & Layering
- **Framework**: LangChain Agent Framework (`FrameworkType.LANGCHAIN`) via `LLMGateway`
- **LLM Provider**: Gemini Provider via `LLMGateway` (with fallback `MockProvider`)
- **Authentication**: JWT Auth Manager (`backend/infrastructure/auth/jwt_manager.py`, `password_hasher.py`)
- **Profile & Account Persistence**: SQLite Database (`backend/infrastructure/auth/user_repository.py` in `data/memory.db`)
- **Personalization Vector RAG**: ChromaDB (`data/vectorstore/chroma`) + `EmbeddingService` (isolated per-user collections `user_personalization_{user_id}`)
- **Vision & Image Processing**: Unified `ImageService` (`backend/infrastructure/storage/image_service.py`) for validation, proportional resizing (max 2048px), and user-isolated file storage (`data/uploads/{user_id}/`).

---

## 4. Architecture & Endpoints

### 4.1. Controllers (Thin API Proxies)
- `backend/api/routes/auth.py`: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`
- `backend/api/routes/profile.py`: `/api/v1/profile` (`GET`, `PUT`)
- `backend/api/routes/content_generation.py`:
  - `POST /api/v1/content-generation`: Generate personalized content (multipart form: optional image + payload JSON)
  - `GET /api/v1/content-generation/history`: Get user generation history
  - `POST /api/v1/content-generation/feedback`: Rate output (1–5 stars) and optionally save to personal dataset
  - `POST /api/v1/content-generation/submit`: Finalize draft and publish to Author Wall
- `backend/api/routes/content_examples.py`:
  - `GET /api/v1/content-generation/examples`: List personal writing samples
  - `POST /api/v1/content-generation/examples`: Create new writing sample (auto-embedded in ChromaDB)
  - `DELETE /api/v1/content-generation/examples/{sample_id}`: Remove sample
  - `GET /api/v1/content-generation/examples/export/jsonl`: Export dataset to JSONL format

### 4.2. Prompt Hierarchy & Pipeline Modules
```text
backend/use_cases/use_case_5_content_gen/
├── __init__.py
├── models.py              # DTOs: GenerateContentRequest, GenerateContentResponse, UserProfile, etc.
├── service.py             # ContentGenerationService domain orchestrator
├── agent.py               # ContentAgentPipeline (LCEL multi-step workflow)
├── dataset_service.py     # PersonalizationDatasetService (ChromaDB RAG & JSONL exporter)
└── prompts/
    ├── planner_prompt.txt          # Strategist: outlines, messaging points, audience hooks
    ├── generator_prompt.txt        # Writer: draft composition, voice calibration, few-shot injection
    ├── vision_extractor_prompt.txt # Vision: extracts structured scene facts from uploaded images
    └── formats/                    # Modular format templates
        ├── blog_post.txt
        ├── linkedin_post.txt
        ├── marketing_email.txt
        └── social_media_post.txt
```

---

## 5. Multi-Step Lean Agent Workflow & Author Wall

1. **Context Assembly (Deterministic / RAG)**: Fetch user profile (tone, audience, style notes) and query ChromaDB for top-2 matching liked writing samples.
2. **Conditional Vision Processing & Extractor**: If an image is uploaded, validate and downscale via `ImageService`, persist in `data/uploads/{user_id}/`, and extract factual scene observations using Gemini Vision.
3. **Content Strategist & Planner**: Synthesize profile parameters, exemplars, and visual context to construct an outline, key messaging, and audience hooks.
4. **Personalized Generator & Reviewer**: Compose the final tailored markdown draft formatted according to the selected format template.
5. **Memory, Feedback & Author Wall**:
   - Rate generations (1–5 stars); 5-star ratings automatically sync to personal ChromaDB RAG.
   - User submits post via **«🚀 Submit Post»**, marking the draft finalized and publishing it to the interactive **Author Wall** with format badges, author metadata, and thumbnail preview.

---

## 6. Verification & Test Results
- **Automated Tests**: Covered in `tests/test_use_case_5.py` (PasswordHasher, JWTManager, UserRepository, PersonalizationDatasetService, ContentGenerationService, Vision Sanitization, Image Persistence, API Endpoints, Auth Guard).
- **Test Pass Rate**: 100% (12/12 Use Case 5 tests passing in local and live Docker containers; 53/53 tests across all platform modules).

