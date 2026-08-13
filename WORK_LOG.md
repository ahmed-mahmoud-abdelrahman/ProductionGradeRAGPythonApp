# Project Development Log — Building the Production-Grade RAG AI Agent

**Project:** ProductionGradeRAGPythonApp  
**Author:** Ahmed Mahmoud  
**Repository:** [https://github.com/ahmed-mahmoud-abdelrahman/ProductionGradeRAGPythonApp](https://github.com/ahmed-mahmoud-abdelrahman/ProductionGradeRAGPythonApp)  

---

## 🎯 Project Goal & Motivation

The objective was to build a **production-ready, enterprise-grade Retrieval-Augmented Generation (RAG) system** in Python that goes beyond basic naive RAG scripts. Rather than relying on simple text lookup, the system needed to:
1. Support **intelligent AI Agent reasoning and planning** (dynamic decision making on whether to retrieve from documents or answer directly).
2. Store and search vectorized knowledge with high performance using **Qdrant Vector Database**.
3. Provide an **asynchronous event-driven workflow engine** using **FastAPI** and **Inngest** for background queueing and retries.
4. Deliver **full observability & evaluation** using **LangSmith Tracing** (tracing token usage, tool calls, and latency).
5. Feature an intuitive, **modern, colorful Streamlit Chat UI** with persistent multi-turn conversational memory, PDF ingestion, and collapsible step-by-step thinking traces.

---

## 🛠️ Complete "From Scratch" Development Timeline

### Phase 1: Environment & Project Foundation
- Initialized a modern Python project using **`uv`** and standard `pyproject.toml` configuration.
- Configured `.gitignore` to safeguard API keys, environment files (`.env`), cached models, and local vector storage folders (`qdrant_storage/`).
- Set up Docker containerization with `Dockerfile` and `docker-compose.yml` for unified local deployment of Qdrant and FastAPI.

### Phase 2: Ingestion & Document Processing (`data_loader.py`)
- Created a robust ingestion pipeline using `llama-index-readers-file` (via `PDFReader`) and `llama-index-core` (`SentenceSplitter`).
- Configured document chunking with a `chunk_size` of 512 tokens and `chunk_overlap` of 64 tokens.
- Implemented `embed_texts()` leveraging OpenAI's state-of-the-art embedding model (`text-embedding-3-large`, dimension 3072) with cosine distance.

### Phase 3: Vector Store Architecture (`vector_db.py`)
- Built `QdrantStorage` wrapper around `qdrant-client` targeting local or cloud Qdrant instances.
- Added automated collection initialization for 3072-dimensional vector collections with Cosine similarity.
- Added metadata-based payload filtering (enabling scoped search by source file name).
- Implemented safe error handling and collection management utilities (`clear_collection`, `upsert`, `search`).

### Phase 4: LangChain & LangGraph AI Agent (`agent.py`)
- Transitioned from static retrieval chains to a **dynamic reasoning Agent** utilizing LangChain and LangGraph paradigms.
- Defined explicit tool abstractions:
  - `search_qdrant_docs`: Performs semantic similarity lookup against Qdrant vectors and returns chunk texts with source attribution.
  - `inspect_indexed_documents`: Checks Qdrant collection status and vector count.
- Structured the Agent's system prompt with strict guidelines:
  1. **Think & Plan**: Determine intent before executing actions.
  2. **General Knowledge Mode**: Direct answers for calculations, code generation, and general inquiries without redundant database calls.
  3. **Document Grounding Mode**: Query Qdrant when context from uploaded files is required.
  4. **Transparent Traces**: Expose intermediate steps and tool outputs for user visibility.

### Phase 5: Observability with LangSmith
- Integrated `LangChainTracer` and project-level tracing into the agent runtime.
- Added dynamic API key handling (both from `.env` and live user inputs via the Streamlit interface).
- Traced full execution graphs including token counts, prompts, tool outputs, and execution duration.

### Phase 6: Asynchronous Event Workflows (`main.py` & Inngest)
- Implemented background event-driven RAG pipelines using Inngest and FastAPI (`rag/query_agent` events).
- Enabled durable background execution with automated step checkpoints, polling endpoints, and error handling.

### Phase 7: Modern Streamlit Chat Interface (`streamlit_app.py`)
- Replaced basic form inputs with a **multi-turn, scrollable chat experience** powered by `st.session_state.messages`.
- Designed a custom **Dark Glassmorphism UI** using bespoke CSS tokens, animated badges, and responsive containers.
- Implemented a collapsible **"💭 Agent Planning & Thinking Process"** expander that reveals the agent's real-time reasoning and tool executions.
- Added a sidebar with:
  - Drag-and-drop PDF file uploader with live chunking and vector indexing.
  - Real-time Qdrant connection status indicator and vector count.
  - LangSmith tracing credentials input and active status badge.
  - Execution mode toggle (Direct in-process vs. Inngest async workflow).

### Phase 8: Multi-Agent Scaffolding (`agents/`)
- Created modular agent stubs for orchestrating complex workflows:
  - `agents/coordinator.py`: Master orchestrator routing incoming user inquiries.
  - `agents/planner.py`: Sub-task breakdown and execution planning.
  - `agents/retriever.py`: Vector search and context filtering worker.
  - `agents/synthesizer.py`: Context fusion and response formatting.

---

## 💻 Essential Commands Reference

### 1. Starting Services (Qdrant & Inngest)
```bash
# Start Qdrant Vector DB container locally
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant

# Run Inngest Dev Server (Optional, for event workflows)
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

### 2. Running FastAPI Backend
```bash
# Run the FastAPI server
uvicorn main:app --reload --port 8000
```

### 3. Launching Streamlit Web App
```bash
# Launch the Streamlit chat UI
streamlit run streamlit_app.py
```
