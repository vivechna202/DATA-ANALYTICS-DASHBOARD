import logging
import os
import re
from typing import Iterable

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

# Prefer GEMINI_API_KEY so a fresh AI Studio key can override a leaked GOOGLE_API_KEY.
api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

if not api_key:
    raise ValueError(
        "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file "
        "(Google AI Studio: https://aistudio.google.com/apikey)."
    )

client = genai.Client(api_key=api_key)

# Models to try if listing fails or a specific id errors (403 / not found).
_STATIC_MODEL_CANDIDATES = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
)

_STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of is are was were be been being
    what which who how when where why does do did can could should would
    will with from into about tell me give show list find falls product
    """.split()
)


def _normalize_model_id(name: str) -> str:
    if not name:
        return name
    return name.removeprefix("models/").strip()


def get_available_flash_model() -> str:
    """Pick a Flash-style model from the API list, or fall back to a static id."""
    try:
        logger.info("Fetching available Gemini models...")
        models = client.models.list()
        available = [_normalize_model_id(m.name) for m in models]

        for name in available:
            if "gemini-2.5-flash" in name and "image" not in name.lower():
                logger.info("Using model: %s", name)
                return name
        for name in available:
            if "gemini-2.0-flash" in name:
                logger.info("Using model: %s", name)
                return name
        for name in available:
            if "flash" in name.lower() and "embedding" not in name.lower():
                logger.info("Using model: %s", name)
                return name

        logger.warning("No flash model in list; using %s", _STATIC_MODEL_CANDIDATES[0])
        return _STATIC_MODEL_CANDIDATES[0]
    except Exception as e:
        logger.warning("Could not list models (%s); using static fallback", e)
        return _STATIC_MODEL_CANDIDATES[0]


_SELECTED_MODEL: str | None = None


def _resolve_model() -> str:
    global _SELECTED_MODEL
    if _SELECTED_MODEL is None:
        _SELECTED_MODEL = get_available_flash_model()
    return _SELECTED_MODEL


def _models_to_try() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in (_resolve_model(),) + _STATIC_MODEL_CANDIDATES:
        m = _normalize_model_id(m)
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def generate_answer(query: str, context_chunks: Iterable[str]) -> str:
    """
    Generate an answer with Gemini. On failure, use structured fallback from chunks.
    """
    chunks = list(context_chunks)
    context = "\n\n".join(chunks)

    prompt = f"""
You are a smart data analyst. Use ONLY the context below.

Context:
{context}

Question:
{query}

Answer:
"""

    last_error: Exception | None = None
    for model in _models_to_try():
        try:
            logger.info("LLM request model=%s", model)
            response = client.models.generate_content(model=model, contents=prompt)

            if response and hasattr(response, "text") and response.text:
                return response.text.strip()
            last_error = ValueError("Empty response from model")
        except Exception as e:
            last_error = e
            logger.warning("LLM error for model %s: %s", model, e)
            continue

    if last_error:
        logger.error("All LLM attempts failed: %s", last_error)

    fallback_answer = build_fallback_answer(query, chunks)
    return (
        "⚠️ LLM unavailable (fallback mode)\n\n"
        "Common causes: invalid or leaked API key (create a new key in Google AI Studio), "
        "quota exceeded, or network issues. Check the server log for details.\n\n"
        f"📌 Answer (from retrieved context):\n{fallback_answer}"
    )


def _split_records(text: str) -> list[str]:
    """Split Mongo-style --- separators or paragraph blocks into records."""
    parts = re.split(r"\n-{3,}\n", text)
    if len(parts) <= 1:
        parts = re.split(r"\n\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _query_keywords(query_lower: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", query_lower)
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def build_fallback_answer(query: str, chunks: list[str]) -> str:
    """Best-effort answers without the LLM from key=value style context."""
    query_lower = query.lower()
    full = "\n\n".join(chunks)
    records = _split_records(full)

    # --- Category / product questions ---
    if "category" in query_lower:
        kws = _query_keywords(query_lower)
        for rec in records:
            m = re.search(r"(?im)^product=(.+)$", rec)
            if not m:
                continue
            pname = m.group(1).strip().lower()
            pname_tokens = [t for t in re.findall(r"[a-z0-9]+", pname) if len(t) > 2]
            if pname_tokens and all(t in query_lower for t in pname_tokens):
                cats = re.findall(r"(?im)^category=(.+)$", rec)
                if cats:
                    uniq = []
                    for c in cats:
                        c = c.strip()
                        if c and c not in uniq:
                            uniq.append(c)
                    if len(uniq) == 1:
                        return f"Category for “{m.group(1).strip()}”: {uniq[0]}"
                    return (
                        f"Category for “{m.group(1).strip()}” (multiple values in data — pick the correct one):\n"
                        + "\n".join(f"  • {c}" for c in uniq)
                    )

    # --- Date / sales row (CSV-style) ---
    if "date" in query_lower or "sale" in query_lower:
        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", query)
        if m_date:
            d = m_date.group(1)
            for rec in records:
                if d in rec and ("sales" in rec.lower() or "price" in rec.lower() or "stock" in rec.lower()):
                    lines = [ln.strip() for ln in rec.splitlines() if ln.strip()]
                    return "\n".join(lines[:12])

    # --- Highest stock (legacy PDF table heuristic) ---
    if "highest stock" in query_lower or "high stock" in query_lower:
        max_stock = -1
        best_line = ""
        for chunk in chunks:
            for line in chunk.split("\n"):
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        stock = int(parts[-1])
                        if stock > max_stock:
                            max_stock = stock
                            best_line = line
                    except ValueError:
                        continue
        if best_line:
            return f"Product with highest stock:\n{best_line}"

    # --- Keyword-focused snippet ---
    kws = _query_keywords(query_lower)
    if kws:
        best_rec = ""
        best_score = 0
        for rec in records:
            rl = rec.lower()
            score = sum(1 for w in kws if w in rl)
            if score > best_score:
                best_score = score
                best_rec = rec
        if best_rec and best_score > 0:
            return best_rec[:4000] + ("…" if len(best_rec) > 4000 else "")

    return "\n\n".join(chunks[:2])
