"""Embedding generation services."""

import logging
from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
    """Get the OpenAI client."""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Generate embeddings for a list of texts in batches using OpenAI API.

    Args:
        texts: A list of text chunks.
        batch_size: Number of texts per batch request.

    Returns:
        list[list[float]]: A list of embeddings corresponding to the input texts.
    """
    if not texts:
        return []

    client = get_openai_client()
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            logger.info(
                f"Generating embeddings for batch {i // batch_size + 1} (size={len(batch)})"
            )
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL, input=batch
            )
            # Extracted embeddings in original order
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    return embeddings
