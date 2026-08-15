---
name: architecture_validator
description: Skill for validating and auditing system layer boundaries, imports, API proxying rules, and configuration settings.
---

# Skill: Architecture Validator

Use this skill to audit code layouts, boundaries, and dependencies before finishing any feature.

## Architecture Checklist Playbook

Run through this checklist file-by-file for any modified or newly added code:

### 1. Layer Boundary Check
- [ ] **No Leak in Frontend**: Verify that files under `frontend/` **never** import `langchain`, `semantic_kernel`, `google-genai`, `openai`, or make raw DB connections.
- [ ] **Proxy-Only Controllers**: Verify that `backend/api/routes/*.py` files **never** contain custom business logic, text processing, or raw LLM executions. They must only import use case models/services.
- [ ] **Config Decoupling**: Verify that no API keys or environment names are hardcoded in use cases or gateways. They must be loaded via `backend/infrastructure/config/settings.py`.

### 2. Dependency Injection Check
- [ ] **Central Gateway Calls**: Verify that all use case modules obtain model clients from `LLMGateway.get_llm()`.
- [ ] **Interface Dependence**: Ensure use case modules depend on abstract `BaseProvider` or generic clients rather than specific provider implementations (like `GoogleProvider`).

### 3. Verification Commands
- Check codebase layout consistency:
  ```powershell
  Get-ChildItem -Recurse -Filter *.py | Select-String -Pattern "langchain" | Where-Object { $_.Path -like "*frontend*" }
  ```
  *(Expected result: No matches. If matches exist, the layered boundary is violated!)*
