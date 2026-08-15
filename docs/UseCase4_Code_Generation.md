# 💻 Use Case 4: Code Generation Assistant — Technical Specification

## 1. Overview
**Code Generation Assistant** is an advanced AI coding tool built on the AI Learning Platform using Semantic Kernel AI Agents.

---

## 2. Key Capabilities

* **Semantic Kernel Agent Orchestration**: 4-plugin sequential agent workflow:
  `RequirementsAnalyzer` (JSON specifications) → `CodeGenerator` (source code) → `CodeReviewer` (correctness, PEP8, security) → `ImprovementAdvisor` (refactoring recommendations).
* **RAG Few-Shot Model Adaptation**: In `tuned` mode, the `DatasetManager` retrieves relevant training examples from `code_generation_dataset.jsonl` using keyword-overlap matching and injects them into the Code Generator prompt as few-shot context.
* **Unified Diff Engine**: Accepts existing source code and refactoring instructions, calculates unified diffs (`difflib.unified_diff`), and yields clickable file download paths.
* **Fine-Tuning Hub**: Interactive JSONL dataset inspector, inline validation forms, and few-shot mode activation trigger.
* **Side-by-Side Comparison**: Run Base and Few-Shot modes simultaneously and inspect outputs side-by-side.

---

## 3. Technology Stack
- **Framework**: Semantic Kernel (`semantic-kernel` for Python)
- **LLM Provider**: Google Gemini (`gemini-3.1-flash-lite`) / Mock Provider via `LLMGateway`
- **RAG Retrieval**: Keyword-overlap in `DatasetManager`
- **Backend API**: FastAPI (`backend/api/routes/code_generation.py`)
- **Frontend UI**: Streamlit 3-tab IDE-like interface (`frontend/pages/04_Code_Generation.py`)

---

## 4. Architectural Decision: RAG Few-Shot vs Managed Fine-Tuning

> [!IMPORTANT]
> This is a key architecture decision made due to current public cloud API restrictions.

1. **API Limitations**:
   * Google Gemini Developer API yields `501 UNIMPLEMENTED` for model tuning requests (managed tuning is shifted to Vertex AI Enterprise).
   * OpenAI deprecated self-serve fine-tuning endpoints for new accounts.
2. **Alternative (In-Context Learning)**:
   Instead of retuning weights, the agent retrieves target examples and injects them in-context. This yields comparable behavior alignment for target coding patterns and style.

---

## 5. REST API Endpoints

- `POST /api/v1/code-generation`: Code generation / refactoring via SK pipeline.
- `POST /api/v1/code-generation/diff`: Refactor and generate unified diff logs.
- `GET /api/v1/code-generation/dataset`: List JSONL dataset entries.
- `POST /api/v1/code-generation/dataset`: Append a new training example.
- `POST /api/v1/code-generation/fine-tune`: Verify or trigger RAG few-shot mode.
