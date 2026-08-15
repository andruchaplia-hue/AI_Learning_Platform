# ✍️ Use Case 1: Text Autocomplete — Technical Specification

## 1. Overview
**Use Case 1 (Text Autocomplete)** provides intelligent completion for text phrases and paragraphs using a **LangChain LCEL (LangChain Expression Language)** pipeline powered by **Google Gemini** (or **MockProvider** for offline testing).

---

## 2. Component Layout

```text
backend/use_cases/use_case_1_autocomplete/
├── __init__.py
├── models.py              # AutocompleteRequest, AutocompleteResponse, CompletionMode
├── service.py             # AutocompleteService (orchestrates parsing & instruction loading)
├── chain.py               # LCEL runnable composition: prompt | llm | parser
└── prompts/
    └── autocomplete_prompt.txt
```

---

## 3. Data Transfer Objects (DTO)

### `CompletionMode` Enum
```python
class CompletionMode(str, Enum):
    SENTENCE  = "sentence"    # Complete the current sentence/phrase
    PARAGRAPH = "paragraph"   # Complete the current paragraph
```

### Request (`AutocompleteRequest`)
```python
class AutocompleteRequest(BaseModel):
    text: str             # Min length: 5, Max length: 5000
    mode: CompletionMode  # Default: "sentence"
```

### Response (`AutocompleteResponse`)
```python
class AutocompleteResponse(BaseModel):
    completion: str              # Main output completion (first parsed option)
    completions: list[str]       # All parsed clean completion options
    execution_time_sec: float    # Pipeline execution duration in seconds
```

---

## 4. LCEL Pipeline Composition

The LCEL chain is defined in `chain.py`:
```python
prompt = ChatPromptTemplate.from_template(raw_prompt)
parser = StrOutputParser()
chain = prompt | llm | parser   # LCEL pipe operator
```

Called asynchronously in `service.py`:
```python
completion_result = await self.chain.ainvoke({"text": valid_text, "instruction": instruction})
```

### Mode-specific Instructions
The `instruction` variable is injected into the prompt depending on the chosen mode:

| Mode | Instruction injected into prompt |
|---|---|
| `sentence` | "Complete the current sentence/phrase. Stop as soon as the current sentence is finished." |
| `paragraph` | "Complete the current paragraph. Stop as soon as the current paragraph is finished. Do not start a new paragraph." |

---

## 5. Text Parsing Utilities (`service.py`)

* **`clean_option_prefix(text)`**: Strips leading list markers and numbers from raw LLM output so completion options can be cleanly concatenated with user input (e.g. `1. `, `* Option A:`, `Option B:`).
* **`split_options(text)`**: Splits multi-option LLM responses into a `list[str]` of individual clean options.
* **`parse_provider_exception(exc)`**: Maps raw LLM provider exceptions (timeouts, quota exceeded, invalid API keys) to clean, user-friendly error messages.

---

## 6. API Endpoint

- **Endpoint**: `POST /api/v1/autocomplete`
- **Controller**: `backend/api/routes/autocomplete.py`

Example Request:
```json
{
  "text": "Artificial Intelligence is",
  "mode": "sentence"
}
```

Example Response:
```json
{
  "completion": "transforming modern technology by automating routine tasks.",
  "completions": [
    "transforming modern technology by automating routine tasks."
  ],
  "execution_time_sec": 0.342
}
```

---

## 7. UI Features (`frontend/pages/01_Autocomplete.py`)
- Text area input with live character counter (colors: grey for empty, orange for `< 5` chars, red for `> 5000` chars, green for valid).
- Buttons disabled when length rules are violated.
- Split-screen colored output rendering (user input grey, generated completion bold blue).
- Execution timing and quick copy buttons.
