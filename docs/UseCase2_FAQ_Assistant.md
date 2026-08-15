# 💬 Use Case 2: FAQ Assistant — Technical Specification & Architecture

## 1. Overview
The **FAQ Assistant** is an intelligent AI Agent built with **Semantic Kernel** and multi-query RAG capabilities. It processes compound user questions, decomposes them into sub-queries, performs vector similarity retrieval via ChromaDB, evaluates coverage, and generates responses in two distinct modes.

---

## 2. Technology Stack & Frameworks

| Component | Technology |
|---|---|
| **Agent Framework** | Semantic Kernel (`kernel.invoke`, native plugin tool calling) |
| **LLM Provider** | `GoogleProvider` / `MockProvider` via `LLMGateway` (`FrameworkType.SEMANTIC_KERNEL`) |
| **Vector Storage** | ChromaDB (`backend/infrastructure/memory/vectorstorage/chroma_store.py`) — with persistent index cache loading from `data/vectorstore/chroma/chroma_embeddings.json` to prevent re-embedding on container restarts |
| **Embedding Model** | Gemini Embedding via `EmbeddingService` (with deterministic offline mock fallback) |
| **Session Memory** | SQLite (`backend/infrastructure/memory/sqlite/sqlite_memory.py`) — persists per `session_id` |
| **Knowledge Base** | `FAQRepository` (`backend/infrastructure/memory/storage/faq_repository.py`) — JSON file storage |

---

## 3. Component Layout

```text
backend/use_cases/use_case_2/
├── __init__.py
├── models.py          # FAQQueryRequest/Response, ExecutionDetails, RetrievedFAQ
├── service.py         # FAQService — orchestration, memory, ingestion, query processing
├── agent.py           # FAQAgent — decomposed SK kernel pipeline orchestrator
├── retriever.py       # FAQRetriever — ChromaDB vector search wrapper
├── prompt_loader.py   # Loads prompt .txt files from prompts/
├── plugins/
│   ├── analysis_plugins.py   # QueryDecomposerPlugin, CoverageAnalyzerPlugin
│   └── faq_plugin.py         # FAQPlugin — ChromaDB retrieval tool
└── prompts/
    ├── system_prompt.txt
    ├── synthesis_prompt.txt
    ├── decompose_prompt.txt
    ├── coverage_prompt.txt
    └── parse_prompt.txt
```

---

## 4. RAG Pipeline Flow

```text
User query
    │
    ▼  1. QueryDecomposerPlugin
Compound query → ["sub-question 1", "sub-question 2", ...]
    │
    ▼  2. FAQPlugin + ChromaDB
Per sub-question → top-K FAQ candidates (cosine similarity)
    │
    ▼  3. CoverageAnalyzerPlugin
coverage_score, selected_faq_ids (max 1 per sub-question)
    │
    ▼  4. Filtering
Discard candidates below similarity_threshold / not in selected_faq_ids
    │
    ▼  5. Strict Block or Response Generation
coverage_score == 0.0 → fallback message
coverage_score  > 0.0 → synthesize (User-Friendly) or return raw (Direct)
    │
    ▼  SQLiteMemory.save_message(session_id, ...)
```

---

## 5. Data Transfer Objects

### `FAQItem` (Defined in `backend/domain/models/faq.py`)
```python
class FAQItem(BaseModel):
    id: int
    category: str
    question: str
    answer: str
```

### `FAQQueryRequest`
```python
class FAQQueryRequest(BaseModel):
    query: str                         # User question
    session_id: str | None             # Default: "default_session"
    user_friendly: bool = True         # True: LLM synthesis, False: raw FAQ text
    sk_filtering: bool = True          # True: SK agent candidate filter active
```

### `FAQQueryResponse`
```python
class FAQQueryResponse(BaseModel):
    status: str                        # "success"
    answer: str                        # Generated or raw FAQ text
    found: bool                        # False if coverage_score == 0.0
    session_id: str
    execution_details: ExecutionDetails | None
```

---

## 6. Response Modes

* **✨ User-Friendly**: LLM synthesizes a smooth structured answer, appending `[FAQ #ID]` citations to the output.
* **📌 Direct Raw**: Bypasses LLM synthesis and returns the exact raw unedited text of the matching FAQ items.

Both modes apply a **strict block** when `coverage_score == 0.0` to prevent hallucinations.

---

## 7. REST API Endpoints (`backend/api/routes/faq.py`)

- `POST /api/v1/faq/chat`: Main query processing route.
- `POST /api/v1/faq/item`: Add single Q&A item and re-index.
- `POST /api/v1/faq/bulk`: Bulk index JSON array of Q&A items.
- `POST /api/v1/faq/parse-text`: SK-powered unstructured text parsing and index.
- `POST /api/v1/faq/reload`: Force reload index from faq.json.
- `GET /api/v1/faq/history/{session_id}`: Fetch SQLite chat history.
- `DELETE /api/v1/faq/history/{session_id}`: Clear SQLite chat history.
