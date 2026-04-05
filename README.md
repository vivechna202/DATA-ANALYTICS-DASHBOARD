# AI Analytics Dashboard

A small Flask app that answers natural-language questions about sales data (CSV + charts) and falls back to **RAG** (retrieval-augmented generation) over a PDF when the CSV layer does not understand the query.

## Features

- **CSV analytics** — Pandas reads `analytics_dashboard/data/sales.csv` and answers queries about totals, averages, and trends.
- **Charts** — Plotly line charts for sales trend queries; the front end renders them with Plotly.js.
- **RAG pipeline** — Loads `analytics_dashboard/data/documents/pdf-data.pdf`, chunks text, embeds with Sentence Transformers, stores vectors in **FAISS**, retrieves relevant chunks, and generates answers with **Google Gemini** (with a rule-based fallback if the API fails).
- **Single-page UI** — `index.html` with a query box and optional chart area.

## How it works

1. User submits a question from the browser (POST to `/query`).
2. **CSV path first** — `query_service.handle_query()` checks for keywords (`total sales`, `average sales`, `trend`). If matched, it returns text and optionally a Plotly chart JSON with `source: "csv"`.
3. **RAG path** — If the result is `Query not understood`, the app runs `RAGPipeline.query()`, which embeds the question, searches FAISS, calls the LLM with retrieved context, and returns `source: "rag"`.

```
User question
    → Flask (/query)
        → handle_query (CSV)
            → understood? → JSON + source: csv
            → not understood? → RAGPipeline → JSON + source: rag
```

## Project structure

```
mini_prj/
├── app.py                          # Flask entry: registers blueprint, serves index
├── config.py                       # Reserved for future settings (optional)
├── setup.py                        # Package metadata (setuptools)
├── requirements.txt
├── Dockerfile                      # Optional deployment (configure as needed)
├── .dockerignore
├── analytics_dashboard/
│   ├── data/
│   │   ├── sales.csv               # Sample monthly sales
│   │   └── documents/
│   │       └── pdf-data.pdf        # Document for RAG (required for RAG)
│   ├── routes/
│   │   └── query_routes.py         # POST /query, wires CSV then RAG
│   ├── services/
│   │   └── query_service.py        # CSV / Plotly logic
│   ├── rag/
│   │   ├── pipeline.py             # RAG orchestration
│   │   ├── pdf_loader.py           # PDF text extraction (pypdf)
│   │   ├── chunking.py             # Line-based chunking
│   │   ├── embeddings.py           # Sentence Transformers
│   │   ├── vector_store.py         # FAISS index
│   │   └── llm_generator.py        # Gemini + fallback answers
│   ├── templates/
│   │   └── index.html              # UI + fetch to /query
│   └── tests/
│       └── test_api.py             # Manual-style RAG script (not pytest)
```

Optional scaffolding for extra modules (extra routes, static JS bundles, notebooks) may be created via `template.py` at the repo root; only the layout above is required for the current app.

## Prerequisites

- Python 3.10+ recommended
- A **Google API key** with access to Gemini (for full RAG answers). The app can still return fallback text from retrieved chunks if the API fails.

## Environment variables

Create a `.env` file in the project root (same folder as `app.py`):

| Variable         | Purpose                                      |
|-----------------|----------------------------------------------|
| `GOOGLE_API_KEY` | Required for Gemini in `llm_generator.py`   |

Without `GOOGLE_API_KEY`, importing the LLM module will raise; ensure the key is set before starting the app if you use the current code as-is.

## Installation

From the project root (`mini_prj`):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
pip install -e .                  # optional: install analytics_dashboard as a package
```

## Run the app

Always start from the **project root** so paths like `analytics_dashboard/data/...` resolve correctly.

```bash
python app.py
```

Open the UI at `http://127.0.0.1:5000/`.

The first startup loads the embedding model and builds the FAISS index from the PDF (can take a minute).

## API

### `POST /query`

**Request** — JSON:

```json
{ "query": "your question here" }
```

**Response (CSV)** — Example fields:

- `answer` — Text reply
- `chart` — Optional Plotly figure JSON string (for trend queries)
- `source` — `"csv"`

**Response (RAG)**:

- `answer` — Model or fallback text
- `source` — `"rag"`

**Error** — `500` with `{ "error": "..." }`.

### Example CSV queries

| Intent        | Example phrase   | Notes                    |
|---------------|------------------|--------------------------|
| Total sales   | contains `total sales` | Sum of `sales` column |
| Average sales | contains `average sales` | Mean of `sales`      |
| Trend chart   | contains `trend` | Line chart date vs sales |

Anything else is treated as not understood and is sent to RAG.

## Front end

`analytics_dashboard/templates/index.html` calls `http://127.0.0.1:5000/query`. For deployment behind another host or port, change the fetch URL to a **relative** path (`/query`) so the same origin is used.

## Tech stack

| Layer        | Technology                          |
|-------------|--------------------------------------|
| Web         | Flask, Jinja templates               |
| Data        | Pandas, CSV                          |
| Charts      | Plotly (Python) + Plotly.js (CDN)    |
| Embeddings  | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS (`IndexFlatL2`)              |
| PDF         | pypdf (`PdfReader`)                  |
| LLM         | Google GenAI (Gemini Flash family)   |

## Docker

`Dockerfile` and `.dockerignore` are present but not fully configured; add install steps, `COPY`, `ENV`, and `CMD`/`ENTRYPOINT` when you containerize the app.

## License / author

Package metadata is in `setup.py` (author: Vivechana Singh).
