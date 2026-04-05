"""Load CSV and convert rows into line-oriented text for RAG."""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_MAX_ROWS = 50_000


def load_csv_source(path: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    path = os.path.abspath(os.path.normpath(path))
    if not os.path.isfile(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    max_rows = max(1, min(int(max_rows), DEFAULT_MAX_ROWS))
    logger.info("Loading CSV: %s (max_rows=%s)", path, max_rows)

    df = pd.read_csv(path, nrows=max_rows)
    if df.empty:
        raise ValueError("CSV file is empty")

    lines = []
    for _, row in df.iterrows():
        parts = [f"{col}={row[col]}" for col in df.columns]
        lines.append(" | ".join(parts))

    return "\n".join(lines)
