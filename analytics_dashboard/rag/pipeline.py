# analytics_dashboard/rag/pipeline.py

from __future__ import annotations

import logging

from analytics_dashboard.rag.chunking import chunk_text
from analytics_dashboard.rag.embeddings import EmbeddingModel
from analytics_dashboard.rag.llm_generator import generate_answer
from analytics_dashboard.rag.pdf_loader import load_pdf
from analytics_dashboard.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Guardrails for very large corpora
DEFAULT_MAX_TEXT_CHARS = 500_000
DEFAULT_MAX_CHUNKS = 5_000


class RAGPipeline:
    def __init__(self, file_path: str | None = None):
        """
        Build a RAG pipeline from a PDF file path (legacy / default behavior).
        """
        self.file_path = file_path
        self.embedding_model = EmbeddingModel()
        self.vector_store = None

        if not file_path:
            raise ValueError("file_path is required when using RAGPipeline(file_path=...)")

        logger.info("Building RAG pipeline from PDF: %s", file_path)
        text = load_pdf(file_path)
        self._build_pipeline_from_text(text)

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
        max_chunks: int = DEFAULT_MAX_CHUNKS,
    ) -> RAGPipeline:
        """
        Build a RAG pipeline from arbitrary text (PDF/CSV/Mongo, etc.).
        Truncates oversized text and chunk lists to keep memory predictable.
        """
        inst = cls.__new__(cls)
        inst.file_path = None
        inst.embedding_model = EmbeddingModel()
        inst.vector_store = None

        if not text or not str(text).strip():
            raise ValueError("Empty text cannot be indexed")

        raw = str(text)
        if len(raw) > max_text_chars:
            logger.warning("Truncating text from %s to %s characters", len(raw), max_text_chars)
            raw = raw[:max_text_chars]

        inst._build_pipeline_from_text(raw, max_chunks=max_chunks)
        return inst

    def _build_pipeline_from_text(self, text: str, max_chunks: int = DEFAULT_MAX_CHUNKS) -> None:
        """Load → Chunk → Embed → Store."""
        logger.info("Chunking text...")
        chunks = chunk_text(text)

        if not chunks:
            raise ValueError("No chunks created from document")

        if len(chunks) > max_chunks:
            logger.warning("Truncating chunks from %s to %s", len(chunks), max_chunks)
            chunks = chunks[:max_chunks]

        logger.info("Total chunks: %s", len(chunks))

        logger.info("Creating embeddings...")
        embeddings = self.embedding_model.encode(chunks)

        if len(embeddings.shape) != 2:
            raise ValueError(f"Invalid embedding shape: {embeddings.shape}")

        logger.info("Embedding shape: %s", embeddings.shape)

        logger.info("Storing in FAISS...")
        self.vector_store = VectorStore(embedding_dim=embeddings.shape[1])
        self.vector_store.add_embeddings(embeddings, chunks)

        logger.info("Pipeline ready")

    def query(self, user_query: str, top_k: int = 3) -> dict:
        """Retrieve relevant chunks and generate an answer."""
        try:
            logger.info("Processing query: %s", user_query[:200])

            if not self.vector_store:
                raise ValueError("Vector store not initialized")

            query_embedding = self.embedding_model.encode([user_query])
            results = self.vector_store.search(query_embedding, top_k=top_k)

            logger.info("Retrieved %s chunks", len(results))

            answer = generate_answer(user_query, results)

            return {
                "answer": answer,
                "chunks": results,
            }

        except Exception as e:
            logger.exception("Query error")
            return {
                "answer": f"Error: {str(e)}",
                "chunks": [],
            }
