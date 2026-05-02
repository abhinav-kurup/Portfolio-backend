from sentence_transformers import SentenceTransformer
from app.core.logging import setup_logging
from app.core.config import settings

logger = setup_logging()


class EmbeddingsClient:
    def __init__(self):
        logger.info(f"Initializing embedding client with model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding client initialized")
    
    def embed(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()


embeddings_client = EmbeddingsClient()
