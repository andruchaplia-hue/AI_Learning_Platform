# 🏛️ AI Learning Platform — Technical Architecture Specification

## 1. Executive Overview

The **AI Learning Platform** is an enterprise-ready, modular architecture designed to host 5 generative and agentic AI use cases on top of shared core infrastructure. It enforces **Clean Architecture**, **Dependency Inversion**, **Config-First Management**, and a unified **Multi-Framework LLM Gateway** supporting both **LangChain** and **Semantic Kernel**.

---

## 2. Layered Architecture

The platform strictly enforces a clean 4-layer Clean Architecture boundary:

```text
┌────────────────────────────────────────────────────────┐
│                   UI Layer (Streamlit)                 │
│  Home.py + pages/ + components/ + services/api_client  │
└───────────────────────────┬────────────────────────────┘
                            │ REST HTTP (JSON)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                  │
│  app.py + routes/ (auth, profile, autocomplete, ...)   │
└───────────────────────────┬────────────────────────────┘
                            │ Domain Calls / DTO
                            ▼
┌────────────────────────────────────────────────────────┐
│             Use Cases & Domain Layer                   │
│  use_cases/use_case_X/ (services, agents, prompts)     │
│  domain/ (models, validators, exceptions)              │
└───────────────────────────┬────────────────────────────┘
                            │ Factory & Storage Access
                            ▼
┌────────────────────────────────────────────────────────┐
│            Infrastructure & Gateway Layer              │
│  llm/gateway.py (Google / Mock) + memory/ + storage/   │
│  auth/ (JWT, bcrypt, SQLite) + config/ (AppSettings)   │
└────────────────────────────────────────────────────────┘
```

### Layer Descriptions:
1. **UI Layer (Streamlit)**: Houses `Home.py`, case pages in `pages/`, reusable widgets, and themes. Interacts with the backend solely via the `APIClient` (`frontend/services/api_client.py`). **No direct LangChain/Semantic Kernel imports, no API key loading, no direct LLM calling.**
2. **API Layer (FastAPI)**: Serves thin routing controllers (`routes/`) that parse and validate HTTP requests using Pydantic DTO models and proxy them immediately to the Use Case services.
3. **Use Cases Layer (Business Logic)**: Located in `backend/use_cases/` and `backend/domain/`. Each use case resides in its own isolated directory containing request/response models, service orchestration, prompts, LCEL chains, and Semantic Kernel agents.
4. **Infrastructure & Gateway Layer**: Abstracts LLM provider initialization (Google Gemini, Mock) via `LLMGateway`, vector search (`ChromaStore`), persistence (`UserRepository`, `FAQRepository`), media processing (`ImageService`), security (`JWTManager`), and configuration (`AppSettings`).


---

## 3. Core Architectural Patterns

### 3.1. Multi-Framework LLM Gateway
The gateway abstracts LLM provider initialization (Google Gemini, Mock) and supplies framework-native clients on demand via `FrameworkType`:

```python
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base_provider import FrameworkType

# Request LangChain ChatModel (BaseChatModel)
langchain_llm = LLMGateway.get_llm(settings, framework=FrameworkType.LANGCHAIN)

# Request Semantic Kernel (sk.Kernel)
sk_kernel = LLMGateway.get_llm(settings, framework=FrameworkType.SEMANTIC_KERNEL)
```

### 3.2. Global Error Handling Schema
Raw Python stack trace leakage is prevented by global FastAPI handlers mapping custom exceptions to clean JSON payloads:

| Exception Type | HTTP Code | Status Field | Description |
| :--- | :--- | :--- | :--- |
| `ValidationError` | `400 Bad Request` | `"error"` | Input text fails validation rules (length, format, size) |
| `AuthenticationError` | `401 Unauthorized` | `"error"` | Invalid credentials, expired token, or unauthorized access |
| `ProviderError` | `502 Bad Gateway` | `"error"` | LLM gateway/provider call failed (timeout, quota, credentials) |
| `ConfigurationError` | `500 Internal Error` | `"error"` | Configuration file missing, invalid or corrupt |
| `InternalError` | `500 Internal Error` | `"error"` | General unhandled backend runtime issues |

Standard JSON Error Format:
```json
{
  "status": "error",
  "message": "Human-readable error description"
}
```

---

## 4. Platform Directory Layout

```text
ai-learning-platform/
├── frontend/                   # Streamlit Multi-Page UI
│   ├── Home.py                 # Platform Homepage & Dashboard
│   ├── pages/                  # Use Case Pages (01_Autocomplete.py ... 05_Content_Generator.py)
│   ├── components/             # Reusable UI widgets (chat_component, image_uploader, code_editor, common_widgets)
│   └── services/               # API Client (api_client.py)
│
├── backend/                    # Core Backend Service
│   ├── api/                    # FastAPI App & APIRouters
│   │   ├── app.py              # Main FastAPI application & exception handlers
│   │   └── routes/             # Thin APIRouter controllers per use case
│   │       ├── auth.py         # Authentication routes (register, login, me)
│   │       ├── profile.py      # Profile management routes
│   │       ├── autocomplete.py # UC1 Autocomplete route
│   │       ├── faq_routes.py   # UC2 FAQ Chatbot routes
│   │       ├── image_caption.py # UC3 Image captioning routes
│   │       ├── code_generation.py # UC4 Code generation routes
│   │       ├── content_generation.py # UC5 Content generation & feedback routes
│   │       └── content_examples.py   # UC5 Personalization dataset routes
│   ├── use_cases/              # Modular Use Case Logic
│   │   ├── use_case_1_autocomplete/    # Autocomplete LCEL chain & service
│   │   ├── use_case_2/                 # FAQ Agent + ChromaDB vector search
│   │   ├── use_case_3_image_captioning/ # Image Captioning LangChain Vision
│   │   ├── use_case_4_code_generation/ # Code Assistant sequential agent pipeline
│   │   └── use_case_5_content_gen/     # Content Studio LCEL Multi-Step Agent & RAG
│   ├── domain/                 # Shared domain logic, models, and validators
│   │   ├── exceptions.py       # Typed domain exceptions (ValidationError, ProviderError, etc.)
│   │   ├── models/             # Cross-usecase models (FAQItem, etc.)
│   │   └── validators/         # Domain text & input validators
│   └── infrastructure/         # Platform Shared Infrastructure
│       ├── auth/               # JWTManager, PasswordHasher, UserRepository (SQLite)
│       ├── config/             # Settings (pydantic-settings & config.yaml)
│       ├── llm/                # LLMGateway, GoogleProvider, MockProvider
│       ├── memory/             # SQLite Memory + ChromaDB VectorStore + EmbeddingService
│       └── storage/            # LocalStorageManager, ImageService (validation & resizing)
│
├── configs/                    # YAML Configuration files (config.yaml, logging.yaml)
├── data/                       # Database files, Vector stores, Upload directories
├── docs/                       # System Documentation & Specifications
├── docker/                     # Dockerfiles and docker-compose configurations
└── tests/                      # Automated test suite (Pytest, 53 tests)
```
