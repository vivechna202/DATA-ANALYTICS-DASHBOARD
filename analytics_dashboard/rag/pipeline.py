# analytics_dashboard/rag/pipeline.py

from analytics_dashboard.rag.pdf_loader import load_pdf
from analytics_dashboard.rag.chunking import chunk_text
from analytics_dashboard.rag.embeddings import EmbeddingModel
from analytics_dashboard.rag.vector_store import VectorStore
from analytics_dashboard.rag.llm_generator import generate_answer


class RAGPipeline:
    def __init__(self, file_path):
        """
        Initialize full RAG pipeline
        """
        self.file_path = file_path
        self.embedding_model = EmbeddingModel()
        self.vector_store = None

        # Build pipeline once at startup
        self._build_pipeline()

    def _build_pipeline(self):
        """
        Step 1: Load → Chunk → Embed → Store
        """
        try:
            print("🔄 Loading document...")
            text = load_pdf(self.file_path)

            print("🔄 Chunking text...")
            chunks = chunk_text(text)

            if not chunks:
                raise ValueError("No chunks created from document")

            print(f"📦 Total chunks created: {len(chunks)}")

            print("🔄 Creating embeddings...")
            embeddings = self.embedding_model.encode(chunks)

            if len(embeddings.shape) != 2:
                raise ValueError(f"Invalid embedding shape: {embeddings.shape}")

            print(f"🧠 Embedding shape: {embeddings.shape}")

            print("🔄 Storing in FAISS...")
            self.vector_store = VectorStore(embedding_dim=embeddings.shape[1])
            self.vector_store.add_embeddings(embeddings, chunks)

            print("✅ Pipeline ready!")

        except Exception as e:
            print("❌ Error building pipeline:", str(e))
            raise

    def query(self, user_query, top_k=3):
        """
        Step 2: Query pipeline
        """
        try:
            print(f"\n🔍 Processing query: {user_query}")

            if not self.vector_store:
                raise ValueError("Vector store not initialized")

            # Convert query → embedding (IMPORTANT: keep as list)
            query_embedding = self.embedding_model.encode([user_query])

            # Retrieve similar chunks
            results = self.vector_store.search(query_embedding, top_k=top_k)

            print(f"📄 Retrieved {len(results)} chunks")

            # Generate final answer using LLM
            answer = generate_answer(user_query, results)

            return {
                "answer": answer,
                "chunks": results
            }

        except Exception as e:
            print("❌ Query error:", str(e))
            return {
                "answer": f"Error: {str(e)}",
                "chunks": []
            }