# rag/embedding_model.py

from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """
        Load pre-trained embedding model
        """
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        """
        Convert list of text chunks into embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(texts)
        return embeddings