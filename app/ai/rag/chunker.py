"""
Text Chunker
============
Splits long documents into overlapping chunks for RAG indexing.
"""

from typing import List
from app.config import settings


class TextChunker:
    """
    Splits text into overlapping chunks of fixed token/character length.

    Args:
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to overlap between consecutive chunks.
    """

    def __init__(
        self,
        chunk_size: int = None,
        overlap: int = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP

    def chunk(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Full document text.

        Returns:
            List of text chunks.
        """
        text = text.strip()
        if not text:
            return []

        # First split by paragraphs to respect natural boundaries
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            # If a single paragraph exceeds chunk_size, split it by sentences
            if len(para) > self.chunk_size:
                sentences = para.replace(". ", ".\n").split("\n")
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= self.chunk_size:
                        current_chunk += " " + sentence
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
            else:
                if len(current_chunk) + len(para) <= self.chunk_size:
                    current_chunk += "\n\n" + para
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    # Start new chunk with overlap from previous
                    overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks
