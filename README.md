# 🎓 AI Learning Platform — Unified Architecture for 5 Use Cases

**AI Learning Platform** is a unified, multi-module platform encompassing 5 educational generative and agentic AI use cases. The architecture is engineered according to **Clean Architecture** principles, featuring a **Multi-Framework LLM Gateway** (combining **LangChain LCEL** and **Semantic Kernel**), a multi-page dashboard built with **Streamlit**, and a clean REST API built with **FastAPI**.

---

## 📌 Table of Contents
1. [Platform Architecture Overview](#platform-architecture-overview)
2. [Documentation & Specifications](#documentation--specifications)
3. [Covered Use Cases](#covered-use-cases)
4. [Quick Start with Docker](#quick-start-with-docker)
5. [Local Development (Dev Mode)](#local-development-dev-mode)
6. [Testing](#testing)

---

## 🏛️ Platform Architecture Overview

The system is structured across clean, strictly isolated layers:

```text
┌───────────────────────────────────────┐
│        Streamlit Frontend             │  (Home.py + pages/ + components/ + services/)
└───────────────────┬───────────────────┘
                    │ REST HTTP
                    ▼
┌───────────────────────────────────────┐
│              FastAPI API              │  (app.py + routes/)
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│     Use Cases & Domain Layer          │  (use_cases/ + domain/)
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│    Infrastructure & Gateway Layer     │  (LLMGateway, Memory, Storage, Auth, Config)
└───────────────────────────────────────┘
```


---

## 📚 Documentation & Specifications

Detailed architectural documents and technical specifications are available in the [`docs/`](docs/) directory:

- 📺 **[Presentation.md](docs/Presentation.md)** — Express 3-minute onboarding presentation outlining project goals and features.
- 🏛️ **[Main_Architecture.md](docs/Main_Architecture.md)** — Complete architectural passport, Clean Architecture layer rules, and Multi-Framework Gateway design.
- ✍️ **[UseCase1_Text_Autocomplete.md](docs/UseCase1_Text_Autocomplete.md)** — Technical specification for UC1 (LangChain LCEL Text Autocomplete).
- 💬 **[UseCase2_FAQ_Assistant.md](docs/UseCase2_FAQ_Assistant.md)** — Specification and roadmap for UC2 (Semantic Kernel FAQ & Memory).
- 🖼️ **[UseCase3_Image_Captioning.md](docs/UseCase3_Image_Captioning.md)** — Specification and roadmap for UC3 (LangChain Vision & Multimodal).
- 💻 **[UseCase4_Code_Generation.md](docs/UseCase4_Code_Generation.md)** — Specification and roadmap for UC4 (Semantic Kernel Agents & Visual Diff).
- 🎯 **[UseCase5_Content_Generator.md](docs/UseCase5_Content_Generator.md)** — Specification and roadmap for UC5 (LangChain Agent, JWT Auth & Personalization RAG).

---

## 🚀 Covered Use Cases

| Module | Use Case | Framework | Specification | Status |
| :--- | :--- | :--- | :--- | :--- |
| **01** | **Text Autocomplete** | LangChain (LCEL) + Gemini | [UseCase1_Text_Autocomplete.md](docs/UseCase1_Text_Autocomplete.md) | 🟢 Fully Ready |
| **02** | **FAQ Assistant** | Semantic Kernel + ChromaDB | [UseCase2_FAQ_Assistant.md](docs/UseCase2_FAQ_Assistant.md) | 🟢 Fully Ready |
| **03** | **Image Captioning** | LangChain Vision + Gemini | [UseCase3_Image_Captioning.md](docs/UseCase3_Image_Captioning.md) | 🟢 Fully Ready |
| **04** | **Code Generation** | Semantic Kernel Agents + RAG Few-Shot | [UseCase4_Code_Generation.md](docs/UseCase4_Code_Generation.md) | 🟢 Fully Ready |
| **05** | **Content Generator** | LangChain Agent + Auth + Vector RAG | [UseCase5_Content_Generator.md](docs/UseCase5_Content_Generator.md) | 🟢 Fully Ready |

---

## 🐳 Quick Start with Docker

Build and start the entire multi-container platform with a single command:

```powershell
docker compose up --build
```

Once started:
- 🌐 **Frontend (Streamlit Multi-page App)**: [http://localhost:8501](http://localhost:8501)
- ⚙️ **Backend REST API (FastAPI Swagger Docs)**: [http://localhost:8001/docs](http://localhost:8001/docs)

Stop containers:
```powershell
docker compose down
```

---

## 💻 Local Development (Dev Mode)

### 1. Environment Setup
Install dependencies using `uv` or `pip`:
```powershell
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create or edit `.env`:
```env
GOOGLE_API_KEY=your_api_key_here
APP_ENV=dev
BACKEND_URL=http://localhost:8001
```
*(For offline execution without external API keys, set `provider: "mock"` in `configs/config.yaml`).*

### 3. Start Backend & Frontend
In terminal 1 (FastAPI Backend):
```powershell
uvicorn backend.api.app:app --reload --port 8001
```

In terminal 2 (Streamlit Frontend):
```powershell
streamlit run frontend/Home.py
```

---

## 🧪 Testing

Run unit and integration test suite:
```powershell
pytest
```

Run tests inside live Docker container (recommended):
```powershell
powershell -ExecutionPolicy Bypass -File ".agents/skills/test_runner/scripts/run_docker_tests.ps1"
```

**Test Suite Coverage**: 53 automated tests covering UC1, UC2, UC3, UC4, UC5 + gateway, API routing, auth security, and validators (100% pass rate).
