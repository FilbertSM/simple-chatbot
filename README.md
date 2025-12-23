# CXO-GAIA — Roleplay & Tutor Chatbot

Comprehensive documentation for IT / DevOps to deploy, configure, and maintain the CXO-GAIA project.

---

## Overview

CXO-GAIA is a Streamlit-based interactive training platform combining: roleplay simulations, tutoring Q&A, and grading for customer service scenarios. The application uses a small role database and a retrieval-augmented generation (RAG) flow backed by a Chroma vector store and an LLM.

Key capabilities:
- Guided multi-phase sessions (GREETING → TUTORING → ROLEPLAY → GRADING)
- Auto-triggered assistant messages (system-driven greetings)
- RAG in tutoring phase using Chroma
- Extensible role definitions stored in `engine.py`'s `DUMMY_DB`

---

## Repo layout

- `main.py` — Streamlit app, UI, session state, and phase controls.
- `engine.py` — Core orchestration: role DB, system prompt builder, `query_chain`, vectorestore loading, and retriever utils.
- `requirements.txt` — Python dependencies (install with pip).
- `uploaded_pdfs/` — (data folder) user-uploaded docs (if used for indexing).
- `chroma_store/` — Chroma persistent folder (vector DB files).

---

## Components & Flow

1. Streamlit UI (`main.py`) manages user session, phases, and triggers AI greeting when `st.session_state.trigger_ai_greeting` is true.
2. `query_chain` in `engine.py` orchestrates prompt building and LLM invocation:
   - Loads role data from `DUMMY_DB` via `fetch_roleplay_data(role_id)`.
   - Builds a dynamic system prompt via `build_system_prompt(phase, data)` depending on the phase (GREETING, TUTORING, ROLEPLAY, GRADING).
   - For `TUTORING` phase, performs retrieval from Chroma using `retriever.invoke(user_input)` and embeds context into the prompt.
   - Calls an LLM chain built as `ChatPromptTemplate.from_template(...) | llm | StrOutputParser()` and `chain.invoke(...)` to get the textual response.

Notes: the project currently forces `ALWAYS RESPONSE USING BAHASA INDONESIA` in the prompt template in `engine.py`.

---

## Environment & Secrets

Required environment variables (set via OS or `.env`):

- `GEMINI_API_KEY` — (optional) Google Gemini API key if using Gemini/Google Generative AI.
- `UPLOAD_DIR` — optional (defaults to `./uploaded_pdfs`).
- `PERSIST_DIR` — optional (defaults to `./chroma_store`).

Store secrets securely. On Windows you can set a user environment variable:

```powershell
setx GEMINI_API_KEY "your_api_key_here"
```

Or create a `.env` file with:

```
GEMINI_API_KEY=your_api_key_here
```

---

## Dependencies

Install dependencies from `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

If you want to use Google Gemini instead of Ollama, install the official Google generative AI client:

```bash
python -m pip install google-generative-ai
```

Optional: `langchain` and `langchain_ollama` are referenced; keep them in `requirements.txt` as needed by project.

---

## Running Locally (development)

1. Ensure dependencies installed and environment variables set.
2. Ensure Chroma store folder exists (the code creates `uploaded_pdfs` automatically).
3. Start the Streamlit app:

```bash
streamlit run main.py
```

Port: Streamlit chooses an available port (default 8501). Open the URL shown in the terminal.

---

## LLM Configuration

The repository contains references to two LLM approaches:

- Ollama (local Ollama server): `OllamaLLM` (used in `engine.py` and older `main.py` variant).
- Google Gemini via `langchain_google_genai.ChatGoogleGenerativeAI` (used in `main.py` in current workspace snapshot).

engine.py currently creates `OllamaEmbeddings` and an `OllamaLLM` instance at module import time. `main.py` creates the runtime `st.session_state.llm` (either `OllamaLLM` or `ChatGoogleGenerativeAI`).

Switching to Gemini (recommended steps):

1. Install `google-generative-ai`.
2. Set `GEMINI_API_KEY` (see above).
3. Update the code that sets `st.session_state.llm` to use the LangChain Gemini wrapper or a custom adapter that matches the chain's expected interface.

Minimal example adapter (non-LangChain) to wrap Gemini chat completions:

```python
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class GeminiAdapter:
    def __init__(self, model='gemini-3.5-pro'):
        self.model = model

    def __call__(self, prompt_text: str) -> str:
        # Minimal mapping: returns plain text response
        resp = genai.chat.completions.create(model=self.model, messages=[{'author': 'user', 'content': prompt_text}])
        return resp.choices[0].message.content

# In main.py, set:
# st.session_state.llm = GeminiAdapter(model='gemini-3.5-pro')
```

Adapting to LangChain: if `llm` must be a LangChain LLM, prefer `langchain`'s Google/Vertex integrations or `langchain_google_genai.ChatGoogleGenerativeAI` which the code already imports.

Important: `engine.py` builds a prompt template and then does `prompt | llm | StrOutputParser()`. That composition expects the `llm` to be a LangChain-compatible component. If using a custom adapter, adapt `engine.py` to call `llm(prompt_text)` directly and bypass the operator pipeline.

Example small change in `engine.py` to support non-LangChain LLMs (conceptual):

```python
# Build prompt_text from prompt.invoke(...)
prompt_text = prompt.format(role_instruction=system_instructions, knowledgeBase=knowledge_base_content, question=user_input)
if hasattr(llm, '__call__'):
    raw = llm(prompt_text)
else:
    # existing LangChain pipeline
    raw = chain.invoke({...})
```

---

## Vectors & Knowledge Base

- Vector store persist dir: `PERSIST_DIR` (default `./chroma_store`). `engine.load_vectors()` constructs a `Chroma` instance that uses `OllamaEmbeddings` at module import.
- To rebuild or update vectors: add/upload documents into `uploaded_pdfs/` and run your embedding/indexing routine (not included in repo — implement a script to ingest and call `Chroma` insert APIs).

---

## Roles & Scenario Data

Role definitions live in `engine.py` as `DUMMY_DB` (an in-memory list of role records). Each entry contains fields like:

- `role_name` — short ID (e.g., `CS_COMPLAINT`)
- `topic` — human-friendly topic name
- `mentor_persona` — persona text for system prompt
- `simulation_persona_text` — role to play in roleplay
- `scenario_details_text` — scenario context for roleplay
- `success_criteria` — list of rubric items used during grading

To add a new role: edit `DUMMY_DB` and add a new dict with the same fields (or replace with a DB read if you prefer persistent storage).

## Function Reference

This section documents the main functions in `engine.py` and `main.py` so IT and developers can understand responsibilities, inputs/outputs, and extension points.

### `engine.py`

- `setup_logger(name="gaia") -> logging.Logger`
  - Purpose: create and return a configured logger (DEBUG console handler).
  - Notes: idempotent; checks `hasHandlers()` to avoid duplicate handlers.

- `load_vectors() -> Chroma`
  - Purpose: instantiate and return a `Chroma` vectorstore using `PERSIST_DIR` and module `embeddings`.
  - Side-effects: expects `OllamaEmbeddings` at module import; consider lazy initialization in production.

- `get_retriever(vectorstore, k=3)`
  - Purpose: return a retriever for the provided vectorstore configured to return `k` matches.

- `fetch_roleplay_data(role_id: str) -> Dict`
  - Purpose: lookup and return role configuration from `DUMMY_DB`.
  - Raises: `ValueError` when role not found.

- `build_system_prompt(phase: str, data: dict) -> str`
  - Purpose: build dynamic system instructions tailored to the current `phase` and role `data` (persona, scenario, rubric, transitions).
  - Inputs: `phase` (GREETING|TUTORING|ROLEPLAY|GRADING), `data` (role record).

- `query_chain(retriever, llm, user_input: str, role_id: str, current_phase: str)`
  - Purpose: orchestrate RAG + prompt assembly + LLM invocation and return the model output.
  - Flow:
    1. Fetch role data (`fetch_roleplay_data`).
    2. Build `system_instructions` via `build_system_prompt`.
    3. Select `knowledge_base_content` (RAG only for TUTORING; static otherwise).
    4. Build prompt template and LangChain chain: `ChatPromptTemplate.from_template(...) | llm | StrOutputParser()`.
    5. Invoke the chain with mapping and return parsed result.
  - Notes: expects a LangChain-compatible `llm`. For non-LangChain LLMs implement an adapter or change `query_chain` to call `llm(prompt_text)`.

### `main.py`

- `render_advisor_grid(data: dict)`
  - Purpose: render advisor cards grid; each card contains image, title, description, and a chat button that navigates to `Destination`.
  - Input: `data` with lists `Title`, `Description`, `Image Path`, `Destination`.

- `mainpage()` / `mb_page()`
  - Purpose: simple pages for navigation; `mb_page` shows a sample advisor grid and sidebar.

- `cxo_page()`
  - Purpose: main chat interface:
    - Initialize `st.session_state` keys: `messages`, `phase`, `trigger_ai_greeting`, `retriever`, `llm`.
    - Lazily create vectorstore and LLM objects (calls `load_vectors()` and `get_retriever()`).
    - Sidebar: control phase transitions and trigger AI greetings.
    - Render history (`st.session_state.messages`) with `st.chat_message`.
    - Auto-trigger system message using `query_chain(..., user_input='[SYSTEM_TRIGGER_START]')` when `trigger_ai_greeting` is true.
    - Handle user input (`st.chat_input`) and append both user and assistant messages to history.

### Extension points & operational notes

- Replace `DUMMY_DB` with a persistent store and update `fetch_roleplay_data` accordingly.
- Provide a clear `LLMAdapter` interface when switching backends (Ollama / Gemini / other): prefer a callable `__call__(prompt_text)` or LangChain-compatible wrapper.
- Add an ingestion script to tokenize/extract `/uploaded_pdfs` and index into Chroma using the same embeddings used by `load_vectors()`.

---

## System-Only (No User Input) Triggers

`main.py` uses `user_input='[SYSTEM_TRIGGER_START]'` to signal `query_chain` to produce an auto message (e.g., greeting). `engine.build_system_prompt` generates phase-aware instructions, so `query_chain` can run without a meaningful user question. This works as-is.

If you prefer a cleaner API, modify `query_chain` signature to accept `user_input: Optional[str]=None` and build the prompt accordingly.

---

## Troubleshooting

- If LLM calls fail:
  - Verify env variables (API keys) and network access to model endpoints.
  - If using Ollama: ensure an Ollama server is running locally (default base_url in code: `http://localhost:11434`).
  - If using Gemini: ensure `google-generative-ai` is installed and `GEMINI_API_KEY` is valid.

- If Chroma errors on startup:
  - Confirm `PERSIST_DIR` is writable, and the process has permissions.

- Streamlit UI not showing expected buttons:
  - Check `st.session_state.phase` and `trigger_ai_greeting` initialization in `main.py`.

---

## Security & Operational Notes

- Never commit API keys or service account JSONs to the repo.
- Run the app behind a corporate firewall or in a VPC when using cloud LLMs.
- Rate-limiting and quotas: monitor Gemini usage carefully.
- Audit logs: consider adding structured logging for LLM calls and user interactions (already a logger exists in `engine.py`).

---

## Next steps & Suggestions for Production

1. Move `DUMMY_DB` to a proper datastore (e.g., SQLite, Postgres) and add migrations.
2. Add an ingestion script for `uploaded_pdfs/` that extracts text, creates embeddings, and stores them in Chroma.
3. Add CI checks and a `pre-commit` config.
4. Add a feature-flag / config switch to choose LLM backend (Ollama vs Gemini vs other).

---

## Contact / Maintainers

For deployment and operations questions, contact the project owner or the IT team responsible for AI & infra.

---

File references: see `main.py` and `engine.py` in the repository root for implementation details.
