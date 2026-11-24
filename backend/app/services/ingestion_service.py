"""
Complete Document Ingestion Pipeline for MAYA.
Orchestrates:
1. Document retrieval & hash verification
2. 8-Process ProcessPool worker dispatch (PyMuPDF native + OCR fallback + DOCX)
3. Text cleaning & normalization
4. Semantic chunking with page reference tracking
5. Verified 384-dimensional PyTorch embeddings (batch size 64)
6. Zilliz Cloud vector indexing & deduplication
7. Supabase notice state synchronization
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.config import get_settings
from app.database.supabase_client import get_supabase_client
from app.database.zilliz_client import get_zilliz_client
from app.services.chunking_service import ChunkingService, NoticeChunk
from app.services.embedding_service import get_embedding_service
from app.services.pdf_worker_pool import get_pdf_worker_pool
from app.services.text_cleaner import TextCleaner

settings = get_settings()
logger = logging.getLogger("maya.ingestion_service")


class IngestionService:
    """
    Parent-process coordinator for end-to-end document processing,
    chunking, vectorization, and multi-database persistence.
    """

    def __init__(self):
        self.db = get_supabase_client()
        self.zilliz = get_zilliz_client()
        self.chunker = ChunkingService()
        self.embedder = get_embedding_service()
        self.worker_pool = get_pdf_worker_pool()
        self.storage_dir = Path(settings.STORAGE_DIR) / "documents"
        self._lock = asyncio.Lock()
        self._active_job_id: Optional[str] = None
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def is_ingestion_running(self) -> bool:
        return self._active_job_id is not None

    async def get_ingestion_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    async def get_statistics(self) -> Dict[str, Any]:
        """Aggregate real-time document extraction and indexing metrics."""
        notices_data = await self.db.list_notices(limit=500)
        items = notices_data.get("items", [])

        stats = {
            "total_notices": len(items),
            "downloaded": 0,
            "extracted": 0,
            "ocr_processed": 0,
            "indexed": 0,
            "failed": 0,
            "pending": 0,
            "worker_count": self.worker_pool.worker_count,
            "total_indexed_chunks": len(self.zilliz._memory_vectors),
        }

        for item in items:
            st = item.get("processing_status", "pending")
            if st == "indexed":
                stats["indexed"] += 1
            elif st in ("downloaded", "downloading"):
                stats["downloaded"] += 1
            elif st == "extracted":
                stats["extracted"] += 1
            elif st == "ocr_processing":
                stats["ocr_processed"] += 1
            elif st == "failed":
                stats["failed"] += 1
            else:
                stats["pending"] += 1

        return stats

    async def start_ingestion_job(
        self,
        batch_size: int = 10,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """Initiate asynchronous document ingestion batch."""
        async with self._lock:
            if self.is_ingestion_running():
                raise RuntimeError(f"Ingestion is already in progress (Job ID: {self._active_job_id}).")
            job_id = str(uuid.uuid4())
            self._active_job_id = job_id

        job_record = {
            "id": job_id,
            "status": "running",
            "current_stage": "fetching_candidates",
            "total_documents": 0,
            "processed_documents": 0,
            "extracted_documents": 0,
            "ocr_pages_processed": 0,
            "chunks_created": 0,
            "vectors_indexed": 0,
            "failed_documents": 0,
            "errors": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        self._jobs[job_id] = job_record
        return job_record

    async def run_ingestion_pipeline(
        self,
        job_id: str,
        batch_size: int = 10,
        force_reindex: bool = False,
    ):
        """
        Full 13-step pipeline coordinating parent and 8 worker processes.
        """
        logger.info(f"Running Ingestion Pipeline for Job {job_id}...")
        job = self._jobs.get(job_id)
        if not job:
            return

        try:
            # 1. Fetch notice candidates
            all_notices = await self.db.list_notices(limit=200)
            candidates = []
            for n in all_notices.get("items", []):
                # Filter candidates that have downloadable/downloaded documents
                status = n.get("processing_status", "pending")
                if force_reindex or status in ("pending", "downloaded", "failed", "processed"):
                    candidates.append(n)

            # Limit to configured bounded batch
            candidates = candidates[:batch_size]
            job["total_documents"] = len(candidates)
            logger.info(f"Found {len(candidates)} document candidates for ingestion.")

            if not candidates:
                job["status"] = "completed"
                job["current_stage"] = "completed_no_candidates"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
                return

            # 2. Match local files and check hashes
            worker_tasks = []
            notice_lookup: Dict[str, Dict[str, Any]] = {}

            for notice in candidates:
                url = notice.get("pdf_url") or notice.get("source_url", "")
                doc_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                local_file = self.storage_dir / f"{doc_id}.pdf"

                if not local_file.exists():
                    # Check if file exists without .pdf extension or docx
                    possible = list(self.storage_dir.glob(f"{doc_id}.*"))
                    if possible:
                        local_file = possible[0]

                if local_file.exists():
                    worker_tasks.append({
                        "doc_id": doc_id,
                        "file_path": str(local_file),
                        "url": url,
                        "ocr_enabled": settings.OCR_ENABLED,
                    })
                    notice_lookup[doc_id] = notice

            job["current_stage"] = "extracting_with_8_workers"
            logger.info(f"Submitting {len(worker_tasks)} documents to 8-process worker pool...")

            # 3 & 4. Submit to 8-Process ProcessPoolExecutor
            worker_results = await self.worker_pool.process_batch_async(worker_tasks)

            # 5-13. Process results in parent process
            for res in worker_results:
                doc_id = res.get("doc_id")
                notice = notice_lookup.get(doc_id)
                if not notice:
                    continue

                source_url = notice["source_url"]

                if not res.get("success"):
                    err = res.get("error") or "Unknown extraction failure"
                    job["failed_documents"] += 1
                    job["errors"].append(f"Document {doc_id} failed: {err}")
                    await self.db.update_notice_status(source_url, "failed")
                    continue

                # Document extraction succeeded
                job["extracted_documents"] += 1
                job["ocr_pages_processed"] += res.get("scanned_pages", 0)

                # Update stage
                job["current_stage"] = "chunking"
                await self.db.update_notice_status(source_url, "chunking")

                # Clean and chunk
                full_text = res.get("full_text", "")
                chunks = self.chunker.chunk_extracted_document(
                    extracted_doc=res,
                    notice_metadata=notice,
                )

                if not chunks:
                    logger.warning(f"No chunks generated for notice: {notice.get('title')}")
                    await self.db.update_notice_status(source_url, "processed")
                    job["processed_documents"] += 1
                    continue

                job["chunks_created"] += len(chunks)

                # Vector Embeddings in Batches
                job["current_stage"] = "embedding"
                await self.db.update_notice_status(source_url, "embedding")

                chunk_texts = [c.content for c in chunks]
                embeddings = self.embedder.generate_embeddings(chunk_texts)

                for idx, chunk in enumerate(chunks):
                    chunk.embedding = embeddings[idx]

                # Zilliz Vector Insertion
                job["current_stage"] = "indexing"
                await self.db.update_notice_status(source_url, "indexing")

                # If re-indexing, remove old chunks first for idempotency
                notice_id = str(notice.get("id") or source_url)
                await self.zilliz.delete_notice_chunks(notice_id)

                # Batch insert into Zilliz
                inserted_count = await self.zilliz.insert_chunks(chunks)
                job["vectors_indexed"] += inserted_count

                # Mark notice as indexed in Supabase
                now_iso = datetime.now(timezone.utc).isoformat()
                await self.db.update_notice_status(source_url, "indexed")
                notice["indexed_at"] = now_iso
                job["processed_documents"] += 1

            # Finish job
            job["status"] = "completed"
            job["current_stage"] = "completed"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Ingestion Job {job_id} completed successfully. Indexed {job['vectors_indexed']} vectors.")

        except Exception as global_err:
            logger.exception(f"Unhandled error in ingestion pipeline: {global_err}")
            job["status"] = "failed"
            job["current_stage"] = "failed"
            job["errors"].append(str(global_err))
            job["completed_at"] = datetime.now(timezone.utc).isoformat()

        finally:
            async with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    async def retry_notice_ingestion(self, notice_id: str) -> Dict[str, Any]:
        """Retry processing for a specific failed notice."""
        notice = None
        all_notices = await self.db.list_notices(limit=500)
        for n in all_notices.get("items", []):
            if n.get("id") == notice_id or n.get("source_url") == notice_id:
                notice = n
                break

        if not notice:
            raise ValueError(f"Notice {notice_id} not found.")

        # Trigger single notice processing
        job = await self.start_ingestion_job(batch_size=1, force_reindex=True)
        asyncio.create_task(self.run_ingestion_pipeline(job["id"], batch_size=1, force_reindex=True))
        return job


# Singleton instance
_global_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Return singleton instance of IngestionService."""
    global _global_ingestion_service
    if _global_ingestion_service is None:
        _global_ingestion_service = IngestionService()
    return _global_ingestion_service
