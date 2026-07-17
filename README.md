# Safran R&D Knowledge Assistant

An on-premise, CPU-only Python knowledge assistant for searching Safran Electronics & Defense R&D documents. It ingests PDF, Word, and PowerPoint files from a local folder or SharePoint, stores extracted text in SQLite, builds a BM25 search index, and serves ranked, summarised results in Streamlit.

No runtime external AI APIs are used. Optional vector search requires a local sentence-transformers model directory already present on the company network.

## Architecture

```text
SharePoint / Local Folder
        |
        v
IngestPipeline -> PDF/DOCX/PPTX Extractors -> SQLite projects/chunks/keywords
        |                                      |
        v                                      v
 BM25 pickle index                    Optional FAISS vector index
        \                                      /
         \                                    /
          v                                  v
        HybridEngine -> Ranker -> AnswerGenerator -> ResponseBuilder -> Streamlit UI
```

## Quickstart

```bash
cd safran-knowledge-assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/create_sample_docs.py
python scripts/ingest_local.py --path ./sample_docs --reset
streamlit run ui/app.py
```

On Linux/macOS, use `source .venv/bin/activate` instead of the Windows activation command.

## SharePoint Configuration

Set these values in `.env`:

```text
SHAREPOINT_URL=https://your-sharepoint-site
SHAREPOINT_USERNAME=DOMAIN\user
SHAREPOINT_PASSWORD=your-password
SHAREPOINT_LIBRARY=Documents
```

Run:

```bash
python scripts/ingest_sharepoint.py --check
python scripts/ingest_sharepoint.py
```

Use `--check` first to validate credentials and list the first files found in the library. The client treats URLs containing `.sharepoint.com` as SharePoint Online. Other URLs are treated as on-premise deployments and currently use username/password auth through the Office365 client library; if your on-premise deployment requires NTLM or Kerberos, add the company-approved auth adapter before ingestion. Failures are logged and skipped so one unreadable file does not stop a full ingestion run.

## Vector Search

Vector search is disabled by default. To enable it offline:

1. Download a compatible sentence-transformers model on an internet-enabled machine.
2. Move the full model directory onto the company network.
3. Install optional wheels from the local package mirror: `sentence-transformers`, `faiss-cpu`.
4. Set:

```text
EMBEDDING_MODEL_PATH=./models/all-MiniLM-L6-v2
USE_VECTOR_SEARCH=true
```

Then rebuild indexes:

```bash
python scripts/rebuild_index.py
```

## Local LLM

The assistant can use a local-only model when a model file is configured. It supports `ctransformers` and `llama-cpp-python` backends and falls back to extractive grounded answers when no model is available.

Example `.env` configuration:

```text
LOCAL_LLM_PATH=./models/mistral-7b-instruct.Q4_K_M.gguf
LOCAL_LLM_BACKEND=ctransformers
LOCAL_LLM_MODEL_TYPE=mistral
LOCAL_LLM_MAX_NEW_TOKENS=320
LOCAL_LLM_CONTEXT_CHARS=6000
```

For `llama-cpp-python`, use:

```text
LOCAL_LLM_BACKEND=llama-cpp
LOCAL_LLM_PATH=./models/your-model.gguf
```

Model files must be copied into the company network ahead of time. The application does not download models at runtime.

## Folder Structure

```text
config.py                  Environment-backed settings
db/                        SQLite schema, models, and access wrapper
ingest/                    SharePoint/local ingestion and extractors
search/                    BM25, optional vector search, hybrid merge, reranking
assistant/                 Query parsing, summarisation, response assembly
ui/app.py                  Streamlit application
scripts/                   Operational CLIs
tests/                     Pytest coverage
```

## Tests

```bash
pytest
```

The tests create synthetic DOCX/PPTX documents and exercise BM25 and end-to-end local ingestion.

## Known Limitations And Roadmap

- PDF image-only pages are skipped; OCR can be added later with an approved offline OCR engine.
- SharePoint metadata availability varies by deployment; local ingestion uses filesystem modified time.
- The default answer generator is extractive and grounded in retrieved chunks. It provides citations and limitations, but does not yet use a local LLM.
- Vector search requires optional dependencies and a local model directory.
- Access control filtering is not implemented; deploy behind existing internal controls or add per-document ACL metadata before broad rollout.

## Current Answer Format

The UI now shows a direct grounded answer first, followed by confidence, limitations, source citations, and expandable evidence chunks. The raw snippets are still available for auditability, but they are no longer the primary answer surface.

Use `python scripts/create_sample_docs.py` to generate local demo files covering radar FPGA processing, UAV navigation, and inertial/GNSS sensor fusion.
