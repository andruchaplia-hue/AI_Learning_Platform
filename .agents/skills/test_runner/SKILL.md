---
name: test_runner
description: Skill for running automated pytest suites and reproducing API issues via curl.
---

# Skill: Test Runner

Use this skill to configure, run, and audit testing processes across all platform services and reproduce API issues before fixing bugs.

## Playbook 1: Local Test Execution

To execute tests against the active workspace:

1. Identify the virtual environment interpreter or `uv` runner:
   - Command (using `uv`):
     ```powershell
     uv run pytest
     ```
   - Command (using native python virtualenv):
     ```powershell
     .\venv\Scripts\pytest
     ```
2. Verify all test files under `tests/` pass with zero failures:
   - `test_api.py` (FastAPI routing & thin controller behaviors)
   - `test_service.py` (orchestration, validation, option formatting)
   - `test_gateway.py` (Central LLM Gateway behavior)
   - `test_validator.py` (domain inputs validation)

---

## Playbook 2: Writing New Tests for a Use Case

When creating tests for a new Use Case:
1. Put the test file inside `tests/` with the prefix `test_use_case_X.py`.
2. Mock external services or use the `MockProvider` client to ensure tests run offline without valid keys.
3. Assert that both success responses and failure domain exceptions (e.g. `ValidationError`, `AuthenticationError`) match the expected contracts.

---

## Playbook 3: Mandatory Docker Container Integration Testing

Integration and API tests MUST ALWAYS be validated against the live Docker container environment after restarting the container:

1. Always execute container tests via the helper script:
   ```powershell
   & ".agents/skills/test_runner/scripts/run_docker_tests.ps1"
   ```
2. The helper script automatically performs:
   - `docker compose restart backend` (reloads modified Python files into process RAM).
   - `docker compose exec -T backend pytest tests/ -v` (executes test suite in live container).

---

## Playbook 4: Bug Reproduction via curl (Red Phase)

When tasked with resolving an API bug or defect, **reproduce it explicitly first** before modifying code:

1. **JSON Endpoint Request**:
   ```powershell
   curl.exe -X POST "http://localhost:8000/api/v1/content-generation" `
     -H "Content-Type: application/json" `
     -H "Authorization: Bearer <JWT_TOKEN>" `
     -d '{"content_type": "blog_post", "prompt": "AI Future"}'
   ```

2. **Multipart/Form-Data Request (e.g. with image)**:
   ```powershell
   curl.exe -X POST "http://localhost:8000/api/v1/image-captioning" `
     -F "file=@data/uploads/sample.png" `
     -F "style=detailed"
   ```

3. **Verify the failure output**:
   Capture the exact HTTP status code and JSON error payload to confirm reproduction, then proceed to fix the domain code.
