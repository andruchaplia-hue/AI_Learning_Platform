---
name: frontend_developer
description: Skill for developing user interface pages, components, and services in Streamlit.
---

# Skill: Frontend Developer

Use this skill when implementing UI elements, adding Streamlit pages, or writing client integration logic.

## Key Rules & Constraints

1. **No Direct LLM SDKs / Frameworks**:
   - Do not import `langchain`, `semantic_kernel`, `google-genai`, or `openai` inside the frontend module.
2. **Backend Communication**:
   - The frontend must only speak with the backend via the `APIClient` (`frontend/services/api_client.py`).
3. **No Hardcoded Endpoints**:
   - Retrieve the API URL via `BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")`.

---

## Playbook 1: Adding a New Streamlit Page

1. Create a file inside `frontend/pages/` with prefix numbers matching the Use Case (e.g., `02_FAQ_Assistant.py`).
2. Add the path resolution fallback at the top of the file to prevent module import issues:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
   ```
3. Use `APIClient` to perform network operations:
   ```python
   from frontend.services.api_client import APIClient
   client = APIClient()
   response = client.post("/api/v1/usecase-endpoint", json=payload)
   ```
4. Render UI with standard layouts (`st.container`, `st.columns`).
5. Render error messages gracefully:
   ```python
   if not response.is_success:
       st.error(f"Error: {response.message}")
   ```
6. **Update Landing Page Navigation (`frontend/Home.py`)**:
   - Update the module card status to `🟢 Ready` and add `st.switch_page("pages/<page_name>.py")` button so the page is accessible from the main landing page.


---

## Playbook 2: Creating Reusable Widgets

1. Reusable components (e.g. sidebar, copy button, header theme) belong in `frontend/components/common_widgets.py`.
2. Ensure components are parameter-driven and do not make state assumptions.
