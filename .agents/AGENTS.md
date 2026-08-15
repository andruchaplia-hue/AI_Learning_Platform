# Workspace Guidelines & Standard Operating Procedures (AI Learning Platform)

Any agent working in this workspace must strictly adhere to these architectural standards, development lifecycle rules, and guidelines.

---

## 1. Standard Development & Bugfix Lifecycle (SOP)

Every task, feature implementation, or bugfix MUST strictly follow this 7-step sequence:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Documentation Review & Context Analysis                              │
│    - Read README.md, docs/Main_Architecture.md, docs/Presentation.md,   │
│      and target docs/UseCase*.md.                                       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Bug Reproduction via curl / API Test (MANDATORY for Bugfixes)       │
│    - If solving an issue/bug: write & run a curl/PowerShell test to     │
│      explicitly reproduce the failure BEFORE touching production code.  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Domain & Architecture Implementation                                 │
│    - Implement changes following Clean Architecture boundaries.         │
│    - Respect config-first settings in configs/config.yaml.              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Architecture Validation Audit                                        │
│    - Run architecture_validator skill to ensure no leaks across layers. │
│    - Verify proxy-only routers and clean imports.                       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Synchronized Test & UI Navigation Updates                            │
│    - Update unit/integration tests in tests/ (with Mock/Offline fallback).│
│    - Update frontend/Home.py navigation status if UI pages change.      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Live Docker Container Testing                                        │
│    - Execute live container tests via:                                  │
│      powershell -ExecutionPolicy Bypass -File                           │
│      ".agents/skills/test_runner/scripts/run_docker_tests.ps1"          │
│    - Verify 100% test pass rate in the live container.                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. Documentation Synchronization (MANDATORY)                            │
│    - Run documentation_manager skill to synchronously update README.md, │
│      docs/Presentation.md, and relevant docs/UseCase*.md files.         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architectural Layers & Strict Boundaries

The platform strictly enforces a 5-layer Clean Architecture layout:

1. **UI Layer** (`frontend/`):
   - Scope: Streamlit pages (`pages/`), components, and themes.
   - Constraints: **Zero direct LLM calls, zero LangChain/Semantic Kernel imports, zero API key access.** Interacts only with FastAPI backend via `APIClient` (`frontend/services/api_client.py`).
2. **API Layer** (`backend/api/`):
   - Scope: FastAPI HTTP routing, request parsing, and error serialization.
   - Constraints: **Thin controllers only.** Routers in `routes/` must strictly act as proxies to the use case services. Zero business logic or framework invocation is allowed here.
3. **Use Cases Layer** (`backend/use_cases/`):
   - Scope: Business logic, domain validation, execution timing, agent orchestration, and prompt composition.
   - Structure: Each use case resides in its own isolated folder (`use_cases/use_case_X/`), housing models, services, chains/agents, and prompts.
4. **Framework Layer** (`backend/frameworks/`):
   - Scope: Integration adapters and helpers for LangChain and Semantic Kernel bindings.
5. **Infrastructure & Gateway Layer** (`backend/infrastructure/`):
   - Scope: `LLMGateway` (wrapping Google/Mock providers), SQLite Memory (`memory/`), ChromaDB Vector Storage (`vectorstorage/`), Storage Manager (`storage/`), and Authentication (`auth/`).

---

## 3. API Proxying & Thin Controller Rules

Every router defined in `backend/api/routes/*.py` must strictly adhere to the following rules:
- Parse and validate request bodies using Pydantic DTO models.
- Delegate the call immediately to the specific use case `Service` class.
- Return the service output serialized to JSON.
- No direct LLM client instantiations or chain executions are permitted in the router file.

---

## 4. Security & Authentication Standards (JWT)

- **Infrastructure Location**: `backend/infrastructure/auth/` (JWTManager, PasswordHasher, UserRepository in SQLite).
- **Scope**: Authentication is enforced strictly for **Use Case 5** (`/api/v1/auth`, `/api/v1/profile`, `/api/v1/content-generation`). Use Cases 1–4 remain open and unauthenticated.
- **Dependency Injection**: Protected endpoints must use FastAPI `Depends(get_current_user)`:
  - Unauthorized access must return standard JSON: `{"status": "error", "message": "Could not validate credentials"}` with HTTP 401.
- **Security Rules**: Never log or store plain-text passwords or JWT secret keys.

---

## 5. LangChain & Framework API Standards

- **No Legacy LangChain Imports**:
  - ❌ `from langchain.llms import OpenAI`
  - ❌ `from langchain.chat_models import ChatOpenAI`
  - ❌ `from langchain.chains import LLMChain`
  - ✔️ `from langchain_google_genai import ChatGoogleGenerativeAI`
  - ✔️ `from langchain_openai import ChatOpenAI`
  - ✔️ `from langchain_core.prompts import ChatPromptTemplate`
- **Use LCEL (LangChain Expression Language)**:
  - Compose chains using the pipe operator: `chain = prompt | llm | parser`.
  - Parser: `StrOutputParser` from `langchain_core.output_parsers`.
- **Chain Invocation**:
  - Use `.invoke({"text": input_text})` or `.ainvoke({"text": input_text})`.

---

## 6. Error Handling & Fail-Fast Schema

Under no circumstances should raw Python stack traces or silent fallbacks be returned.

- **Custom Exception Types** (`backend/domain/exceptions.py`):
  - `ValidationError`: Input text or payload fails domain validation.
  - `ConfigurationError`: Missing, corrupt, or invalid config parameters.
  - `ProviderError`: LLM gateway or provider fails to call the LLM.
  - `AuthenticationError`: Invalid credentials, expired token, or unauthorized access.
  - `InternalError`: Unhandled backend issues.
- **FastAPI Exception Handlers**:
  - Catch typed exceptions and return standard JSON error payload:
    ```json
    {
      "status": "error",
      "message": "Human-readable error description"
    }
    ```
- **Zero Silent Fallbacks**: Never catch LLM/gateway exceptions to silently return mock fallbacks. Log the complete traceback (`logger.error(..., exc_info=True)`) and raise typed domain exceptions.

---

## 7. Config-First Management

- No hardcoded models, keys, parameters, endpoints, or fallback defaults in Python code.
- **Single Source of Truth**: `configs/config.yaml` is the authoritative source.
- **No Fallbacks**: Never use `.get("key", default_value)` or hardcode fallback magic numbers in `AppSettings` or service classes. Missing parameters in `configs/config.yaml` MUST fail fast by raising a `ConfigurationError`.
- Settings are loaded via `backend/infrastructure/config/settings.py` from `configs/config.yaml` and `.env` using Pydantic Settings.

---

## 8. Directory Structure
```text
ai-learning-platform/
├── frontend/
│   ├── Home.py
│   ├── pages/
│   ├── components/
│   └── services/
├── backend/
│   ├── api/
│   │   ├── app.py
│   │   └── routes/
│   ├── use_cases/
│   ├── frameworks/
│   └── infrastructure/
│       ├── auth/
│       ├── config/
│       ├── llm/
│       ├── memory/
│       └── storage/
├── configs/
├── data/
├── docs/
├── docker/
└── tests/
```

---

## 9. Strict User Authorization for Code Edits

- **No Automatic Code Edits**: Do not automatically edit any code or files unless the user explicitly instructs you to fix/edit them directly.
