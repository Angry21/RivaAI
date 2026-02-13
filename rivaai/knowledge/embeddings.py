"""Embedding generation for knowledge base using OpenAI text-embedding-3-large."""

import logging
from typing import List

from openai import OpenAI

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using OpenAI's text-embedding-3-large model."""

    def __init__(self, settings: Settings) -> None:
        """Initialize embedding generator.

        Args:
            settings: Application settings containing OpenAI API key
        """
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimension = 1536  # text-embedding-3-large dimension

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in a batch.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise


def get_embedding_generator(settings: Settings | None = None) -> EmbeddingGenerator:
    """Get or create embedding generator instance.

    Args:
        settings: Application settings (required on first call)

    Returns:
        EmbeddingGenerator instance
    """
    if settings is None:
        from rivaai.config.settings import get_settings
        settings = get_settings()

    return EmbeddingGenerator(settings)
