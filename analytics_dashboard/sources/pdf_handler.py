"""Load plain text from a PDF file path."""

import logging
import os

from analytics_dashboard.rag.pdf_loader import load_pdf

logger = logging.getLogger(__name__)


def load_pdf_source(path: str) -> str:
    path = os.path.abspath(os.path.normpath(path))
    if not os.path.isfile(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    logger.info("Loading PDF: %s", path)
    text = load_pdf(path)
    if not text or not str(text).strip():
        raise ValueError("PDF contained no extractable text")
    return text
