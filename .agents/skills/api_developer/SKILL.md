---
name: api_developer
description: Skill for developing thin FastAPI APIRouters acting strictly as proxy layers to Use Case services.
---

# Skill: API Developer

Use this skill when defining FastAPI endpoints, routing request payloads, configuring security dependencies, or updating the FastAPI app setup.

## Key Rules & Constraints

1. **Proxy-Only Controllers (Thin Routers)**:
   - APIRouter endpoints must **never** contain business logic, database queries, framework integrations (LangChain/Semantic Kernel), or prompt rendering.
   - Routers only parse requests, invoke the correct Use Case service, and return serialized responses.
2. **Strict Layer Boundaries**:
   - Do not import `BaseProvider`, `LLMGateway`, or framework-native client classes in the router files.
3. **Pydantic Validation**:
   - Ensure all request bodies and query parameters use Pydantic models.

---

## Playbook 1: Creating a Thin Use Case Router

1. Create a router file in `backend/api/routes/` (e.g. `content_generation.py`).
2. Define the APIRouter with tags:
   ```python
   from fastapi import APIRouter, Depends
   from backend.use_cases.use_case_5_content_gen.models import ContentGenerationRequest, ContentGenerationResponse
   from backend.use_cases.use_case_5_content_gen.service import ContentGenerationService

   router = APIRouter(prefix="/api/v1/content-generation", tags=["ContentGeneration"])
   ```
3. Implement thin endpoint delegating to the service layer:
   ```python
   @router.post("/", response_model=ContentGenerationResponse)
   async def generate_content(
       payload: ContentGenerationRequest,
       current_user: User = Depends(get_current_user),
       service: ContentGenerationService = Depends(ContentGenerationService)
   ):
       return await service.generate(payload, current_user)
   ```

---

## Playbook 2: Registering a Router

1. Open `backend/api/app.py`.
2. Import the new router.
3. Include the router in the app startup:
   ```python
   app.include_router(new_router)
   ```
