---
name: backend_developer
description: Skill for developing use case business logic, services, orchestration chains, and security adapters.
---

# Skill: Backend Developer

Use this skill when implementing new use case services, composing LCEL prompt chains, configuring LLM invocations, or managing authentication/data layers.

## Key Rules & Constraints

1. **Centralized Model Inversion (Gateway)**:
   - Always instantiate models via the `LLMGateway.get_llm(settings, framework)` factory.
   - Do not directly instantiate provider classes (e.g. `ChatOpenAI`, `ChatGoogleGenerativeAI`) in the use case files.
2. **Modular Business Logic**:
   - Every use case must be contained within `backend/use_cases/use_case_X/`.
   - Implement `service.py` for execution logic and DTO translation.
3. **Robust Exception Wrapping**:
   - Wrap provider timeouts, API credentials, or schema errors in typed exceptions from `backend/domain/exceptions.py`.
4. **Zero Fallbacks**:
   - Never catch exceptions to silently return mock fallbacks or raw lists. Fail fast and log full context.

---

## Playbook 1: Bootstrapping a Use Case Package

1. Create a directory: `backend/use_cases/use_case_X/`.
2. Implement DTO definitions in `models.py`:
   ```python
   from pydantic import BaseModel

   class UseCaseRequest(BaseModel):
       prompt: str

   class UseCaseResponse(BaseModel):
       result: str
   ```
3. Implement prompt template file in `prompts/use_case_prompt.txt`.
4. Compose chain/kernel composition in `chain.py` or helper module using `LLMGateway`:
   ```python
   from backend.infrastructure.llm.gateway import LLMGateway
   from backend.infrastructure.llm.providers.base_provider import FrameworkType

   llm = LLMGateway.get_llm(settings, framework=FrameworkType.LANGCHAIN)
   ```
5. Implement execution service in `service.py`:
   ```python
   class UseCaseService:
       def __init__(self, settings: AppSettings):
           self.settings = settings

       async def execute(self, payload: UseCaseRequest) -> UseCaseResponse:
           # Validate, invoke model, handle exception wrapper
           pass
   ```

---

## Playbook 2: Authentication & Security Patterns (Use Case 5)

When implementing authentication or profile-backed services:
1. **Password Hashing**: Use `passlib.context.CryptContext` with `bcrypt` (or `hashlib` SHA-256 fallback if native bcrypt is unavailable):
   ```python
   from passlib.context import CryptContext
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   ```
2. **JWT Creation & Verification**: Use `python-jose` or `jwt` with HS256 and expiration timestamps:
   ```python
   import jwt
   from datetime import datetime, timedelta

   def create_access_token(data: dict, secret_key: str, expires_delta: timedelta) -> str:
       to_encode = data.copy()
       expire = datetime.utcnow() + expires_delta
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, secret_key, algorithm="HS256")
   ```
3. **User Isolation**:
   - Ensure personal vector collections in ChromaDB and SQLite records are strictly partitioned by `user_id`.
