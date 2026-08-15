---
name: documentation_manager
description: Skill for maintaining, updating, and auditing AI Learning Platform documentation across docs/, Presentation.md, and README.md.
---

# Skill: Documentation Manager

Use this skill whenever creating, updating, or auditing documentation for the AI Learning Platform.

## Core Rules & Responsibilities

0. **Mandatory Pre-Edit Context Review**:
   Before making any code modifications or implementing new features, you **MUST** read and review `README.md`, `docs/Main_Architecture.md`, `docs/Presentation.md`, and relevant `docs/UseCase*.md` specifications to gain full project context and adhere to design decisions.

1. **Mandatory Dual Sync**:
   Whenever making architectural changes, modifying API contracts, altering services, or adding a new Use Case, you **MUST** update both:
   - Root **`README.md`** (high-level setup, routes, status badges, links)
   - Specific specification files in **`docs/`** (`Main_Architecture.md`, `UseCaseX_...md`, `Presentation.md`).

2. **Evaluator Presentation Framing**:
   Keep **`docs/Presentation.md`** focused on presenting key engineering decisions (Clean Architecture layers, LCEL, LLM Gateway, error schema, MockProvider) and the physical project tree layout for the assignment reviewer/teacher.

3. **Markdown Hyperlink Standard**:
   Always use valid Markdown links to referenced files (e.g. `[Main Architecture](docs/Main_Architecture.md)`).

---

## Playbook 1: Updating Documentation on Code Changes

Whenever an API route, DTO model, or service logic changes:

1. Identify affected Use Case specification (e.g. `docs/UseCase1_Text_Autocomplete.md`).
2. Update DTO request/response schemas or endpoint paths in the specification.
3. Check `docs/Main_Architecture.md` if gateway interfaces, error handlers, or settings changed.
4. Update `README.md` table of endpoints, status badges, and instructions.
5. Verify that all Markdown links in root `README.md` resolve correctly.

---

## Playbook 2: Onboarding a New Use Case Document

When starting implementation of a new Use Case (e.g. UC2 FAQ Assistant):

1. Create/update `docs/UseCaseX_<Name>.md` with:
   - Overview & Business Goals
   - Target Technology Stack (Framework, LLM Gateway mode, Database)
   - Data Transfer Objects (Request/Response)
   - API Endpoint paths and controller mapping
   - Test Plan
2. Update the Use Case status table in `README.md` and engineering decisions in `docs/Presentation.md`.
3. Add the link to root `README.md`.

---

## Playbook 3: Documentation Audit Checklist

Before concluding any task:
- [ ] Is root `README.md` updated with accurate environment instructions, container commands, and documentation links?
- [ ] Are all files in `docs/` matching the actual code layout in `backend/` and `frontend/`?
- [ ] Is `docs/Presentation.md` aligned with current engineering decisions and physical project tree?
- [ ] Do all Markdown links in root `README.md` resolve correctly?
