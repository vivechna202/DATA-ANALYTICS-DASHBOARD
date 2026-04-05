# AI Analytics Dashboard

Flask app for **analytics-style questions** over CSV (with charts), plus **RAG** over **PDF**, **CSV-as-text**, or **MongoDB** using Sentence Transformers, **FAISS**, and **Google Gemini** (with structured fallback if the API fails).

## Features

- **Auto mode (default)** — Keyword analytics on `analytics_dashboard/data/sales.csv` (totals, averages, trend chart). If the query does not match, RAG runs on the default PDF (`analytics_dashboard/data/documents/pdf-data.pdf`).
- **Explicit sources** — Choose **PDF path**, **CSV path** (rows turned into text for RAG), or **MongoDB URI** (documents turned into text). Pipelines are **cached** when the same source is reused.
- **RAG** — Chunk → embed (`all-MiniLM-L6-v2`) → FAISS → retrieve → **Gemini** answer (retries multiple Flash model ids; fallback uses heuristics on retrieved text).
- **UI** — Single page: data source dropdown, path/URI field, optional Mongo fields, question box; uses **`POST /query`** (relative URL).

## How it works

### `source_type`: `auto` (default)

1. `POST /query` with `{ "query": "..." }` (optionally omit `source_type` or set `"auto"`).
2. **CSV keywords** — Phrases containing `total sales`, `average sales`, or `trend` → Pandas + optional Plotly chart → `source: "csv"`.
3. **Else** — Default PDF RAG → `source: "rag"`.

### `source_type`: `pdf` | `csv` | `mongo`

1. Send `source_type` and `source_input` (file path or MongoDB URI).
2. Data is loaded via `analytics_dashboard.sources.load_data()` → text → `RAGPipeline.from_text()` (cached per source key) → answer → `source: "rag:pdf"` (or `csv` / `mongo`).

```
auto:   query → CSV rules? → else default PDF RAG
pdf/csv/mongo:  query → load_data → cached RAG → answer
```

## Project structure

```
mini_prj/
├── app.py
├── setup.py
├── requirements.txt
├── .env                         # create locally: API keys (not committed)
├── analytics_dashboard/
│   ├── data/
│   │   ├── sales.csv
│   │   └── documents/
│   │       └── pdf-data.pdf     # default RAG doc for auto mode
│   ├── sources/
│   │   ├── loader.py            # load_data(source_type, source_input, **opts)
│   │   ├── pdf_handler.py
│   │   ├── csv_handler.py
│   │   └── mongo_handler.py
│   ├── routes/
│   │   └── query_routes.py      # POST /query
│   ├── services/
│   │   ├── query_service.py     # process_query, auto vs explicit sources
│   │   └── pipeline_cache.py    # LRU cache for RAG pipelines
│   ├── rag/
│   │   ├── pipeline.py          # RAGPipeline(file_path) | from_text(text)
│   │   ├── pdf_loader.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── llm_generator.py     # Gemini + fallback
│   ├── templates/
│   │   └── index.html
│   └── tests/
│       └── test_api.py
```

## Prerequisites

- Python 3.10+
- **Google AI Studio API key** for Gemini ([get a key](https://aistudio.google.com/apikey)). Revoked or “leaked” keys will not work; create a new key if you see `403` / “LLM unavailable”.
- **MongoDB** (only if you use the Mongo source): cluster URI and **`pymongo`** installed (`requirements.txt` includes it).

## Environment variables

Create `.env` next to `app.py`:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | **Preferred** — Gemini API key from AI Studio. |
| `GOOGLE_API_KEY` | Alternative if `GEMINI_API_KEY` is not set. |

If neither is set, the app raises on import when loading `llm_generator`.

## Installation

```bash
cd mini_prj
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
pip install -e .                # optional editable install
```

## Run

From the **project root** (`mini_prj`):

```bash
python app.py
```

Open `http://127.0.0.1:5000/`.

The first RAG use downloads/embeds models and may take a minute. **File paths** can be relative to the project root or absolute. Do not wrap paths in quotes in the UI (or use quotes — the server strips common wrapping quotes).

## API

### `POST /query`

**Headers:** `Content-Type: application/json`

**Body (examples):**

```json
{ "query": "total sales" }
```

```json
{
  "query": "What category is Wireless Mouse?",
  "source_type": "mongo",
  "source_input": "mongodb+srv://user:pass@cluster.example.net/",
  "mongo_database": "mydb",
  "mongo_collection": "products",
  "mongo_limit": 5000
}
```

```json
{
  "query": "Summarize discounts in the file.",
  "source_type": "pdf",
  "source_input": "analytics_dashboard/data/documents/pdf-data.pdf"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `query` | Yes | User question. |
| `source_type` | No | `auto` (default), `pdf`, `csv`, or `mongo`. |
| `source_input` | For `pdf` / `csv` / `mongo` | File path or MongoDB URI. |
| `mongo_database` | Sometimes | If not part of the URI path. |
| `mongo_collection` | For Mongo | Collection name. |
| `mongo_limit` | No | Max documents (capped in code). |

**Success:** `answer`, optional `chart` (Plotly JSON string), `source` (`csv`, `rag`, or `rag:pdf` / `rag:csv` / `rag:mongo`).

**Error:** HTTP **400** with `{ "error": "..." }`.

### Auto mode — CSV keyword hints

| Intent | Example phrase contains |
|--------|-------------------------|
| Total | `total sales` |
| Average | `average sales` |
| Trend chart | `trend` |

Other phrasing in auto mode goes to default PDF RAG.

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `LLM unavailable (fallback mode)` | Check API key, quota, and server logs. Prefer `GEMINI_API_KEY` with a **new** key if the old one was disabled. |
| `CSV not found` / bad path | Run `python app.py` from project root; use valid paths; avoid broken copy-paste (quotes are stripped, but path must be complete, e.g. ends in `.csv`). |
| Mongo errors | Install deps; check URI, database, collection, and network allowlist for Atlas. |

## Tech stack

| Layer | Technology |
|-------|------------|
| Web | Flask, Jinja |
| Data | Pandas, CSV, PyMongo (Mongo source) |
| Charts | Plotly + Plotly.js |
| Embeddings | sentence-transformers |
| Vectors | FAISS |
| PDF | pypdf |
| LLM | `google-genai` (Gemini) |

## Docker

`Dockerfile` / `.dockerignore` may be empty or minimal; add image build steps when you deploy.

## Author

See `setup.py` for package metadata.
