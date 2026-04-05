"""Unified entry point for loading text from PDF, CSV, or MongoDB."""

import logging
from typing import Any

from analytics_dashboard.sources import csv_handler, mongo_handler, pdf_handler

logger = logging.getLogger(__name__)


def _strip_wrapping_quotes(value: str) -> str:
    """Remove outer matching quotes often pasted from File Explorer or docs."""
    s = value.strip()
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1].strip()
    return s


def normalize_source_input(raw: str | None) -> str | None:
    """Same cleaning as load_data uses (paths / URIs); use for cache keys and display."""
    if raw is None:
        return None
    out = _strip_wrapping_quotes(str(raw))
    return out or None


def load_data(source_type: str, source_input: str | None, **options: Any) -> str:
    """
    Load content and return a single string suitable for chunking and embedding.

    :param source_type: One of: pdf, csv, mongo
    :param source_input: File path (pdf/csv) or MongoDB connection URI (mongo)
    :param options: For mongo: mongo_database, mongo_collection, mongo_limit.
                    For csv: max_rows (optional, capped in handler).
    """
    if not source_type:
        raise ValueError("source_type is required")

    st = source_type.lower().strip()

    if st not in ("pdf", "csv", "mongo"):
        raise ValueError(f"Unsupported source_type: {source_type}. Use pdf, csv, or mongo.")

    if source_input is None or not str(source_input).strip():
        raise ValueError("source_input (path or URI) is required for this source type")

    source_input = _strip_wrapping_quotes(str(source_input))

    if st == "pdf":
        return pdf_handler.load_pdf_source(source_input)

    if st == "csv":
        max_rows = options.get("max_rows", csv_handler.DEFAULT_MAX_ROWS)
        return csv_handler.load_csv_source(source_input, max_rows=max_rows)

    if st == "mongo":
        return mongo_handler.load_mongo_source(
            source_input,
            database=options.get("mongo_database"),
            collection=options.get("mongo_collection"),
            limit=options.get("mongo_limit", mongo_handler.DEFAULT_LIMIT),
        )

    raise ValueError(f"Unsupported source_type: {source_type}")
