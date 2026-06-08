"""Document parsing services."""

import io
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from PDF bytes.

    Args:
        pdf_bytes: The raw PDF bytes.

    Returns:
        str: Extracted text content.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        raise ValueError(f"Failed to parse PDF document: {e}")
