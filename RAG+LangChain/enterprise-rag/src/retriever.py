from dataclasses import dataclass

import numpy as np

from src.models import Document


@dataclass(slots=True)
class RetrievalResult:
    document: Document
    score: float


class DenseRetriever:
    def __init__(
        self,
        documents: list[Document],
        embeddings: np.ndarray,
    ) -> None:

        if len(documents) != len(embeddings):
            raise ValueError(
                "documents and embeddings must have same length"
            )

        if not documents:
            raise ValueError(
                "documents cannot be empty"
            )

        self.documents = documents
        self.embeddings = embeddings

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> list[RetrievalResult]:

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        # embeddings: (N, D)
        # query_embedding: (D,)
        #
        # normalized embeddings:
        # dot product == cosine similarity
        scores = (
            self.embeddings
            @ query_embedding
        )

        top_k = min(
            top_k,
            len(self.documents),
        )

        # 从大到小排序
        indices = np.argsort(scores)[::-1][:top_k]

        results = []

        for index in indices:
            results.append(
                RetrievalResult(
                    document=self.documents[index],
                    score=float(scores[index]),
                )
            )

        return results