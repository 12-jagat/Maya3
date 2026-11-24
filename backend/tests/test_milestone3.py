"""
MAYA Milestone 3 Comprehensive Test Suite.
Verifies notice crawler, document downloader, 8-process worker architecture, crawl manager, and APIs.
All network requests are mocked. Zero external network calls.
"""

import asyncio
import hashlib
import os
from pathlib import Path
import tempfile
import pytest
import httpx

from app.config import get_settings
from app.services.notice_crawler import GGSIPUNoticeCrawler, NoticeItem
from app.services.document_downloader import DocumentDownloader, DocumentDownloadResult
from app.services.pdf_worker_pool import PDFWorkerPool, process_single_pdf_worker
from app.services.crawl_manager import CrawlManager
from app.main import app

settings = get_settings()

MOCK_GGSIPU_HTML = """
<!DOCTYPE html>
<html>
<head><title>University Notices - GGSIPU</title></head>
<body>
    <table class="table-striped">
        <thead>
            <tr><th>Date</th><th>Notice / Circular</th><th>Department</th></tr>
        </thead>
        <tbody>
            <tr>
                <td>20-11-2024</td>
                <td><a href="pubinfo/datesheet_endterm2024.pdf">End Term Examination Date Sheet Nov-Dec 2024</a></td>
                <td>Examination Division</td>
            </tr>
            <tr>
                <td>18-11-2024</td>
                <td><a href="/admissions/counselling_round3.pdf">Spot Counselling Notification for B.Tech Admissions</a></td>
                <td>Admissions Branch</td>
            </tr>
            <tr>
                <td>15-11-2024</td>
                <td><a href="circular_sports_meet.php">Notice regarding Annual Inter-College Sports Meet</a></td>
                <td>Directorate of Student Welfare</td>
            </tr>
            <tr>
                <td></td>
                <td><a href="pubinfo/tender_security_2024.pdf">Quotation for Security Services</a></td>
                <td>General Administration</td>
            </tr>
        </tbody>
    </table>

    <div class="pagination">
        <a href="notices.php?page=1" class="active">1</a>
        <a href="notices.php?page=2">2</a>
        <a href="notices.php?page=3">Next &raquo;</a>
    </div>
</body>
</html>
"""


# =============================================================================
# 1. HTML PARSING & METADATA EXTRACTION
# =============================================================================

def test_notice_extraction_and_categorization():
    crawler = GGSIPUNoticeCrawler()
    base_url = "https://www.ipu.ac.in/notices.php"
    notices = crawler.extract_notices_from_html(MOCK_GGSIPU_HTML, base_url)

    assert len(notices) == 4

    # Notice 1: Exam Date Sheet
    n1 = notices[0]
    assert "End Term Examination Date Sheet" in n1.title
    assert n1.published_date == "20-11-2024"
    assert n1.category == "Examinations"
    assert n1.pdf_url == "https://www.ipu.ac.in/pubinfo/datesheet_endterm2024.pdf"

    # Notice 2: Admissions
    n2 = notices[1]
    assert "Spot Counselling Notification" in n2.title
    assert n2.published_date == "18-11-2024"
    assert n2.category == "Admissions"
    assert n2.pdf_url == "https://www.ipu.ac.in/admissions/counselling_round3.pdf"

    # Notice 3: Non-PDF link
    n3 = notices[2]
    assert "Sports Meet" in n3.title
    assert n3.pdf_url is None
    assert n3.source_url == "https://www.ipu.ac.in/circular_sports_meet.php"

    # Notice 4: Missing Date handling
    n4 = notices[3]
    assert "Security Services" in n4.title
    assert n4.published_date is None
    assert n4.category == "Tenders"


# =============================================================================
# 2. PAGINATION DISCOVERY & URL NORMALIZATION
# =============================================================================

def test_pagination_discovery():
    crawler = GGSIPUNoticeCrawler()
    base_url = "https://www.ipu.ac.in/notices.php"
    links = crawler.discover_pagination_links(MOCK_GGSIPU_HTML, base_url)

    # Discovered pagination targets
    assert any("page=2" in l for l in links)
    assert any("page=3" in l for l in links)
    for l in links:
        assert l.startswith("https://www.ipu.ac.in/")


# =============================================================================
# 3. CONTENT HASH & DUPLICATE DETECTION
# =============================================================================

def test_duplicate_content_hash():
    n1 = NoticeItem(
        title="Notice A",
        source_url="https://ipu.ac.in/a.pdf",
        pdf_url="https://ipu.ac.in/a.pdf",
        published_date="01-01-2025",
    )
    n2 = NoticeItem(
        title="Notice A",
        source_url="https://ipu.ac.in/a.pdf",
        pdf_url="https://ipu.ac.in/a.pdf",
        published_date="01-01-2025",
    )
    n3 = NoticeItem(
        title="Notice A (Revised)",
        source_url="https://ipu.ac.in/a.pdf",
        pdf_url="https://ipu.ac.in/a.pdf",
        published_date="01-01-2025",
    )

    assert n1.content_hash == n2.content_hash
    assert n1.content_hash != n3.content_hash


# =============================================================================
# 4. EXACTLY 8 PROCESS POOL WORKERS CONFIGURATION
# =============================================================================

def test_pdf_worker_pool_configured_with_exactly_8_workers():
    # Strict project requirement verification
    pool = PDFWorkerPool(max_workers=8)
    assert pool.worker_count == 8, f"Configured worker count must be exactly 8, got {pool.worker_count}"
    assert settings.PDF_WORKERS == 8, f"Default settings.PDF_WORKERS must be 8, got {settings.PDF_WORKERS}"


# =============================================================================
# 5. WORKER EXECUTION & FAILURE ISOLATION
# =============================================================================

def test_worker_failure_isolation():
    # Test 1: Non-existent file
    bad_task = {
        "doc_id": "bad123",
        "file_path": "/path/to/non_existent_file.pdf",
        "url": "http://example.com/bad.pdf",
    }
    result = process_single_pdf_worker(bad_task)
    assert result["success"] is False
    assert "does not exist" in result["error"]

    # Test 2: Invalid PDF magic bytes
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"NOT A VALID PDF FILE CONTENT")
        temp_path = f.name

    try:
        corrupted_task = {
            "doc_id": "corrupt123",
            "file_path": temp_path,
            "url": "http://example.com/corrupt.pdf",
        }
        res_corrupt = process_single_pdf_worker(corrupted_task)
        assert res_corrupt["success"] is False
        assert "Invalid PDF magic byte" in res_corrupt["error"]
    finally:
        Path(temp_path).unlink(missing_ok=True)

    # Test 3: Valid PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
        valid_path = f.name

    try:
        valid_task = {
            "doc_id": "valid123",
            "file_path": valid_path,
            "url": "http://example.com/valid.pdf",
        }
        res_valid = process_single_pdf_worker(valid_task)
        assert res_valid["success"] is True
        assert res_valid["status"] == "ready_for_m4_extraction"
    finally:
        Path(valid_path).unlink(missing_ok=True)


# =============================================================================
# 6. ASYNC PDF DOWNLOADER WITH MOCKED TRANSPORT
# =============================================================================

@pytest.mark.asyncio
async def test_document_downloader_validation_and_hash():
    with tempfile.TemporaryDirectory() as tmp_dir:
        downloader = DocumentDownloader(storage_dir=tmp_dir, max_size_mb=5)

        valid_pdf_content = b"%PDF-1.5\nSample University Exam Circular Content\n%%EOF"
        expected_hash = hashlib.sha256(valid_pdf_content).hexdigest()

        # Mock transport returning valid PDF
        def handler(request: httpx.Request) -> httpx.Response:
            if "valid.pdf" in str(request.url):
                return httpx.Response(200, content=valid_pdf_content, headers={"Content-Type": "application/pdf"})
            elif "corrupt.pdf" in str(request.url):
                return httpx.Response(200, content=b"INVALID HTML CONTENT", headers={"Content-Type": "text/html"})
            elif "404.pdf" in str(request.url):
                return httpx.Response(404)
            return httpx.Response(500)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            # 1. Download valid PDF
            res_valid = await downloader.download_document(mock_client, "http://test.edu/valid.pdf")
            assert res_valid.success is True
            assert res_valid.sha256_hash == expected_hash
            assert res_valid.file_size_bytes == len(valid_pdf_content)

            # 2. Download invalid signature
            res_invalid = await downloader.download_document(mock_client, "http://test.edu/corrupt.pdf")
            assert res_invalid.success is False
            assert "magic bytes" in res_invalid.error_message

            # 3. 404 download
            res_404 = await downloader.download_document(mock_client, "http://test.edu/404.pdf")
            assert res_404.success is False
            assert "404" in res_404.error_message


# =============================================================================
# 7. CRAWL MANAGER CONCURRENCY & RESUME LOGIC
# =============================================================================

@pytest.mark.asyncio
async def test_crawl_manager_job_lifecycle():
    manager = CrawlManager()
    assert manager.is_crawl_running() is False

    # Start job
    job = await manager.start_crawl(sources=["http://test.edu/notices"])
    assert job["status"] == "running"
    assert manager.is_crawl_running() is True

    # Attempt simultaneous job -> must raise RuntimeError
    with pytest.raises(RuntimeError):
        await manager.start_crawl()

    # Finish job manually
    await manager.db.update_crawl_job(job["id"], {"status": "completed"})
    manager._active_job_id = None
    assert manager.is_crawl_running() is False

    # Test resume
    resumed = await manager.resume_crawl(job["id"])
    assert resumed["status"] == "running"
    assert resumed["current_stage"] == "resumed"
    manager._active_job_id = None


# =============================================================================
# 8. API ENDPOINTS VERIFICATION
# =============================================================================

@pytest.mark.asyncio
async def test_api_endpoints():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # GET /health
        h_res = await client.get("/health")
        assert h_res.status_code == 200
        assert h_res.json()["status"] == "healthy"

        # GET /api/v1/status
        s_res = await client.get("/api/v1/status")
        assert s_res.status_code == 200
        assert s_res.json()["subsystems"]["notice_crawler"] == "ready"
        assert s_res.json()["subsystems"]["pdf_worker_pool"] == "ready_8_processes"

        # GET /api/v1/notices
        n_res = await client.get("/api/v1/notices")
        assert n_res.status_code == 200
        assert "items" in n_res.json()

        # GET /api/v1/notices/latest
        l_res = await client.get("/api/v1/notices/latest?limit=5")
        assert l_res.status_code == 200
        assert "items" in l_res.json()

        # GET /api/v1/crawl/history
        c_res = await client.get("/api/v1/crawl/history")
        assert c_res.status_code == 200
        assert "jobs" in c_res.json()
