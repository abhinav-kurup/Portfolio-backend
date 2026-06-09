from __future__ import annotations

from sentence_transformers import CrossEncoder
from app.core.logging import setup_logging
from app.core.config import settings

logger = setup_logging()


class RerankerClient:
    def __init__(self):
        logger.info(f"Initializing reranker client with model: {settings.RERANKER_MODEL}")
        # Load the cross-encoder model locally (lazy initialization)
        self.model = CrossEncoder(settings.RERANKER_MODEL)
        logger.info("Reranker client initialized successfully")

    def rerank(self, query: str, documents: list[dict], top_n: int = 5) -> list[dict]:
        """
        Rerank document candidates using Cross-Encoder model.
        Returns a sorted list of documents with updated scores, sliced to top_n.
        """
        if not documents:
            return []

        # Construct pairs: [query, document_text]
        # Ingestion context structure: Title + content + metadata summary
        pairs = []
        for doc in documents:
            doc_text = f"Title: {doc['title']}\nContent: {doc['content']}"
            pairs.append([query, doc_text])

        try:
            logger.info(f"Reranking {len(documents)} candidates with query: '{query}'")
            scores = self.model.predict(pairs)
            
            # Convert numpy floats/scores to standard floats
            ranked_docs = []
            for doc, score in zip(documents, scores):
                doc_copy = dict(doc)
                doc_copy["score"] = round(float(score), 4)
                ranked_docs.append(doc_copy)

            # Sort descending by cross-encoder relevance score
            ranked_docs.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info(f"Reranked finished. Best score: {ranked_docs[0]['score'] if ranked_docs else 'N/A'}")
            return ranked_docs[:top_n]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}. Returning original documents as fallback.")
            return documents[:top_n]


# Instantiate globally
reranker_client = RerankerClient()
