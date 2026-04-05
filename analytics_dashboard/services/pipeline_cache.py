"""LRU-style cache for RAG pipelines built from dynamic sources."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)

MAX_CACHE_ENTRIES = 10


def _normalize_source_input(source_type: str, source_input: str) -> str:
    st = source_type.lower()
    if st in ("pdf", "csv"):
        return os.path.abspath(os.path.normpath(source_input))
    return source_input


def make_cache_key(source_type: str, source_input: str, options: dict[str, Any]) -> str:
    normalized = _normalize_source_input(source_type, source_input)
    payload = json.dumps(
        {"t": source_type, "i": normalized, "o": options},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class PipelineCache:
    """Thread-safe LRU cache for a small number of RAG pipeline instances."""

    def __init__(self, max_entries: int = MAX_CACHE_ENTRIES):
        self._max = max(1, int(max_entries))
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._lock = Lock()

    def get_or_build(self, key: str, builder: Callable[[], Any]) -> Any:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                logger.debug("Pipeline cache hit: %s...", key[:16])
                return self._data[key]

        pipeline = builder()

        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
            self._data[key] = pipeline
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                evicted, _ = self._data.popitem(last=False)
                logger.debug("Pipeline cache evicted: %s...", evicted[:16])
            return self._data[key]


_pipeline_cache = PipelineCache()


def get_pipeline_cache() -> PipelineCache:
    return _pipeline_cache
