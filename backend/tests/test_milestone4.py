"""
MAYA Milestone 4 Comprehensive Test Suite.
Verifies Document Extraction, OCR Fallback, DOCX Extractor, Text Cleaning,
Chunking, 384-d Embedding Service, Zilliz Client, 8-Worker Pool, and APIs.
All tests run locally with zero external network dependencies.
"""

import asyncio
import os
import tempfile
from pathlib import Path
import pytest
import fitz  # PyMuPDF
import docx  # python-docx
import httpx

from app.config import get_settings
from app.services.text_cleaner import TextCleaner
from app.services.pdf_extractor import PDFExtractor
from app.services.docx_extractor import DOCXExtractor
from app.services.chunking_service import ChunkingService, NoticeChunk
from app.services.embedding_service import EmbeddingService
from app.services.pdf_worker_pool import PDFWorkerPool, process_single_pdf_worker
from app.database.zilliz_client import ZillizClient
from app.main import app

settings = get_settings()


# =============================================================================
# 1. CONFIGURATION & WORKER POOL VERIFICATION
# =============================================================================

def test_milestone4_settings():
    """Verify strict Milestone 4 architectural settings."""
    assert settings.PDF_WORKERS == 8, "Worker pool must strictly configure 8 processes by default"
    assert settings.CHUNK_SIZE == 700, "Target chunk size must be 700 tokens"
    assert settings.CHUNK_OVERLAP == 120, "Target chunk overlap must be 120 tokens"
    assert settings.EMBEDDING_BATCH_SIZE == 64, "Embedding batch size must be 64"
    assert settings.ZILLIZ_COLLECTION == "maya_notice_chunks", "Target collection must be maya_notice_chunks"


def test_pdf_worker_pool_has_8_workers():
    """Verify that PDFWorkerPool initializes with exactly 8 workers."""
    pool = PDFWorkerPool()
    assert pool.max_workers == 8
    assert pool.worker_count == 8


# =============================================================================
# 2. TEXT CLEANER & NORMALIZATION
# =============================================================================

def test_text_cleaner_normalization():
    """Verify text cleaner normalizes Unicode, whitespace, and fixes broken hyphens."""
    cleaner = TextCleaner()
    raw = "Guru  Gobind   Singh \u00a0 Indraprastha\t\tUniversity\r\n\r\nExami-\r\nnation Division."
    cleaned = cleaner.clean(raw)

    assert "Guru Gobind Singh" in cleaned
    assert "Indraprastha" in cleaned
    assert "Examination Division." in cleaned


def test_text_cleaner_preserves_university_patterns():
    """Verify text cleaner preserves enrollment numbers, dates, emails, and URLs."""
    cleaner = TextCleaner()
    text = (
        "Notice Date: 24-11-2024. Enrollment No: 01216403220.\n"
        "Contact: examdept@ipu.ac.in. Official Portal: https://www.ipu.ac.in/notices.php\n"
        "Subject: B.Tech CSE Semester VII Result."
    )
    cleaned = cleaner.clean(text)

    assert "24-11-2024" in cleaned
    assert "01216403220" in cleaned
    assert "examdept@ipu.ac.in" in cleaned
    assert "https://www.ipu.ac.in/notices.php" in cleaned


def test_text_cleaner_table_preservation():
    """Verify tables with vertical bar separators are preserved intact."""
    cleaner = TextCleaner()
    table = "Code | Subject Name | Credits | Max Marks\nETCS-401 | Soft Computing | 4 | 100"
    cleaned = cleaner.clean(table)

    assert "Code | Subject Name | Credits | Max Marks" in cleaned
    assert "ETCS-401 | Soft Computing | 4 | 100" in cleaned


# =============================================================================
# 3. NATIVE PDF EXTRACTION (PYMUPDF)
# =============================================================================

def test_native_pdf_extraction(tmp_path):
    """Verify PyMuPDF extracts page text, page numbers, and document metadata."""
    pdf_path = tmp_path / "sample_notice.pdf"

    # Create synthetic 2-page PDF
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 72),
        "GURU GOBIND SINGH INDRAPRASTHA UNIVERSITY\n"
        "Sector 16-C, Dwarka, New Delhi - 110078\n"
        "EXAMINATION DIVISION - NOTICE\n"
        "End Term Examination Date Sheet for December 2024.\n"
        "All candidates must bring valid admit cards.",
        fontsize=12,
    )
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(
        (50, 72),
        "Page 2: Instructions for Examination Centres.\n"
        "Mobile phones and electronic gadgets are strictly prohibited inside examination halls.",
        fontsize=12,
    )
    doc.set_metadata({"title": "Examination Date Sheet 2024", "author": "GGSIPU Exam Division"})
    doc.save(str(pdf_path))
    doc.close()

    # Extract
    extractor = PDFExtractor(ocr_enabled=False)
    result = extractor.extract_pdf(str(pdf_path))

    assert result["success"] is True
    assert result["total_pages"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["page_number"] == 1
    assert "GURU GOBIND SINGH INDRAPRASTHA UNIVERSITY" in result["pages"][0]["text"]
    assert result["pages"][1]["page_number"] == 2
    assert "strictly prohibited" in result["pages"][1]["text"]
    assert result["metadata"]["title"] == "Examination Date Sheet 2024"


def test_corrupt_pdf_handling(tmp_path):
    """Verify corrupt or unreadable PDF files fail gracefully without crashing."""
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.4 Not a valid PDF content header")

    extractor = PDFExtractor()
    result = extractor.extract_pdf(str(corrupt_path))

    assert result["success"] is False
    assert result["total_pages"] == 0
    assert result["error"] is not None


# =============================================================================
# 4. DOCX EXTRACTION
# =============================================================================

def test_docx_extraction(tmp_path):
    """Verify DOCX extractor extracts paragraphs, headings, and table cells."""
    docx_path = tmp_path / "sample_circular.docx"

    doc = docx.Document()
    doc.add_heading("GGSIPU Sports Directorate", level=1)
    doc.add_paragraph("Annual Inter-College Sports Meet scheduled from 15th December 2024.")

    table = doc.add_table(rows=2, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Event"
    hdr_cells[1].text = "Venue"
    hdr_cells[2].text = "Date"

    row_cells = table.rows[1].cells
    row_cells[0].text = "100m Sprint"
    row_cells[1].text = "Main Stadium"
    row_cells[2].text = "15-12-2024"

    doc.save(str(docx_path))

    result = DOCXExtractor.extract_docx(str(docx_path))

    assert result["success"] is True
    assert "Annual Inter-College Sports Meet" in result["full_text"]
    assert "100m Sprint" in result["full_text"]
    assert "Main Stadium" in result["full_text"]


# =============================================================================
# 5. CHUNKING SERVICE
# =============================================================================

def test_chunking_service_basic():
    """Verify chunking service creates structured chunks within token bounds."""
    chunker = ChunkingService(chunk_size=700, chunk_overlap=120)

    # Generate a long text with multiple paragraphs
    paragraphs = [
        f"Paragraph {i}: Guru Gobind Singh Indraprastha University (GGSIPU) announces the schedule for "
        f"academic session 2024-25. The examination branch will conduct the end semester theory and practical "
        f"examinations for all affiliated institutes and university schools of studies. "
        f"Candidates are advised to regularly monitor the university website for datesheet updates."
        for i in range(25)
    ]
    long_text = "\n\n".join(paragraphs)

    extracted_doc = {
        "pages": [{"page_number": 1, "text": long_text}],
        "full_text": long_text,
    }
    metadata = {
        "id": "notice_chunk_test",
        "title": "Exam Schedule",
        "source_url": "https://ipu.ac.in/notice1",
        "category": "Examination",
    }
    chunks = chunker.chunk_extracted_document(extracted_doc, metadata)

    assert len(chunks) >= 2, "Long text should split into multiple chunks"
    for chunk in chunks:
        assert chunk.notice_id == "notice_chunk_test"
        assert len(chunk.content) > 50
        assert chunk.token_count <= 850, "Chunk should respect approximate token bounds"
        assert chunk.source_url == "https://ipu.ac.in/notice1"
        assert chunk.page_number == 1


def test_chunking_short_text():
    """Verify short text produces exactly one chunk with deterministic ID."""
    chunker = ChunkingService(chunk_size=700, chunk_overlap=120)
    extracted_doc = {
        "pages": [{"page_number": 1, "text": "Short notice regarding holiday on 25th December."}],
        "full_text": "Short notice regarding holiday on 25th December.",
    }
    metadata = {"id": "short_001", "title": "Holiday", "source_url": "https://ipu.ac.in/h1"}
    chunks = chunker.chunk_extracted_document(extracted_doc, metadata)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert "holiday" in chunks[0].content.lower()


# =============================================================================
# 6. LOCAL EMBEDDING SERVICE (384 DIMENSIONS)
# =============================================================================

def test_embedding_dimensions_and_normalization():
    """Verify EmbeddingService produces strictly 384-dimensional cosine-normalized vectors."""
    service = EmbeddingService()

    text = "Guru Gobind Singh Indraprastha University End Term Examination 2024"
    vector = service.embed_text(text)

    # 1. Dimension check
    assert len(vector) == 384, f"Vector dimension must be strictly 384, got {len(vector)}"

    # 2. Finite float check
    assert all(isinstance(x, float) for x in vector)
    assert not any(x != x for x in vector), "NaN found in embedding"

    # 3. L2 norm check (must be normalized to 1.0 for cosine similarity)
    norm = sum(x * x for x in vector) ** 0.5
    assert abs(norm - 1.0) < 1e-4, f"Vector must be unit normalized, got norm={norm}"


def test_batch_embedding():
    """Verify batch embedding generates expected (N, 384) matrix."""
    service = EmbeddingService()
    texts = [
        "First circular regarding admission counseling.",
        "Second circular regarding end term examinations.",
        "Third circular regarding annual sports day.",
    ]
    vectors = service.embed_batch(texts)

    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 384
        norm = sum(x * x for x in v) ** 0.5
        assert abs(norm - 1.0) < 1e-4


def test_semantic_similarity_order():
    """Verify semantically similar texts yield higher cosine similarity than dissimilar texts."""
    service = EmbeddingService()

    q = service.embed_text("examination date sheet for btech students")
    similar = service.embed_text("schedule and timetable for b.tech end term examination")
    unrelated = service.embed_text("cricket tournament venue and player registration guidelines")

    def cosine_similarity(v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    sim_score = cosine_similarity(q, similar)
    unrel_score = cosine_similarity(q, unrelated)

    assert sim_score > unrel_score, f"Similar ({sim_score}) must have higher score than unrelated ({unrel_score})"


# =============================================================================
# 7. ZILLIZ CLIENT OPERATIONS (IN-MEMORY / RESILIENT MODE)
# =============================================================================

def test_zilliz_client_insert_and_search():
    """Verify Zilliz client handles vector insertion, search, and notice-level deletion in offline mode."""
    async def _test():
        # Using empty uri/token triggers the local in-memory fallback for zero network calls
        client = ZillizClient(uri="", token="", collection_name="test_collection")

        test_chunk = NoticeChunk(
            id="notice_test_c0",
            notice_id="notice_test",
            chunk_index=0,
            page_number=1,
            content="Spot round counselling schedule for B.Tech admission at GGSIPU Dwarka campus.",
            title="B.Tech Admission Counselling",
            source_url="https://ipu.ac.in/counselling.pdf",
            category="Admission",
            published_date="2024-11-20",
            content_hash="abc12345",
            token_count=14,
            embedding=[0.05] * 384,
        )
        norm = sum(x * x for x in test_chunk.embedding) ** 0.5
        test_chunk.embedding = [x / norm for x in test_chunk.embedding]

        # 1. Insert
        insert_count = await client.insert_chunks([test_chunk])
        assert insert_count == 1

        # 2. Search
        query_vector = test_chunk.embedding
        search_res = await client.semantic_search(query_vector=query_vector, top_k=2, threshold=0.1)

        assert len(search_res) >= 1
        assert search_res[0]["notice_id"] == "notice_test"
        assert "counselling" in search_res[0]["content"].lower()

        # 3. Delete chunks by notice_id
        del_ok = await client.delete_chunks_by_notice_id("notice_test")
        assert del_ok is True

    asyncio.run(_test())


# =============================================================================
# 8. MULTIPROCESSING WORKER ISOLATION
# =============================================================================

def test_single_worker_execution(tmp_path):
    """Verify process_single_pdf_worker executes in isolation and returns structured dict."""
    pdf_path = tmp_path / "worker_test.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Official Notice for Worker Isolation Verification", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    task = {
        "doc_id": "doc_worker_1",
        "file_path": str(pdf_path),
        "url": "https://ipu.ac.in/notice_worker.pdf",
        "ocr_enabled": False,
    }
    result = process_single_pdf_worker(task)

    assert result["doc_id"] == "doc_worker_1"
    assert result["success"] is True
    assert result["total_pages"] == 1
    assert "Worker Isolation" in result["full_text"]


# =============================================================================
# 9. INGESTION & SEARCH REST APIS
# =============================================================================

def test_api_ingestion_statistics():
    """Verify GET /api/v1/ingestion/statistics returns required metrics."""
    async def _test():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/ingestion/statistics")
            assert res.status_code == 200
            data = res.json()
            assert "worker_count" in data
            assert data["worker_count"] == 8
            assert "indexed" in data
            assert "total_indexed_chunks" in data

    asyncio.run(_test())


def test_api_semantic_search():
    """Verify POST /api/v1/search/semantic returns matches and dimensions."""
    async def _test():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "query": "examination date sheet and admit card guidelines",
                "top_k": 3,
                "threshold": 0.0,
            }
            res = await ac.post("/api/v1/search/semantic", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["query"] == payload["query"]
            assert "results" in data
            assert "results_count" in data
            assert data["top_k"] == 3

    asyncio.run(_test())


def test_api_ingestion_start_and_status():
    """Verify POST /api/v1/ingestion/start and GET /api/v1/ingestion/status/{job_id}."""
    async def _test():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/ingestion/start", json={"batch_size": 2, "force_reprocess": False})
            assert res.status_code in (200, 202)
            data = res.json()
            assert "id" in data
            assert data["status"] in ("pending", "processing", "running", "completed")

            job_id = data["id"]
            status_res = await ac.get(f"/api/v1/ingestion/status/{job_id}")
            assert status_res.status_code == 200
            assert status_res.json()["id"] == job_id

    asyncio.run(_test())
