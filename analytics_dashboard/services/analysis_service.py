"""Keyword-driven dataframe analysis (no LLM). Returns text + optional plot payload."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Intent keyword groups
_TOP_WORDS = frozenset(("highest", "max", "top", "largest", "greatest", "biggest"))
_LOW_WORDS = frozenset(("lowest", "min", "bottom", "smallest", "least"))
_AVG_WORDS = frozenset(("average", "mean", "avg"))
_COUNT_PHRASES = ("how many", "number of")
_COUNT_WORDS = frozenset(("count",))
_TOTAL_WORDS = frozenset(("total", "sum", "overall"))
_TREND_PHRASES = ("over time", "sales over time", "trend", "time series", "by month", "by date")
_TREND_WORDS = frozenset(("trend", "timeline", "evolution"))
_DIST_PHRASES = (
    "category distribution",
    "distribution of",
    "distribution by",
    "breakdown",
    "proportion of",
    "share of",
    "split by",
)
_DATE_HINTS = frozenset(("date", "time", "day", "week", "month", "year"))

_ENTITY_HINTS = ("product", "item", "name", "sku", "title", "region", "store", "customer")
_METRIC_HINTS = (
    "sales",
    "revenue",
    "price",
    "stock",
    "quantity",
    "qty",
    "amount",
    "value",
    "total",
    "units",
)


def _lower_map(df: pd.DataFrame) -> dict[str, str]:
    return {str(c).lower(): c for c in df.columns}


def _word_in_query(q: str, word: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", q))


def _any_words(q: str, words: frozenset[str]) -> bool:
    return any(_word_in_query(q, w) for w in words)


def _any_phrase(q: str, phrases: tuple[str, ...]) -> bool:
    return any(p in q for p in phrases)


def _is_numeric_series(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s)


def _find_date_column(df: pd.DataFrame) -> str | None:
    colmap = _lower_map(df)
    for hint in ("date", "time", "timestamp", "month", "year", "day"):
        for low, orig in colmap.items():
            if hint in low.replace("_", " "):
                return orig
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    for c in df.columns:
        if "date" in str(c).lower() or "time" in str(c).lower():
            parsed = pd.to_datetime(df[c], errors="coerce")
            if parsed.notna().mean() >= 0.8:
                return c
    return None


def _find_category_column(df: pd.DataFrame, exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    colmap = _lower_map(df)
    for hint in ("category", "type", "segment", "group", "class", "department"):
        for low, orig in colmap.items():
            if orig in exclude:
                continue
            if hint in low.replace("_", " "):
                return orig
    best: tuple[int, str] | None = None
    for c in df.columns:
        if c in exclude or _is_numeric_series(df[c]):
            continue
        nu = df[c].nunique(dropna=True)
        if nu <= 1 or nu > min(len(df), 200):
            continue
        if best is None or nu < best[0]:
            best = (int(nu), c)
    return best[1] if best else None


def _metric_column(df: pd.DataFrame, query_lower: str, exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    colmap = _lower_map(df)
    for low, orig in colmap.items():
        if orig in exclude or not _is_numeric_series(df[orig]):
            continue
        for part in low.replace("_", " ").split():
            if len(part) >= 3 and part in query_lower:
                return orig
    for hint in _METRIC_HINTS:
        for low, orig in colmap.items():
            if orig in exclude:
                continue
            if hint in low.replace("_", " ") and _is_numeric_series(df[orig]):
                return orig
    for c in df.columns:
        if c in exclude:
            continue
        if _is_numeric_series(df[c]):
            return c
    return None


def _entity_column(
    df: pd.DataFrame,
    query_lower: str,
    metric_col: str | None,
    exclude: set[str] | None = None,
) -> str | None:
    exclude = {x for x in (exclude or set()) if x}
    if metric_col:
        exclude.add(metric_col)
    colmap = _lower_map(df)
    for hint in _ENTITY_HINTS:
        for low, orig in colmap.items():
            if orig in exclude:
                continue
            if hint in low.replace("_", " "):
                return orig
    for low, orig in colmap.items():
        if orig in exclude:
            continue
        if not _is_numeric_series(df[orig]) and df[orig].nunique(dropna=True) > 1:
            return orig
    return None


def _parse_top_n(query_lower: str, default: int = 5) -> int:
    m = re.search(r"\btop\s+(\d+)\b", query_lower)
    if m:
        return max(1, int(m.group(1)))
    m = re.search(r"\b(first|last)\s+(\d+)\b", query_lower)
    if m:
        return max(1, int(m.group(2)))
    m = re.search(r"\b(\d+)\s+(products?|items?|rows?|records?)\b", query_lower)
    if m:
        return max(1, int(m.group(1)))
    return default


def _coerce_datetime_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    return pd.to_datetime(s, errors="coerce")


def analyze_dataframe(df: pd.DataFrame, user_query: str) -> dict[str, Any] | None:
    """
    Detect intent from keywords. Returns None if no supported intent matches.

    On success returns:
      { "text_answer": str, "plot_data": dict | None }
    plot_data keys: type (bar|line|pie), x, y, optional title.
    """
    if df is None or df.empty:
        return None

    q = (user_query or "").strip().lower()
    if not q:
        return None

    date_col = _find_date_column(df)
    cat_col = _find_category_column(df, exclude={date_col} if date_col else set())
    metric_col = _metric_column(df, q)

    # --- Category distribution / pie ---
    wants_dist = any(p in q for p in _DIST_PHRASES) or (
        "pie" in q and cat_col is not None
    )
    if wants_dist and cat_col:
        vc = df[cat_col].value_counts(dropna=True).head(50)
        if vc.empty:
            return {
                "text_answer": f"No values to chart for column “{cat_col}”.",
                "plot_data": None,
            }
        text_answer = (
            f"Distribution by {cat_col} (top {len(vc)} values): "
            + ", ".join(f"{idx}: {int(v)}" for idx, v in vc.items())
        )
        return {
            "text_answer": text_answer,
            "plot_data": {
                "type": "pie",
                "x": vc.index.astype(str).tolist(),
                "y": vc.astype(float).tolist(),
                "title": f"{cat_col} distribution",
            },
        }

    # --- Trend / time series ---
    trend_phrase = _any_phrase(q, _TREND_PHRASES)
    trend_word = _any_words(q, _TREND_WORDS)
    date_in_q = any(_word_in_query(q, d) for d in _DATE_HINTS)
    if (trend_phrase or trend_word or ("over" in q and "time" in q)) and date_col:
        mcol = metric_col or _metric_column(df, "sales revenue price amount value", exclude={date_col})
        if not mcol:
            return {
                "text_answer": "A date column was found, but no numeric metric column to plot over time.",
                "plot_data": None,
            }
        sub = df[[date_col, mcol]].dropna().copy()
        sub[date_col] = _coerce_datetime_series(sub[date_col])
        sub = sub.dropna(subset=[date_col])
        sub = sub.sort_values(date_col)
        text_answer = f"{mcol} over {date_col} ({len(sub)} points)."
        return {
            "text_answer": text_answer,
            "plot_data": {
                "type": "line",
                "x": sub[date_col].astype(str).tolist(),
                "y": sub[mcol].astype(float).tolist(),
                "title": f"{mcol} over time",
            },
        }
    if date_in_q and date_col and metric_col:
        sub = df[[date_col, metric_col]].dropna().copy()
        sub[date_col] = _coerce_datetime_series(sub[date_col])
        sub = sub.dropna(subset=[date_col]).sort_values(date_col)
        return {
            "text_answer": f"{metric_col} by {date_col} ({len(sub)} points).",
            "plot_data": {
                "type": "line",
                "x": sub[date_col].astype(str).tolist(),
                "y": sub[metric_col].astype(float).tolist(),
                "title": f"{metric_col} over {date_col}",
            },
        }

    # --- Top / highest / max ---
    if _any_words(q, _TOP_WORDS) and metric_col:
        n = _parse_top_n(q, default=5)
        ex = {date_col} if date_col else set()
        ent = _entity_column(df, q, metric_col, exclude=ex)
        if ent:
            ser = (
                df.groupby(ent, dropna=True)[metric_col]
                .sum()
                .sort_values(ascending=False)
                .head(n)
            )
            labels = ser.index.astype(str).tolist()
            values = ser.astype(float).tolist()
        else:
            ser = df[metric_col].sort_values(ascending=False).head(n)
            labels = ser.index.astype(str).tolist()
            values = ser.astype(float).tolist()
        text_answer = f"Top {len(labels)} by {metric_col}: " + ", ".join(
            f"{l}: {v:g}" for l, v in zip(labels, values)
        )
        return {
            "text_answer": text_answer,
            "plot_data": {
                "type": "bar",
                "x": labels,
                "y": values,
                "title": f"Top {len(labels)} by {metric_col}",
            },
        }

    # --- Lowest / min ---
    if _any_words(q, _LOW_WORDS) and metric_col:
        n = _parse_top_n(q.replace("bottom", "top"), default=5)
        ex = {date_col} if date_col else set()
        ent = _entity_column(df, q, metric_col, exclude=ex)
        if ent:
            ser = (
                df.groupby(ent, dropna=True)[metric_col]
                .sum()
                .sort_values(ascending=True)
                .head(n)
            )
            labels = ser.index.astype(str).tolist()
            values = ser.astype(float).tolist()
        else:
            ser = df[metric_col].sort_values(ascending=True).head(n)
            labels = ser.index.astype(str).tolist()
            values = ser.astype(float).tolist()
        text_answer = f"Lowest {len(labels)} by {metric_col}: " + ", ".join(
            f"{l}: {v:g}" for l, v in zip(labels, values)
        )
        return {
            "text_answer": text_answer,
            "plot_data": {
                "type": "bar",
                "x": labels,
                "y": values,
                "title": f"Lowest {len(labels)} by {metric_col}",
            },
        }

    # --- Average / mean ---
    if _any_words(q, _AVG_WORDS):
        mcol = metric_col or _metric_column(df, q)
        if not mcol:
            return None
        avg = float(df[mcol].mean())
        return {
            "text_answer": f"Average {mcol} is {avg:.4g}.",
            "plot_data": None,
        }

    # --- Count / total ---
    if _any_phrase(q, _COUNT_PHRASES) or _any_words(q, _COUNT_WORDS):
        if "by" in q and cat_col:
            vc = df[cat_col].value_counts(dropna=True).head(30)
            text_answer = f"Counts by {cat_col}: " + ", ".join(f"{i}: {int(v)}" for i, v in vc.items())
            return {
                "text_answer": text_answer,
                "plot_data": {
                    "type": "bar",
                    "x": vc.index.astype(str).tolist(),
                    "y": vc.astype(float).tolist(),
                    "title": f"Count by {cat_col}",
                },
            }
        return {
            "text_answer": f"Row count: {len(df)}.",
            "plot_data": None,
        }

    if _any_words(q, _TOTAL_WORDS):
        mcol = metric_col or _metric_column(df, q)
        if mcol and ("sales" in q or "revenue" in q or "amount" in q or mcol.lower() in q):
            total = float(df[mcol].sum())
            return {
                "text_answer": f"Total {mcol} is {total:.4g}.",
                "plot_data": None,
            }
        if "row" in q or "record" in q:
            return {
                "text_answer": f"Total rows: {len(df)}.",
                "plot_data": None,
            }

    return None
