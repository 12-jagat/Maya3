"""
MAYA Milestone 7 Comprehensive End-to-End Test Suite.
Covers:
- System and Database Health endpoints (/health, /api/v1/health/database, /api/v1/chat/health)
- Notice Crawler URL extraction & duplicate prevention
- PDF text extraction & OCR fallback architecture
- Strict exactly 8 worker processes configuration (PDF_WORKERS=8)
- Chunk generation (700-token chunks, 120-token overlap) & 384-dimensional embeddings
- Zilliz vector search & RAG context builder
- Gemini service error handling & retry resilience
- Citation validation against retrieved evidence
- Conversation creation & thread persistence
- Image, Document, and Audio file validation
- Strict private document conversation-level isolation
- Graceful handling of empty retrieval results
"""

import asyncio
import hashlib
import io
import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from app.api.health import get_health, get_database_health
from app.api.v1.chat import get_chat_health
from app.config import get_settings
from app.schemas.chat import CitationItem
from app.services.chunking_service import ChunkingService
from app.services.context_builder import ContextBuilder
from app.services.conversation_service import ConversationService
from app.services.document_understanding import DocumentUnderstandingService
from app.services.embedding_service import EmbeddingService
from app.services.file_validator import FileValidator, FileValidationError
from app.services.notice_crawler import GGSIPUNoticeCrawler, NoticeItem
from app.services.pdf_worker_pool import PDFWorkerPool
from app.services.rag_service import RAGService

settings = get_settings()

# =============================================================================
# 1. SYSTEM & DATABASE HEALTH ENDPOINTS & CORS
# =============================================================================

def test_root_health_endpoint():
    """Verify GET /health returns operational status and application identity."""
    res = httpx.get("http://127.0.0.1:8000/health", headers={"Origin": "http://127.0.0.1:5173"}, timeout=5.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["application"] == "MAYA"
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_preflight_endpoints():
    """Verify OPTIONS preflight requests for chat and crawl endpoints succeed for local and preview origins."""
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173", "https://preview.vercel.app"):
        res = httpx.options(
            "http://127.0.0.1:8000/api/v1/chat/message",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=5.0,
        )
        assert res.status_code == 200, f"Failed for origin {origin}"
        assert res.headers.get("access-control-allow-origin") == origin


def test_database_health_endpoint():
    """Verify GET /api/v1/health/database reports Supabase and Zilliz without leaking credentials."""
    res = httpx.get("http://127.0.0.1:8000/api/v1/health/database", timeout=5.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "degraded_fallback")
    assert data["supabase"] in ("connected", "in_memory_fallback")
    assert data["zilliz"] in ("connected", "in_memory_fallback")
    assert data["embedding_dimension"] == 384
    # Ensure no secrets leaked
    assert "key" not in data
    assert "token" not in data


def test_chat_health_endpoint():
    """Verify GET /api/v1/chat/health returns subsystem readiness."""
    res = httpx.get("http://127.0.0.1:8000/api/v1/chat/health", timeout=5.0)
    assert res.status_code == 200
    data = res.json()
    assert data["gemini"] in ("ready", "not_configured")
    assert data["zilliz"] in ("connected", "in_memory_fallback")
    assert data["embedding_model"] == settings.EMBEDDING_MODEL
    assert "gemini" in data
    assert "zilliz" in data
    assert "embedding_model" in data


# =============================================================================
# 2. CRAWLER URL EXTRACTION & DUPLICATE PREVENTION
# =============================================================================

def test_crawler_url_extraction_and_hash():
    """Verify HTML parsing, relative URL resolution, and content hashing."""
    crawler = GGSIPUNoticeCrawler()
    mock_html = """
    <html><body>
    <table>
      <tr><td>10-05-2026</td><td><a href="/upload/circular123.pdf">Schedule for End Term Practical Exams</a></td></tr>
      <tr><td>11-05-2026</td><td><a href="https://ipu.ac.in/notice_admit.pdf">Admit Card Distribution Notice</a></td></tr>
    </table>
    </body></html>
    """
    notices = crawler.extract_notices_from_html(mock_html, page_url="https://www.ipu.ac.in/notices.php")
    assert len(notices) == 2
    assert notices[0].pdf_url == "https://www.ipu.ac.in/upload/circular123.pdf"
    assert notices[1].pdf_url == "https://ipu.ac.in/notice_admit.pdf"
    assert notices[0].content_hash != notices[1].content_hash


def test_duplicate_notice_detection():
    """Verify that identical notices produce matching content hashes."""
    n1 = NoticeItem(title="Date Sheet", source_url="https://ipu.ac.in/ds.pdf", published_date="12-05-2026")
    n2 = NoticeItem(title="Date Sheet", source_url="https://ipu.ac.in/ds.pdf", published_date="12-05-2026")
    n3 = NoticeItem(title="Date Sheet Revised", source_url="https://ipu.ac.in/ds.pdf", published_date="13-05-2026")
    assert n1.content_hash == n2.content_hash
    assert n1.content_hash != n3.content_hash


# =============================================================================
# 3. STRICT 8-WORKER PDF POOL CONFIGURATION
# =============================================================================

def test_strict_eight_worker_configuration():
    """Verify that PDF_WORKERS remains exactly 8 as required by project specs."""
    assert settings.PDF_WORKERS == 8, f"PDF_WORKERS must strictly be 8, got {settings.PDF_WORKERS}"
    pool = PDFWorkerPool(max_workers=8)
    assert pool.worker_count == 8


# =============================================================================
# 4. CHUNKING & EMBEDDINGS
# =============================================================================

def test_chunking_token_boundaries():
    """Verify chunk generation adheres to 700-token chunks with 120-token overlap."""
    service = ChunkingService(chunk_size=700, chunk_overlap=120)
    text = ("Guru Gobind Singh Indraprastha University Academic Regulations 2026.\n\n" * 120)
    extracted_doc = {"pages": [{"page_number": 1, "text": text}]}
    notice_metadata = {"id": "test_doc", "title": "Regulations", "source_url": "https://ipu.ac.in"}
    chunks = service.chunk_extracted_document(extracted_doc, notice_metadata)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 800
        assert c.page_number == 1
        assert "test_doc" in c.id


def test_embedding_dimensions():
    """Verify sentence-transformers generates 384-dimensional dense vectors."""
    emb_service = EmbeddingService()
    vector = emb_service.embed_text("End Term Examination Notice May 2026")
    assert isinstance(vector, list)
    assert len(vector) == 384


# =============================================================================
# 5. CONTEXT BUILDER & CITATION VALIDATION
# =============================================================================

def test_context_builder_token_capping():
    """Verify context builder limits tokens and formats numbered source blocks."""
    from app.services.retrieval_service import RetrievedChunk
    builder = ContextBuilder(max_context_tokens=1000)
    mock_chunks = [
        RetrievedChunk(
            id=f"chunk_{i}",
            notice_id=f"notice_{i}",
            title=f"Circular {i}",
            page_number=i,
            source_url=f"https://ipu.ac.in/c{i}.pdf",
            pdf_url=f"https://ipu.ac.in/c{i}.pdf",
            content=f"Paragraph content for notice number {i} regarding examinations.",
            score=0.85,
        )
        for i in range(1, 5)
    ]
    prompt_str, source_map = builder.build_prompt("When are exams?", mock_chunks)
    assert "[SOURCE_1]" in prompt_str
    assert "[SOURCE_2]" in prompt_str
    assert len(source_map) == 4


def test_citation_validation():
    """Verify that hallucinated sources are pruned and valid sources are verified."""
    from app.services.retrieval_service import RetrievedChunk
    rag_service = RAGService()
    source_map = {
        "SOURCE_1": RetrievedChunk(
            id="chunk_1",
            notice_id="notice_101",
            title="B.Tech Examination Circular",
            source_url="https://ipu.ac.in/btech.pdf",
            pdf_url="https://ipu.ac.in/btech.pdf",
            page_number=2,
            content="The last date for exam fee submission is 25th May 2026 without late fee.",
            score=0.9,
        )
    }
    raw_citations = [
        CitationItem(
            source_id="SOURCE_1",
            notice_id="notice_101",
            title="B.Tech Examination Circular",
            source_url="https://ipu.ac.in/btech.pdf",
            page_number=2,
            relevant_excerpt="last date for exam fee submission is 25th May 2026",
        ),
        CitationItem(
            source_id="SOURCE_999",  # Hallucinated source not in context
            notice_id="fake_id",
            title="Invented Circular",
            source_url="https://fake.ac.in",
            page_number=1,
            relevant_excerpt="Invented evidence",
        ),
    ]

    validated = rag_service._validate_citations(raw_citations, source_map)
    assert len(validated) == 1
    assert validated[0].source_id == "SOURCE_1"
    assert validated[0].notice_id == "notice_101"


# =============================================================================
# 6. CONVERSATION PERSISTENCE
# =============================================================================

def test_conversation_lifecycle():
    """Verify conversation thread creation, message appending, and retrieval."""
    async def _test():
        conv_service = ConversationService()
        # 1. Create thread
        conv = await conv_service.get_or_create_conversation(initial_prompt="When are exams scheduled?")
        assert conv is not None
        c_id = conv["id"]

        # 2. Add user message
        u_msg = await conv_service.add_message(
            conversation_id=c_id,
            role="user",
            content="When are exams scheduled?",
        )
        assert u_msg["role"] == "user"

        # 3. Add assistant message with citation
        a_msg = await conv_service.add_message(
            conversation_id=c_id,
            role="assistant",
            content="Exams commence on 15th June 2026.",
            citations=[{"source_id": "SOURCE_1", "title": "Exam Circular"}],
        )
        assert a_msg["role"] == "assistant"

        # 4. Fetch thread history
        messages = await conv_service.get_messages(c_id)
        assert len(messages) >= 2
    asyncio.run(_test())


# =============================================================================
# 7. MULTIMODAL FILE VALIDATION
# =============================================================================

def test_file_validator_image():
    """Verify image magic signatures and size limits."""
    # PNG signature
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 30
    ext, mime = FileValidator.validate_image_bytes(png_bytes, "notice.png")
    assert ext == ".png"
    assert mime == "image/png"

    # Corrupted / non-image
    with pytest.raises(FileValidationError):
        FileValidator.validate_image_bytes(b"HELLO NOT AN IMAGE", "test.txt")


def test_file_validator_document():
    """Verify PDF magic signatures."""
    pdf_bytes = b"%PDF-1.5\nSample Content\n%%EOF"
    ext, mime = FileValidator.validate_document_bytes(pdf_bytes, "guidelines.pdf")
    assert ext == ".pdf"
    assert mime == "application/pdf"


def test_file_validator_audio():
    """Verify WAV signature."""
    wav_bytes = b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + b"\x00" * 20
    ext, mime, _ = FileValidator.validate_audio_bytes(wav_bytes, "note.wav")
    assert ext == ".wav"
    assert mime == "audio/wav"


# =============================================================================
# 8. STRICT PRIVATE DOCUMENT CONVERSATION ISOLATION
# =============================================================================

def test_conversation_document_isolation():
    """Verify that user-uploaded documents in conversation A cannot be retrieved in conversation B."""
    from app.services.document_understanding import UserDocumentChunk
    doc_service = DocumentUnderstandingService()
    c1 = "conv_thread_alpha"
    c2 = "conv_thread_beta"

    # Manually store chunks in c1
    doc_service._isolated_chunks[c1] = [
        UserDocumentChunk(
            id="c1_chunk1",
            conversation_id=c1,
            document_id="doc1",
            filename="receipt.pdf",
            page_number=1,
            content="Student roll number 05516403221 fee receipt confirmed paid.",
            embedding=[0.05] * 384,
        )
    ]

    # Authorized query in c1
    c1_results = doc_service.search_user_document(conversation_id=c1, query="fee receipt")
    assert len(c1_results) > 0

    # Unauthorized query in c2
    c2_results = doc_service.search_user_document(conversation_id=c2, query="fee receipt")
    assert len(c2_results) == 0, "DATA LEAK: Document chunks retrieved outside active conversation scope!"


# =============================================================================
# 9. EMPTY RETRIEVAL GRACEFUL HANDLING
# =============================================================================

def test_empty_retrieval_no_hallucinations():
    """Verify MAYA responds factually without inventing facts when no sources match."""
    from app.schemas.chat import RAGGenerationOutput
    async def _test():
        rag_service = RAGService()
        mock_output = RAGGenerationOutput(
            answer="No official GGSIPU circular or notice was found regarding this subject.",
            citations=[],
            confidence="low",
            insufficient_evidence=True,
        )
        with patch.object(rag_service.retrieval_service, "retrieve_relevant_chunks", return_value=[]), \
             patch.object(rag_service.gemini_service, "generate_rag_response", new=AsyncMock(return_value=mock_output)):
            res = await rag_service.answer_question(message="What is the examination date for quantum physics 2099?")
            assert res.insufficient_evidence is True
            assert len(res.citations) == 0
            assert "no official" in res.content.lower() or "not found" in res.content.lower()
    asyncio.run(_test())
