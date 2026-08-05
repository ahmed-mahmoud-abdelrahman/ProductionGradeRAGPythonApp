# Work Log — What I built from scratch

Project: ProductionGradeRAGPythonApp

This document describes the project contents and the likely steps taken to build it from scratch (inferred from the repository files). Use this as the authoritative log to edit with any additional, personal details you want preserved.

## Overview
- Purpose: A retrieval-augmented generation (RAG) Python app with local vector storage and a Streamlit UI.
- Main components: data ingestion, vector store interface, Qdrant-based storage, a Streamlit frontend, and Docker support.

## Files (summary)
- [custom_types.py](custom_types.py): project-specific dataclasses and typed aliases.
- [data_loader.py](data_loader.py): ingestion and preprocessing of source documents.
- [vector_db.py](vector_db.py): vector database adapter / helper functions.
- [main.py](main.py): application entrypoint or CLI (if present).
- [streamlit_app.py](streamlit_app.py): Streamlit-based UI for queries and demos.
- [Dockerfile](Dockerfile) & [docker-compose.yml](docker-compose.yml): containerization and local services.
- [qdrant_storage/](qdrant_storage/): local Qdrant data and shards (used by the vector store).

## Reconstructed "From Scratch" Steps
1. Created a new Python project and virtual environment (e.g. `python -m venv .venv`).
2. Added `pyproject.toml` for dependency management and basic metadata.
3. Implemented data ingestion in `data_loader.py` to read, clean, and chunk source documents.
4. Implemented `vector_db.py` to wrap vector store operations (index, upsert, search).
5. Created domain types in `custom_types.py` for structured data.
6. Added a Streamlit UI (`streamlit_app.py`) to demonstrate querying and RAG flows.
7. Added a local Qdrant folder (`qdrant_storage/`) to persist vectors during development.
8. Wrote a `Dockerfile` and `docker-compose.yml` to run the app and any services (Qdrant, etc.) in containers.
9. Tested locally and iterated on pipelines and UI.

## How to Run Locally (typical steps)
1. Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt  # or `pip install -e .` if package-style
```

2. If using Docker compose:

```bash
docker-compose up --build
```

3. To run Streamlit locally:

```bash
streamlit run streamlit_app.py
```

