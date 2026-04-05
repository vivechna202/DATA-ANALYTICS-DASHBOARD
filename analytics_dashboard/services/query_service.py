"""Query routing: CSV analytics (default) + dynamic-source RAG with caching."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.express as px

from analytics_dashboard.rag.pipeline import RAGPipeline
from analytics_dashboard.services.pipeline_cache import get_pipeline_cache, make_cache_key
from analytics_dashboard.sources.loader import load_data

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = "analytics_dashboard/data/sales.csv"
DEFAULT_PDF_PATH = "analytics_dashboard/data/documents/pdf-data.pdf"

_df_default = pd.read_csv(DEFAULT_CSV_PATH)
_default_rag_pipeline: RAGPipeline | None = None


def _get_default_rag_pipeline() -> RAGPipeline:
    """Lazy singleton for auto mode (backward compatible with fixed PDF)."""
    global _default_rag_pipeline
    if _default_rag_pipeline is None:
        logger.info("Initializing default RAG pipeline: %s", DEFAULT_PDF_PATH)
        _default_rag_pipeline = RAGPipeline(DEFAULT_PDF_PATH)
    return _default_rag_pipeline


def handle_analytical_query(query_lower: str, df: pd.DataFrame) -> dict[str, Any]:
    """Keyword-based analytics on a dataframe (default sales CSV in auto mode)."""
    if "total sales" in query_lower:
        total = df["sales"].sum()
        return {"answer": f"Total sales is {total}"}

    if "average sales" in query_lower:
        avg = df["sales"].mean()
        return {"answer": f"Average sales is {avg:.2f}"}

    if "trend" in query_lower:
        fig = px.line(df, x="date", y="sales", title="Sales Trend")
        return {
            "answer": "Here is the sales trend",
            "chart": fig.to_json(),
        }

    return {"message": "Query not understood"}


def _mongo_options_from_request(
    mongo_database: str | None,
    mongo_collection: str | None,
    mongo_limit: int | None,
) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    if mongo_database is not None:
        opts["mongo_database"] = mongo_database
    if mongo_collection is not None:
        opts["mongo_collection"] = mongo_collection
    if mongo_limit is not None:
        opts["mongo_limit"] = int(mongo_limit)
    return opts


def process_query(
    user_query: str,
    *,
    source_type: str = "auto",
    source_input: str | None = None,
    mongo_database: str | None = None,
    mongo_collection: str | None = None,
    mongo_limit: int | None = None,
) -> dict[str, Any]:
    """
    Main entry for /query.

    - auto: try default CSV analytics, then default PDF RAG (existing behavior).
    - pdf / csv / mongo: load text via load_data, reuse cached RAGPipeline when possible.
    """
    user_query = (user_query or "").strip()
    if not user_query:
        return {"error": "query must not be empty"}

    st = (source_type or "auto").lower().strip()

    if st == "auto":
        analytical = handle_analytical_query(user_query.lower(), _df_default)
        if analytical.get("message") != "Query not understood":
            analytical["source"] = "csv"
            return analytical

        rag = _get_default_rag_pipeline()
        out = rag.query(user_query)
        return {"answer": out["answer"], "source": "rag"}

    if st not in ("pdf", "csv", "mongo"):
        return {"error": f"Invalid source_type: {source_type}. Use auto, pdf, csv, or mongo."}

    mongo_opts = _mongo_options_from_request(mongo_database, mongo_collection, mongo_limit)

    try:
        text = load_data(st, source_input, **mongo_opts)
    except Exception as e:
        logger.exception("Failed to load data for source=%s", st)
        return {"error": str(e), "source": st}

    cache = get_pipeline_cache()
    cache_key = make_cache_key(st, str(source_input), mongo_opts)

    def build_pipeline() -> RAGPipeline:
        logger.info("Building cached RAG pipeline for source=%s", st)
        return RAGPipeline.from_text(text)

    try:
        pipeline = cache.get_or_build(cache_key, build_pipeline)
    except Exception as e:
        logger.exception("Failed to build RAG pipeline")
        return {"error": str(e), "source": st}

    out = pipeline.query(user_query)
    return {
        "answer": out["answer"],
        "source": f"rag:{st}",
    }
