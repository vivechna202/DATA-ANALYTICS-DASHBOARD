"""Load documents from MongoDB and convert them to text for RAG."""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5_000
MAX_LIMIT = 50_000


def _database_from_uri(uri: str) -> str | None:
    parsed = urlparse(uri)
    path = (parsed.path or "").strip("/")
    if not path:
        return None
    return path.split("/")[0] or None


def _doc_to_text(doc: dict) -> str:
    lines = []
    for key, value in doc.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines)


def load_mongo_source(
    uri: str,
    database: str | None = None,
    collection: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    if not uri or not str(uri).strip():
        raise ValueError("MongoDB URI is empty")

    uri = uri.strip()
    limit = max(1, min(int(limit), MAX_LIMIT))

    db_name = database or _database_from_uri(uri)
    if not db_name:
        raise ValueError(
            "MongoDB database not specified. Set mongo_database in the request "
            "or include the database name in the URI (e.g. mongodb://host/dbname)."
        )
    if not collection:
        raise ValueError("mongo_collection is required for MongoDB source")

    logger.info("Connecting to MongoDB database=%s collection=%s limit=%s", db_name, collection, limit)

    try:
        from pymongo import MongoClient
        from pymongo.errors import (
            ConfigurationError,
            ConnectionFailure,
            OperationFailure,
            ServerSelectionTimeoutError,
        )
    except ImportError as e:
        raise ImportError(
            "MongoDB source requires pymongo. Install with: pip install pymongo"
        ) from e

    client = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
        client.admin.command("ping")
    except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
        logger.exception("MongoDB connection failed")
        raise ConnectionError(f"MongoDB connection failed: {e}") from e

    try:
        coll = client[db_name][collection]
        cursor = coll.find().limit(limit)
        parts: list[str] = []
        for doc in cursor:
            if isinstance(doc, dict):
                parts.append(_doc_to_text(doc))
            else:
                parts.append(str(doc))

        if not parts:
            raise ValueError("No documents returned from the collection (empty collection or limit 0)")

        return "\n\n---\n\n".join(parts)
    except OperationFailure as e:
        logger.exception("MongoDB query failed")
        raise ValueError(f"MongoDB query failed: {e}") from e
    finally:
        if client is not None:
            client.close()
