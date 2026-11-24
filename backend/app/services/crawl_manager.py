"""
MAYA Crawl Job Manager.
Orchestrates multi-source notice discovery, document downloading, and 8-process worker execution.
Manages job lifecycle, stage progression, concurrency locking, and resume capability.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

import httpx

from app.database.supabase_client import get_supabase_client
from app.services.document_downloader import DocumentDownloader
from app.services.notice_crawler import DEFAULT_GGSIPU_SOURCES, GGSIPUNoticeCrawler
from app.services.pdf_worker_pool import get_pdf_worker_pool
from app.utils.logger import logger


class CrawlManager:
    """
    Coordinates asynchronous crawling, notice upserts to Supabase,
    concurrent PDF downloads, and 8-worker process pool execution.
    """

    def __init__(self):
        self.db = get_supabase_client()
        self.crawler = GGSIPUNoticeCrawler()
        self.downloader = DocumentDownloader()
        self.worker_pool = get_pdf_worker_pool()
        self._lock = asyncio.Lock()
        self._active_job_id: Optional[str] = None

    def is_crawl_running(self) -> bool:
        """Check if an active crawl is currently in flight."""
        return self._active_job_id is not None

    async def start_crawl(
        self,
        sources: Optional[List[str]] = None,
        max_pages_per_source: int = 5,
        download_pdfs: bool = True,
    ) -> Dict[str, Any]:
        """
        Initiate a new full or partial crawl.
        Guarantees that two simultaneous full crawls cannot run at once.
        """
        async with self._lock:
            if self.is_crawl_running():
                raise RuntimeError(
                    f"A crawl job is already currently running (Job ID: {self._active_job_id}). "
                    "Cannot start simultaneous full crawls."
                )

            job_id = str(uuid.uuid4())
            self._active_job_id = job_id

        target_sources = sources or DEFAULT_GGSIPU_SOURCES
        job_record = {
            "id": job_id,
            "status": "running",
            "current_stage": "discovering_pages",
            "current_source": target_sources[0] if target_sources else "",
            "pages_discovered": len(target_sources),
            "pages_processed": 0,
            "notices_discovered": 0,
            "new_notices": 0,
            "updated_notices": 0,
            "skipped_notices": 0,
            "pdfs_downloaded": 0,
            "pdfs_failed": 0,
            "last_processed_url": "",
            "errors": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.db.create_crawl_job(job_record)
        await self.db.add_crawl_event(
            job_id, "start", f"Initiated crawl across {len(target_sources)} GGSIPU sources."
        )

        return job_record

    async def resume_crawl(self, job_id: str) -> Dict[str, Any]:
        """
        Resume an interrupted or failed crawl job.
        Avoids re-crawling already processed URLs.
        """
        async with self._lock:
            if self.is_crawl_running():
                raise RuntimeError("Another crawl job is currently running.")
            self._active_job_id = job_id

        existing_job = await self.db.get_crawl_job(job_id)
        if not existing_job:
            self._active_job_id = None
            raise ValueError(f"Crawl job {job_id} not found.")

        updates = {
            "status": "running",
            "current_stage": "resumed",
        }
        await self.db.update_crawl_job(job_id, updates)
        await self.db.add_crawl_event(job_id, "resumed", f"Resumed crawl from job {job_id}")
        existing_job.update(updates)
        return existing_job

    async def run_crawl_pipeline(
        self,
        job_id: str,
        sources: Optional[List[str]] = None,
        max_pages_per_source: int = 5,
        download_pdfs: bool = True,
    ):
        """
        The complete asynchronous crawl pipeline executed as a FastAPI BackgroundTask.
        """
        target_sources = sources or DEFAULT_GGSIPU_SOURCES
        logger.info(f"Starting crawl execution for Job {job_id} on {len(target_sources)} sources...")

        pages_discovered = len(target_sources)
        pages_processed = 0
        notices_discovered = 0
        new_notices = 0
        updated_notices = 0
        skipped_notices = 0
        pdfs_downloaded = 0
        pdfs_failed = 0
        job_errors: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=20.0) as http_client:
                # =============================================================
                # STAGE 1 & 2: DISCOVER PAGES & EXTRACT NOTICES
                # =============================================================
                for src in target_sources:
                    try:
                        await self.db.update_crawl_job(
                            job_id,
                            {
                                "current_source": src,
                                "current_stage": "discovering_pages",
                            },
                        )

                        page_queue = [src]
                        source_pages_count = 0

                        while page_queue and source_pages_count < max_pages_per_source:
                            current_url = page_queue.pop(0)
                            if current_url in self.crawler.visited_urls:
                                continue

                            self.crawler.visited_urls.add(current_url)
                            source_pages_count += 1
                            pages_processed += 1

                            html = await self.crawler.fetch_html(http_client, current_url)
                            if not html:
                                continue

                            # Discover dynamic pagination
                            new_pages = self.crawler.discover_pagination_links(html, current_url)
                            for np in new_pages:
                                if np not in self.crawler.visited_urls and np not in page_queue:
                                    page_queue.append(np)
                                    pages_discovered += 1

                            # Extract notices from current page
                            notices = self.crawler.extract_notices_from_html(html, current_url)
                            notices_discovered += len(notices)

                            # Idempotently store notices in Supabase
                            for item in notices:
                                notice_dict = item.to_dict()
                                existing = await self.db.get_notice_by_source_url(notice_dict["source_url"])

                                if existing is None:
                                    await self.db.upsert_notice(notice_dict)
                                    new_notices += 1
                                else:
                                    # Check if content changed
                                    if existing.get("content_hash") != notice_dict["content_hash"]:
                                        # Preserve prior processing and indexing
                                        notice_dict["processing_status"] = existing.get("processing_status", "pending")
                                        notice_dict["indexed_at"] = existing.get("indexed_at")
                                        await self.db.upsert_notice(notice_dict)
                                        updated_notices += 1
                                    else:
                                        skipped_notices += 1

                            # Update progress periodically
                            await self.db.update_crawl_job(
                                job_id,
                                {
                                    "pages_discovered": pages_discovered,
                                    "pages_processed": pages_processed,
                                    "notices_discovered": notices_discovered,
                                    "new_notices": new_notices,
                                    "updated_notices": updated_notices,
                                    "skipped_notices": skipped_notices,
                                    "last_processed_url": current_url,
                                    "current_stage": "extracting_notices",
                                },
                            )

                    except Exception as src_err:
                        err_msg = f"Source crawl failed for {src}: {str(src_err)}"
                        logger.error(err_msg)
                        job_errors.append(err_msg)
                        await self.db.add_crawl_event(job_id, "error", err_msg)
                        # Continue to other sources if one source fails!
                        continue

                # =============================================================
                # STAGE 3: ASYNC PDF DOWNLOADS (CONCURRENCY=10)
                # =============================================================
                pending_download_tasks: List[Dict[str, Any]] = []

                if download_pdfs:
                    await self.db.update_crawl_job(
                        job_id, {"current_stage": "downloading_pdfs"}
                    )
                    await self.db.add_crawl_event(
                        job_id, "downloading_pdfs", "Starting concurrent PDF download phase..."
                    )

                    # Query notices with valid pdf_urls
                    notice_res = await self.db.list_notices(limit=100)
                    notices_with_pdf = [n for n in notice_res["items"] if n.get("pdf_url")]

                    pdf_urls = [n["pdf_url"] for n in notices_with_pdf]
                    known_hashes = {
                        n["pdf_url"]: n.get("content_hash", "")
                        for n in notices_with_pdf
                        if n.get("content_hash")
                    }

                    download_results = await self.downloader.download_batch(pdf_urls, known_hashes=known_hashes)

                    for res in download_results:
                        if res.success:
                            pdfs_downloaded += 1
                            if res.file_path:
                                pending_download_tasks.append({
                                    "doc_id": res.doc_id,
                                    "file_path": res.file_path,
                                    "url": res.url,
                                })
                        else:
                            pdfs_failed += 1
                            if res.error_message:
                                job_errors.append(f"PDF download failed ({res.url}): {res.error_message}")

                    await self.db.update_crawl_job(
                        job_id,
                        {
                            "pdfs_downloaded": pdfs_downloaded,
                            "pdfs_failed": pdfs_failed,
                        },
                    )

                # =============================================================
                # STAGE 4: EXACTLY 8 PROCESS POOL WORKER EXECUTION
                # =============================================================
                if pending_download_tasks:
                    await self.db.update_crawl_job(
                        job_id, {"current_stage": "processing_documents"}
                    )
                    await self.db.add_crawl_event(
                        job_id,
                        "processing_documents",
                        f"Submitting {len(pending_download_tasks)} PDFs to 8-worker ProcessPool...",
                    )

                    worker_results = await self.worker_pool.process_batch_async(pending_download_tasks)

                    # Update status in Supabase for each processed PDF
                    for w_res in worker_results:
                        status_label = "processed" if w_res.get("success") else "failed"
                        doc_url = w_res.get("url")
                        if doc_url:
                            await self.db.update_notice_status(doc_url, status_label)

                # =============================================================
                # STAGE 5: COMPLETION
                # =============================================================
                completed_at = datetime.now(timezone.utc).isoformat()
                final_status = "completed" if not job_errors else "completed_with_warnings"

                await self.db.update_crawl_job(
                    job_id,
                    {
                        "status": final_status,
                        "current_stage": "completed",
                        "completed_at": completed_at,
                        "errors": job_errors,
                    },
                )
                await self.db.add_crawl_event(
                    job_id, "completed", f"Crawl job completed successfully. New notices: {new_notices}."
                )
                logger.info(f"Crawl Job {job_id} finished: status={final_status}, new={new_notices}")

        except Exception as global_err:
            logger.exception(f"Unhandled exception in crawl pipeline for job {job_id}: {global_err}")
            await self.db.update_crawl_job(
                job_id,
                {
                    "status": "failed",
                    "current_stage": "failed",
                    "errors": [str(global_err)],
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.db.add_crawl_event(job_id, "failed", f"Fatal error: {str(global_err)}")

        finally:
            async with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None


# Singleton instance
_global_crawl_manager: Optional[CrawlManager] = None


def get_crawl_manager() -> CrawlManager:
    """Return singleton instance of CrawlManager."""
    global _global_crawl_manager
    if _global_crawl_manager is None:
        _global_crawl_manager = CrawlManager()
    return _global_crawl_manager
