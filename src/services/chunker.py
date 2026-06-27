"""Text chunking service."""

import logging

logger = logging.getLogger(__name__)


def split_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Split text into chunks of specified size with overlap.

    Args:
        text: The text to split.
        chunk_size: Target size of each chunk in characters.
        overlap: Overlap between consecutive chunks in characters.

    Returns:
        list[str]: A list of text chunks.
    """
    if not text:
        return []

    # Safeguard against invalid chunk configurations
    step = chunk_size - overlap
    if step <= 0:
        logger.warning(
            f"Invalid chunk configuration: chunk_size={chunk_size}, overlap={overlap}. Setting step to chunk_size."
        )
        step = chunk_size

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # If we reached the end of the text, break
        if end == text_len:
            break

        start += step

    return chunks
