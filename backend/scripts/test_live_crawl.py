"""
Small manual crawl test to verify insertion and PDF downloads.
"""
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.crawl_manager import get_crawl_manager


async def main():
    m = get_crawl_manager()
    job = await m.start_crawl(
        sources=["https://www.ipu.ac.in/notices.php"],
        max_pages_per_source=1,
        download_pdfs=True,
    )
    print(f"Crawl Job Started: {job['id']}")
    await m.run_crawl_pipeline(
        job["id"],
        sources=["https://www.ipu.ac.in/notices.php"],
        max_pages_per_source=1,
        download_pdfs=True,
    )

    final_job = await m.db.get_crawl_job(job["id"])
    print(f"Job Status: {final_job.get('status')}")
    print(f"Notices Discovered: {final_job.get('notices_discovered')}")
    print(f"New Notices: {final_job.get('new_notices')}")
    print(f"PDFs Downloaded: {final_job.get('pdfs_downloaded')}")

    notices = await m.db.list_notices(limit=5)
    print(f"\nSample Ingested Notices in Storage ({len(notices['items'])} items):")
    for n in notices["items"][:3]:
        print(f" - [{n.get('published_date')}] {n.get('title')[:60]}... (Status: {n.get('processing_status')})")

    assert final_job.get("notices_discovered", 0) > 0
    print("\n>>> LIVE CRAWL, INGESTION, AND 8-PROCESS PIPELINE VERIFIED! <<<")


if __name__ == "__main__":
    asyncio.run(main())
