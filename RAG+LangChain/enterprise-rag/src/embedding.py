import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.model_name = model_name

        self.model = SentenceTransformer(
            model_name
        )

    def encode_documents(
        self,
        texts: list[str],
    ) -> np.ndarray:
        """
        Encode document chunks into normalized embeddings.
        """

        if not texts:
            raise ValueError("texts cannot be empty")

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return np.asarray(
            embeddings,
            dtype=np.float32,
        )

    def encode_query(
        self,
        query: str,
    ) -> np.ndarray:
        """
        Encode a single query into a normalized embedding.
        """

        if not query.strip():
            raise ValueError("query cannot be empty")

        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        )

        return np.asarray(
            embedding[0],
            dtype=np.float32,
        )