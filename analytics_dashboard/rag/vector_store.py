# rag/vector_store.py

import faiss
import numpy as np


class VectorStore:
    def __init__(self, embedding_dim):
        """
        Initialize FAISS index
        """
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.text_chunks = []

    def add_embeddings(self, embeddings, chunks):
        """
        Store embeddings and corresponding text chunks
        """
        embeddings = np.array(embeddings).astype('float32')
        self.index.add(embeddings)
        self.text_chunks.extend(chunks)

    def search(self, query_embedding, top_k=3):
        """
        Search for similar chunks
        """
        query_embedding = np.array(query_embedding).astype('float32')

        # Ensure correct shape (1, dim)
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)

        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx in indices[0]:
            results.append(self.text_chunks[idx])

        return results