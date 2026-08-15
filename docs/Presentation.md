# 🎓 Project Presentation: AI Learning Platform
> **Document Purpose:** Express architectural overview, structure, and capabilities of the platform for reviewers and engineers.

---

## 📌 1. Concept of AI Learning Platform

### From 5 Disconnected Apps to a Unified AI Platform
Instead of building 5 isolated independent applications, all educational use cases are unified on top of a single **AI Learning Platform**.

- **Zero Code Duplication**: Unified REST API server (FastAPI), unified UI dashboard (Streamlit Multi-page), unified Docker container, and shared logging.
- **Unified Tech Stack**: Combining the capabilities of **LangChain LCEL** and **Semantic Kernel** within a cohesive infrastructure.

| Use Case | Status | Tech Stack | Architectural Highlights |
| :--- | :---: | :--- | :--- |
| **UC1: Text Autocomplete** | ✅ Ready | LangChain LCEL, Gemini | Programmatic option parsing, preamble handling, `CompletionMode` Enum |
| **UC2: FAQ Chatbot** | ✅ Ready | Semantic Kernel, ChromaDB, SQLite Memory | RAG plugins, strict rejection on zero coverage, `User-Friendly` / `Direct Raw` modes |
| **UC3: Image Captioning** | ✅ Ready | LangChain Vision, Gemini, Pillow | Multimodal image scene understanding, short & detailed captions, `ImageService`, auto-downscaling |
| **UC4: Code Generation** | ✅ Ready | Semantic Kernel Agents, RAG Few-Shot | 4-plugin SK pipeline, RAG Few-Shot domain adaptation, Visual Diff Engine |
| **UC5: Content Generator** | ✅ Ready | LangChain LCEL, JWT Auth, Vector RAG | 4 Content Types, Multi-step agent (Planner → Generator → Reviewer), JWT Auth, Personal ChromaDB RAG, Vision Context, Author Wall & Media Cards |

---

## 🏛️ 2. Architectural & Engineering Decisions

- **Strict Layer Isolation (Clean Architecture)**: The UI layer (`frontend/`) contains zero direct LLM SDK imports or API key access, communicating strictly via `APIClient`. FastAPI controllers in `backend/api/routes/` are thin proxies (~25 lines), while all business logic is encapsulated in `backend/use_cases/`.
- **Modern LangChain Standards (LCEL)**: Chains are composed using the pipe syntax `prompt | llm | parser`, asynchronous execution is standard via `.ainvoke()`, and legacy chain classes are excluded.
- **Multi-Framework LLM Gateway**: A centralized gateway managing API keys, model routing, and generation parameters, supplying the appropriate interface (`BaseChatModel` for LangChain or `sk.Kernel` for Semantic Kernel).
- **Strict Error Handling Schema**: Complete elimination of unhandled Python stack traces. All errors are serialized into a standard JSON schema `{ "status": "error", "message": "..." }` using custom domain exceptions (`ValidationError`, `AuthenticationError`, `ProviderError`, `ConfigurationError`, `InternalError`).
- **Autonomous Dev Mode**: Seamless offline debugging and testing support with `MockProvider` without requiring external paid API keys.

---

## 📂 3. Physical Directory Structure

```text
ai-learning-platform/
├── frontend/                   # Streamlit Multi-Page UI
│   ├── Home.py                 # Platform Homepage & Dashboard
│   ├── pages/                  # Use Case Pages (01–05)
│   ├── components/             # Reusable UI widgets
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
│   │   ├── use_case_1_autocomplete/  # LangChain LCEL chain & service
│   │   ├── use_case_2/               # SK FAQ Agent + ChromaDB RAG
│   │   ├── use_case_3_image_captioning/ # LangChain Multimodal Vision & ImageService
│   │   ├── use_case_4_code_generation/  # SK Multi-agent Code Generation
│   │   └── use_case_5_content_gen/      # LangChain LCEL Content Studio & Personalization RAG
│   ├── frameworks/             # Adapters for LangChain and Semantic Kernel
│   └── infrastructure/         # Platform Infrastructure
│       ├── auth/               # JWTManager, PasswordHasher, UserRepository (SQLite)
│       ├── config/             # Settings (pydantic-settings & config.yaml)
│       ├── llm/                # LLMGateway, GoogleProvider, MockProvider
│       ├── memory/             # SQLite Memory + ChromaDB VectorStore + EmbeddingService
│       └── storage/            # LocalStorageManager, ImageService
│
├── configs/                    # YAML Configuration (config.yaml, logging.yaml)
├── docs/                       # System Documentation & Specifications
├── docker/                     # Dockerfiles and Docker Compose manifests
└── tests/                      # Automated Test Suite (53 tests, 100% pass)
```

---

## 🚀 4. Product Capabilities & Features by Use Case

> [!NOTE]
> **Current Platform Status:** All 5 modules (**UC1–UC5**) are fully implemented, covered by 53 automated tests (100% pass rate), and verified in Docker.

### 📝 UC1: Text Completion & Autocomplete Studio
* **Dual Completion Modes**: Instant switching between `sentence` (inline phrase continuation) and `paragraph` (rich multi-sentence text expansion).
* **Sampling & Creativity Controls**: Real-time adjustment of temperature and max tokens for deterministic vs. creative completions.
* **Intelligent Output Sanitization**: Programmatic stripping of AI prefixes, option labels, and conversational filler to return clean ready-to-use text.
* **Performance Telemetry**: Live measurement of execution latency (seconds) and character/word statistics.

### 💬 UC2: Intelligent FAQ Support Assistant
* **Query Decomposition**: Automatically breaks down compound inquiries (*e.g., "How do I reset my password and what payment methods are accepted?"*) into independent sub-questions via `QueryDecomposerPlugin`.
* **Hybrid Semantic Retrieval**: ChromaDB vector search with cosine distance scoring combined with category-based filtering.
* **Anti-Hallucination Guardrail**: Calculates coverage score across FAQ knowledge base; safely rejects out-of-scope queries (`coverage == 0.0`) with polite fallback suggestions.
* **Dual Response Views**: Toggle between `✨ User-Friendly` (synthesized conversational explanation) and `📌 Direct Raw` (canonical FAQ source text).
* **Explainable AI Reasoning Drawer**: Expandable UI detailing extracted sub-questions, matched FAQ cards, and similarity scores.

### 🖼️ UC3: Multimodal Image Captioning & Visual Intelligence
* **Flexible Detail Levels**: Generate concise 1-sentence summaries, detailed paragraph breakdowns, or comma-separated SEO/social tags.
* **Multi-Format Resilient Processing**: Built-in `ImageService` supporting JPEG, PNG, WEBP, GIF, and BMP with automated downscaling to respect payload limits.
* **Side-by-Side Visual Comparison**: Upload two images simultaneously to compare visual elements, composition, and semantic differences.
* **Direct Export & Copy**: One-click clipboard copy and metadata inspection for alt-text accessibility and social media publication.

### 💻 UC4: Code Generation & Refactoring Assistant
* **Deterministic 4-Step Agent Pipeline**: `Analyzer` (intent parsing) $\rightarrow$ `Generator` (code synthesis) $\rightarrow$ `Reviewer` (correctness & security) $\rightarrow$ `Advisor` (performance & AST validation).
* **AST Syntax & Complexity Audit**: Automated AST verification to detect syntax errors and evaluate cyclomatic complexity before delivery.
* **In-Context Few-Shot Adaptation**: `tuned` mode retrieves relevant domain examples from JSONL datasets via keyword-overlap scoring to enforce project coding conventions.
* **Side-by-Side Comparison**: Parallel execution of Base vs. Tuned mode to benchmark output quality, style adherence, and response latency.
* **Visual Diff Refactoring Engine**: Paste existing source code and refactoring instructions to generate a color-coded unified diff (`difflib`) and download the updated file.
* **Interactive Fine-Tuning Hub**: In-app dataset manager to inspect existing training pairs, submit new input/output pairs, and trigger adaptation updates.

### ✍️ UC5: Personalized Content Creator Studio
* **Secure JWT Multi-User Isolation**: Password-protected authentication isolating user profiles, writing styles, and personal example repositories.
* **4 Tailored Content Formats**: Dedicated templates and tone adjustments for `Blog Post`, `LinkedIn Post`, `Marketing Email`, and `Social Media Post`.
* **Multi-Agent Editorial Pipeline**: `Planner Agent` (outlines structure) $\rightarrow$ `Drafter Agent` (drafts body) $\rightarrow$ `Auditor Agent` (verifies Tone-of-Voice and audience alignment).
* **Personalized Vector Memory (ChromaDB)**: Semantic vector retrieval across user-specific exemplar collections (`user_personalization_{user_id}`) to mimic author style.
* **Multimodal Visual Context**: Upload architecture diagrams or reference screenshots to extract visual context and weave it into generated copy.
* **Interactive Author Wall & Media Cards**: Finalize and publish articles with format badges and attached visual assets to the community feed.
* **Active Feedback & Learning Loop**: Star rating system (1–5 stars) that automatically captures 5-star generations into JSONL fine-tuning datasets for continuous improvement.

---

## 🔬 5. Architectural Decision: RAG Few-Shot vs Managed Fine-Tuning

> [!IMPORTANT]
> This is a key architectural decision for UC4, based on provider API availability constraints.

### The Challenge: Managed Fine-Tuning Limitations

During development, fine-tuning access constraints across target providers were evaluated:

| Provider | Fine-Tuning Availability | Details |
|---|---|---|
| **Google Gemini Developer API** | ❌ Unavailable | `501 UNIMPLEMENTED` for standard models; moved to Vertex AI Enterprise. |
| **OpenAI** | ❌ Legacy Restricted | Restricted for newer standard tiers and deprecated for legacy endpoints. |

### The Solution: RAG Few-Shot Prompting (In-Context Learning)

Instead of weight fine-tuning, **inference-time behavioral adaptation** is utilized:

```text
mode="tuned" → DatasetManager.find_similar_examples(prompt, top_k=3)
                      ↓  keyword-overlap scoring across JSONL dataset
               [Example 1: User prompt → Expected code]
               [Example 2: User prompt → Expected code]
                      ↓  formatting into few-shot block
               Injection into prompts/generator.txt (section few_shot_context)
                      ↓
               Gemini generates code matching project patterns and conventions
```

### Rationale:

1. **Academic Equivalence**: In-context learning (few-shot prompting) is established as functionally equivalent to parameter tuning for code generation domains (Brown et al., 2020; Wei et al., 2022).
2. **Industry Best Practice**: For dynamic and evolving domains, `RAG > fine-tuning` avoids catastrophic forgetting and offers instant updateability.
3. **Complete Learning Loop**: Users submit examples → dataset grows → semantic retrieval adapts → output quality increases.
4. **Data Portability**: The JSONL format is standardized and ready for future direct model fine-tuning if enterprise endpoints are provisioned.

---

## ⚡ 6. Quick Start & Verification Guide

### Start via Docker:
```powershell
docker compose up --build
```
- 🌐 **Platform Dashboard**: [http://localhost:8501](http://localhost:8501)
- ⚙️ **FastAPI Documentation (Swagger UI)**: [http://localhost:8001/docs](http://localhost:8001/docs)

### Run Automated Tests in Docker:
```powershell
powershell -ExecutionPolicy Bypass -File ".agents/skills/test_runner/scripts/run_docker_tests.ps1"
```

### Quick Walkthrough of UC4:
1. Open [http://localhost:8501](http://localhost:8501) → **💻 Code Generation**
2. **Tab 1**: Enter prompt → click `⚡ Generate Code & Audit` → review code, suggestions, and audit
3. **Tab 1**: Toggle `⚡ Side-by-Side Comparison` → compare Base vs Few-Shot mode
4. **Tab 2**: Paste source code → provide refactoring goal → `🔀 Generate Visual Unified Diff`
5. **Tab 3**: Add training pair → `🚀 Trigger Fine-Tuning Job` → verify dataset status
