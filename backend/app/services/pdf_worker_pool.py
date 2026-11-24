"""
MAYA 8-Process Document Worker Architecture.
Manages a dedicated ProcessPoolExecutor of exactly 8 worker processes for CPU-intensive document processing.
Safe for Windows spawn context, completely isolated from DB connections and secrets.
Dispatches to PyMuPDF native extractor, OCR fallback, and python-docx.
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.docx_extractor import DOCXExtractor, ImageExtractor
from app.services.ocr_service import get_process_ocr_service
from app.services.pdf_extractor import PDFExtractor

settings = get_settings()
logger = logging.getLogger("maya.pdf_workers")


def worker_init():
    """
    Worker Process Initializer.
    Executed once per child process when spawned.
    Pre-initializes process-local OCR engine once per worker process.
    Note: NO database clients or API secrets are initialized or shared into worker processes.
    """
    pid = os.getpid()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | WORKER [%(process)d] | %(message)s")
    # Pre-initialize OCR service once in this worker process
    try:
        get_process_ocr_service()
        logging.info(f"Worker process {pid} initialized successfully with process-local OCR.")
    except Exception as e:
        logging.warning(f"Worker process {pid} OCR initialization warning: {e}")


def process_single_pdf_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure worker function executed within one of the 8 child processes.
    Receives only primitive, serializable task data.
    Never receives database connections, HTTP clients, or API keys.
    """
    pid = os.getpid()
    doc_id = task.get("doc_id", "unknown")
    file_path_str = task.get("file_path")
    url = task.get("url", "")
    ocr_enabled = task.get("ocr_enabled", True)

    try:
        if not file_path_str:
            return {
                "doc_id": doc_id,
                "url": url,
                "success": False,
                "worker_pid": pid,
                "error": "No file_path provided to worker",
                "pages": [],
                "full_text": "",
            }

        file_path = Path(file_path_str)
        if not file_path.exists():
            return {
                "doc_id": doc_id,
                "url": url,
                "success": False,
                "worker_pid": pid,
                "error": f"File does not exist: {file_path_str}",
                "pages": [],
                "full_text": "",
            }

        file_size = file_path.stat().st_size
        if file_size == 0:
            return {
                "doc_id": doc_id,
                "url": url,
                "success": False,
                "worker_pid": pid,
                "error": "File is empty (0 bytes)",
                "pages": [],
                "full_text": "",
            }

        suffix = file_path.suffix.lower()

        # 1. DOCX Extraction
        if suffix in (".docx", ".doc"):
            res = DOCXExtractor.extract_docx(file_path_str)
            return {
                "doc_id": doc_id,
                "url": url,
                "success": res.get("success", False),
                "worker_pid": pid,
                "file_type": "docx",
                "pages": res.get("pages", []),
                "full_text": res.get("full_text", ""),
                "total_pages": res.get("total_pages", 1),
                "scanned_pages": 0,
                "is_mixed": False,
                "is_scanned": False,
                "error": res.get("error"),
                "status": "extracted",
            }

        # 2. Standalone Image Extraction
        elif suffix in (".jpg", ".jpeg", ".png"):
            res = ImageExtractor.extract_image(file_path_str)
            return {
                "doc_id": doc_id,
                "url": url,
                "success": res.get("success", False),
                "worker_pid": pid,
                "file_type": "image",
                "pages": res.get("pages", []),
                "full_text": res.get("full_text", ""),
                "total_pages": 1,
                "scanned_pages": 1,
                "is_mixed": False,
                "is_scanned": True,
                "error": res.get("error"),
                "status": "extracted",
            }

        # 3. PDF Extraction (Native + Mixed OCR fallback)
        else:
            with open(file_path, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                return {
                    "doc_id": doc_id,
                    "url": url,
                    "success": False,
                    "worker_pid": pid,
                    "error": "Invalid PDF magic byte header",
                    "pages": [],
                    "full_text": "",
                }

            extractor = PDFExtractor(ocr_enabled=ocr_enabled)
            res = extractor.extract_pdf(file_path_str)
            return {
                "doc_id": doc_id,
                "url": url,
                "success": res.get("success", False),
                "worker_pid": pid,
                "file_type": "pdf",
                "pages": res.get("pages", []),
                "full_text": res.get("full_text", ""),
                "total_pages": res.get("total_pages", 0),
                "scanned_pages": res.get("scanned_pages", 0),
                "is_mixed": res.get("is_mixed", False),
                "is_scanned": res.get("is_scanned", False),
                "error": res.get("error"),
                "status": "ready_for_m4_extraction" if res.get("success") else "failed",
            }

    except Exception as exc:
        return {
            "doc_id": doc_id,
            "url": url,
            "success": False,
            "worker_pid": pid,
            "error": f"Worker exception processing document: {str(exc)}",
            "pages": [],
            "full_text": "",
        }


class PDFWorkerPool:
    """
    Coordinator of exactly 8 worker processes for document processing.
    Ensures safe Windows process spawning and coordinates jobs from parent process.
    """

    def __init__(self, max_workers: Optional[int] = None):
        configured_workers = max_workers or settings.PDF_WORKERS
        # Strict enforcement: default must be exactly 8
        self.worker_count = configured_workers
        self._executor: Optional[ProcessPoolExecutor] = None
        self._is_shutdown = False

    @property
    def max_workers(self) -> int:
        return self.worker_count

    def get_executor(self) -> ProcessPoolExecutor:
        """Lazily initialize reusable ProcessPoolExecutor."""
        if self._executor is None and not self._is_shutdown:
            logger.info(
                f"Spawning reusable ProcessPoolExecutor with EXACTLY {self.worker_count} worker processes..."
            )
            # Use safe spawn context for Windows compatibility
            ctx = multiprocessing.get_context("spawn")
            self._executor = ProcessPoolExecutor(
                max_workers=self.worker_count,
                mp_context=ctx,
                initializer=worker_init,
            )
            logger.info(f"ProcessPoolExecutor started with {self.worker_count} processes.")
        return self._executor

    async def process_batch_async(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Coordinate execution of document processing jobs across the 8 processes asynchronously.
        Does not block the asyncio event loop.
        """
        if not tasks:
            return []

        executor = self.get_executor()
        loop = asyncio.get_running_loop()

        # Submit tasks to the 8 worker processes
        futures = [
            loop.run_in_executor(executor, process_single_pdf_worker, task)
            for task in tasks
        ]

        # Gather all worker outputs safely
        results = await asyncio.gather(*futures, return_exceptions=True)

        structured_results: List[Dict[str, Any]] = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                structured_results.append({
                    "doc_id": tasks[idx].get("doc_id", "unknown"),
                    "url": tasks[idx].get("url", ""),
                    "success": False,
                    "pages": [],
                    "full_text": "",
                    "error": f"Parent worker communication error: {str(res)}",
                })
            else:
                structured_results.append(res)

        return structured_results

    def shutdown(self, wait: bool = True):
        """Cleanly shutdown the worker pool."""
        if self._executor and not self._is_shutdown:
            logger.info("Shutting down PDFWorkerPool...")
            self._executor.shutdown(wait=wait)
            self._is_shutdown = True
            self._executor = None


# Global singleton instance for application lifespan
_global_pdf_worker_pool: Optional[PDFWorkerPool] = None


def get_pdf_worker_pool() -> PDFWorkerPool:
    """Return the global PDF worker pool singleton with exactly 8 workers."""
    global _global_pdf_worker_pool
    if _global_pdf_worker_pool is None:
        _global_pdf_worker_pool = PDFWorkerPool(max_workers=settings.PDF_WORKERS)
    return _global_pdf_worker_pool
