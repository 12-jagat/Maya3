"""
MAYA Milestone 4 Preparation Interfaces.
Pre-defines standard interfaces and contracts for:
- PyMuPDF native text extraction
- PaddleOCR fallback for scanned PDFs and images
- DOCX document parsing
- Text cleaning and normalized chunking with overlap
- all-MiniLM-L6-v2 embedding generation (384-dimensional)
- Zilliz Cloud / Milvus dense vector batch insertion

NOTE: Per Milestone 3 requirements, actual heavyweight OCR and vector insertion
will be implemented in Milestone 4.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    notice_id: str
    chunk_index: int
    text: str
    token_count: int
    page_number: Optional[int] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseDocumentExtractor(ABC):
    """Abstract interface for extracting text from document formats."""

    @abstractmethod
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract clean text content, page boundaries, and metadata from document."""
        pass


class BaseOCRFallback(ABC):
    """Abstract interface for PaddleOCR image / scanned PDF processing."""

    @abstractmethod
    def extract_scanned_text(self, image_bytes_or_path: Any) -> str:
        """Run optical character recognition on scanned pages."""
        pass


class BaseChunker(ABC):
    """Abstract interface for text normalization and chunking with overlap."""

    @abstractmethod
    def create_chunks(self, document_text: str, doc_metadata: Dict[str, Any], chunk_size: int = 512, overlap: int = 64) -> List[DocumentChunk]:
        """Produce overlapping semantic text chunks for embedding."""
        pass


class BaseEmbeddingService(ABC):
    """Abstract interface for 384-dimensional sentence-transformers/all-MiniLM-L6-v2 embeddings."""

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for input text batch."""
        pass


class BaseVectorIndexService(ABC):
    """Abstract interface for Zilliz Cloud / Milvus vector operations."""

    @abstractmethod
    def batch_insert(self, collection_name: str, chunks: List[DocumentChunk]) -> int:
        """Batch insert chunks with vector embeddings into Zilliz collection."""
        pass
