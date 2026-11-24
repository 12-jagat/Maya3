"""
Intelligent Text Chunking Service for Academic Documents and University Circulars.
Preserves page boundaries, headings, and paragraph contexts with configurable overlap.
Generates deterministic chunk IDs and rich metadata envelopes.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import get_settings

settings = get_settings()


class NoticeChunk(BaseModel):
    """Complete chunk entity formatted for vector storage and semantic retrieval."""

    id: str = Field(description="Deterministic primary key for vector database")
    notice_id: str
    chunk_index: int
    title: str
    content: str
    source_url: str
    pdf_url: Optional[str] = None
    page_number: Optional[int] = None
    category: str = "General"
    published_date: Optional[str] = None
    content_hash: str
    token_count: int = 0
    embedding: Optional[List[float]] = None


class ChunkingService:
    """
    Splits multi-page documents into semantically coherent overlapping chunks.
    Prefers paragraph and sentence boundaries while preserving page references.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    @classmethod
    def estimate_token_count(cls, text: str) -> int:
        """Approximate token count based on whitespace and punctuation tokens."""
        if not text:
            return 0
        words = re.findall(r"\w+|[^\w\s]", text)
        return len(words)

    @classmethod
    def generate_chunk_id(cls, notice_id: str, content_hash: str, chunk_index: int) -> str:
        """
        Generate deterministic, URL-safe chunk identifier.
        Guarantees idempotency and prevents duplicate vector entries.
        """
        seed = f"{notice_id}:{content_hash}:{chunk_index}"
        hash_digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        safe_notice = re.sub(r"[^a-zA-Z0-9_-]", "", str(notice_id))[:8]
        return f"{safe_notice}_{hash_digest}_c{chunk_index}"

    def chunk_extracted_document(
        self,
        extracted_doc: Dict[str, Any],
        notice_metadata: Dict[str, Any],
    ) -> List[NoticeChunk]:
        """
        Chunk a multi-page extracted document preserving page numbers and metadata.
        """
        pages = extracted_doc.get("pages", [])
        notice_id = str(notice_metadata.get("id") or notice_metadata.get("source_url", "unknown"))
        title = notice_metadata.get("title", "Official University Notice")
        source_url = notice_metadata.get("source_url", "")
        pdf_url = notice_metadata.get("pdf_url")
        category = notice_metadata.get("category", "General")
        published_date = notice_metadata.get("published_date")
        content_hash = notice_metadata.get("content_hash") or hashlib.sha256(title.encode("utf-8")).hexdigest()

        chunks: List[NoticeChunk] = []
        global_chunk_idx = 0

        # If document has distinct pages, chunk per page while carrying context
        if pages:
            for page in pages:
                page_num = page.get("page_number", 1)
                page_text = (page.get("text") or "").strip()
                if not page_text:
                    continue

                page_chunks = self._split_text_into_chunks(
                    text=page_text,
                    title=title,
                    notice_id=notice_id,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    page_number=page_num,
                    category=category,
                    published_date=published_date,
                    content_hash=content_hash,
                    start_index=global_chunk_idx,
                )
                chunks.extend(page_chunks)
                global_chunk_idx += len(page_chunks)
        else:
            # Fallback to single text body
            full_text = extracted_doc.get("full_text", "").strip()
            if full_text:
                chunks = self._split_text_into_chunks(
                    text=full_text,
                    title=title,
                    notice_id=notice_id,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    page_number=1,
                    category=category,
                    published_date=published_date,
                    content_hash=content_hash,
                    start_index=0,
                )

        return chunks

    def _split_text_into_chunks(
        self,
        text: str,
        title: str,
        notice_id: str,
        source_url: str,
        pdf_url: Optional[str],
        page_number: int,
        category: str,
        published_date: Optional[str],
        content_hash: str,
        start_index: int,
    ) -> List[NoticeChunk]:
        """
        Split a block of text on paragraph boundaries to meet token target.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: List[NoticeChunk] = []
        current_paragraphs: List[str] = []
        current_tokens = 0
        chunk_idx = start_index

        for para in paragraphs:
            para_tokens = self.estimate_token_count(para)

            # If a single paragraph is larger than chunk_size, split by sentences
            if para_tokens > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    s_tokens = self.estimate_token_count(sentence)
                    if current_tokens + s_tokens > self.chunk_size and current_paragraphs:
                        chunk_content = "\n\n".join(current_paragraphs)
                        chunk_id = self.generate_chunk_id(notice_id, content_hash, chunk_idx)
                        chunks.append(
                            NoticeChunk(
                                id=chunk_id,
                                notice_id=notice_id,
                                chunk_index=chunk_idx,
                                title=title,
                                content=chunk_content,
                                source_url=source_url,
                                pdf_url=pdf_url,
                                page_number=page_number,
                                category=category,
                                published_date=published_date,
                                content_hash=content_hash,
                                token_count=current_tokens,
                            )
                        )
                        chunk_idx += 1
                        # Retain overlap sentences
                        current_paragraphs = current_paragraphs[-1:] if self.chunk_overlap > 0 else []
                        current_tokens = self.estimate_token_count("\n\n".join(current_paragraphs))

                    current_paragraphs.append(sentence)
                    current_tokens += s_tokens
            else:
                if current_tokens + para_tokens > self.chunk_size and current_paragraphs:
                    chunk_content = "\n\n".join(current_paragraphs)
                    chunk_id = self.generate_chunk_id(notice_id, content_hash, chunk_idx)
                    chunks.append(
                        NoticeChunk(
                            id=chunk_id,
                            notice_id=notice_id,
                            chunk_index=chunk_idx,
                            title=title,
                            content=chunk_content,
                            source_url=source_url,
                            pdf_url=pdf_url,
                            page_number=page_number,
                            category=category,
                            published_date=published_date,
                            content_hash=content_hash,
                            token_count=current_tokens,
                        )
                    )
                    chunk_idx += 1
                    # Retain last paragraph for overlap
                    current_paragraphs = current_paragraphs[-1:] if self.chunk_overlap > 0 else []
                    current_tokens = self.estimate_token_count("\n\n".join(current_paragraphs))

                current_paragraphs.append(para)
                current_tokens += para_tokens

        # Final trailing chunk
        if current_paragraphs:
            chunk_content = "\n\n".join(current_paragraphs)
            chunk_id = self.generate_chunk_id(notice_id, content_hash, chunk_idx)
            chunks.append(
                NoticeChunk(
                    id=chunk_id,
                    notice_id=notice_id,
                    chunk_index=chunk_idx,
                    title=title,
                    content=chunk_content,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    page_number=page_number,
                    category=category,
                    published_date=published_date,
                    content_hash=content_hash,
                    token_count=current_tokens,
                )
            )

        return chunks
