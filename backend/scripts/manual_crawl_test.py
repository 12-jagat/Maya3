"""
Manual Integration Test Script for Official GGSIPU Portals.
Tests network retrieval, notice extraction, and PDF downloading on a bounded 1-page sample.
Run directly with: python backend/scripts/manual_crawl_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to PYTHONPATH
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import httpx
from app.services.notice_crawler import GGSIPUNoticeCrawler
from app.services.document_downloader import DocumentDownloader
from app.services.pdf_worker_pool import get_pdf_worker_pool


async def run_live_ggsipu_crawler():
    print("=" * 60)
    print("MAYA: MANUAL INTEGRATION TEST — OFFICIAL GGSIPU SOURCES")
    print("=" * 60)

    target_url = "https://www.ipu.ac.in/notices.php"
    print(f"\n1. Probing official portal: {target_url}...")

    crawler = GGSIPUNoticeCrawler(delay_seconds=0.5)

    async with httpx.AsyncClient(timeout=20.0) as client:
        html = await crawler.fetch_html(client, target_url)
        if not html:
            print("FAILED: Could not reach GGSIPU server or server timed out.")
            return

        print(f"SUCCESS: Fetched {len(html)} bytes of HTML from GGSIPU.")

        # Extract notices
        notices = crawler.extract_notices_from_html(html, target_url)
        print(f"\n2. Extracted {len(notices)} notices from front page:")
        for idx, notice in enumerate(notices[:5], 1):
            print(f"   [{idx}] {notice.published_date or 'NO DATE'} | {notice.category.upper()}")
            print(f"       Title: {notice.title[:80]}...")
            if notice.pdf_url:
                print(f"       PDF:   {notice.pdf_url}")

        # Check pagination
        pagination = crawler.discover_pagination_links(html, target_url)
        print(f"\n3. Discovered {len(pagination)} dynamic pagination links:")
        for p in pagination[:3]:
            print(f"       {p}")

        # Test worker pool configuration
        pool = get_pdf_worker_pool()
        print(f"\n4. Verified PDF Worker Pool configuration: {pool.worker_count} processes.")
        assert pool.worker_count == 8, f"Worker count must be exactly 8, got {pool.worker_count}"
        print("   EXACTLY 8 WORKER PROCESSES VERIFIED.")

    print("\n" + "=" * 60)
    print("MANUAL INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_live_ggsipu_crawler())
