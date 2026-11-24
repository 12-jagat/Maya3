"""
Asynchronous PDF & Document Downloader Service.
Streams documents to disk with SHA-256 calculation, size enforcement, and magic byte validation.
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

PDF_MAGIC_BYTES = b"%PDF-"


class DocumentDownloadResult:
    """Structured result of document download operation."""

    def __init__(
        self,
        url: str,
        success: bool,
        doc_id: str,
        file_path: Optional[str] = None,
        file_size_bytes: int = 0,
        sha256_hash: Optional[str] = None,
        error_message: Optional[str] = None,
        skipped_as_duplicate: bool = False,
    ):
        self.url = url
        self.success = success
        self.doc_id = doc_id
        self.file_path = file_path
        self.file_size_bytes = file_size_bytes
        self.sha256_hash = sha256_hash
        self.error_message = error_message
        self.skipped_as_duplicate = skipped_as_duplicate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict without exposing absolute local filesystem paths."""
        return {
            "url": self.url,
            "success": self.success,
            "doc_id": self.doc_id,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "error_message": self.error_message,
            "skipped_as_duplicate": self.skipped_as_duplicate,
        }


class DocumentDownloader:
    """
    Concurrent async PDF downloader with streaming validation.
    Enforces size limits, verifies PDF headers, and computes cryptographic hashes.
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        max_size_mb: Optional[int] = None,
        concurrency: Optional[int] = None,
        timeout: float = 30.0,
    ):
        self.storage_dir = Path(storage_dir or settings.STORAGE_DIR) / "documents"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = (max_size_mb or settings.PDF_MAX_SIZE_MB) * 1024 * 1024
        self.concurrency = concurrency or settings.PDF_DOWNLOAD_CONCURRENCY
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(self.concurrency)

    def _get_document_id(self, url: str) -> str:
        """Generate a deterministic document ID from URL."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    async def download_document(
        self, client: httpx.AsyncClient, url: str, known_hash: Optional[str] = None
    ) -> DocumentDownloadResult:
        """
        Download a single PDF document asynchronously with streaming and verification.
        """
        doc_id = self._get_document_id(url)
        target_file = self.storage_dir / f"{doc_id}.pdf"

        # Check if already downloaded and verified
        if target_file.exists() and target_file.stat().st_size > 0:
            existing_size = target_file.stat().st_size
            try:
                hasher = hashlib.sha256()
                with open(target_file, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hasher.update(chunk)
                computed = hasher.hexdigest()
                if known_hash and known_hash == computed:
                    logger.info(f"Skipping download, unchanged document already cached: {doc_id}")
                    return DocumentDownloadResult(
                        url=url,
                        success=True,
                        doc_id=doc_id,
                        file_path=str(target_file),
                        file_size_bytes=existing_size,
                        sha256_hash=computed,
                        skipped_as_duplicate=True,
                    )
            except Exception as e:
                logger.warning(f"Failed verifying cached file for {doc_id}, will re-download: {e}")

        async with self.semaphore:
            headers = {
                "User-Agent": "MAYA-UniversityAssistant/1.0",
                "Accept": "application/pdf,*/*",
            }

            temp_file = self.storage_dir / f"{doc_id}.tmp"
            try:
                async with client.stream("GET", url, headers=headers, timeout=self.timeout, follow_redirects=True) as response:
                    if response.status_code != 200:
                        return DocumentDownloadResult(
                            url=url,
                            success=False,
                            doc_id=doc_id,
                            error_message=f"HTTP download returned status code {response.status_code}",
                        )

                    # Validate Content-Length header if present
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_size_bytes:
                        return DocumentDownloadResult(
                            url=url,
                            success=False,
                            doc_id=doc_id,
                            error_message=f"File exceeds maximum allowed size ({settings.PDF_MAX_SIZE_MB}MB)",
                        )

                    hasher = hashlib.sha256()
                    bytes_downloaded = 0
                    first_chunk = True
                    abort_error: Optional[str] = None

                    with open(temp_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            if not chunk:
                                continue

                            # Validate magic bytes on initial stream chunk
                            if first_chunk:
                                first_chunk = False
                                if not chunk.startswith(PDF_MAGIC_BYTES) and b"%PDF-" not in chunk[:1024]:
                                    abort_error = "Downloaded content lacks valid PDF magic bytes signature (%PDF-)"
                                    break

                            bytes_downloaded += len(chunk)
                            if bytes_downloaded > self.max_size_bytes:
                                abort_error = f"Download size aborted: exceeded {settings.PDF_MAX_SIZE_MB}MB limit"
                                break

                            hasher.update(chunk)
                            f.write(chunk)

                    # Clean up and return error if aborted during stream
                    if abort_error:
                        temp_file.unlink(missing_ok=True)
                        return DocumentDownloadResult(
                            url=url,
                            success=False,
                            doc_id=doc_id,
                            error_message=abort_error,
                        )

                    # Atomic rename from tmp to final target
                    temp_file.replace(target_file)
                    sha256_hash = hasher.hexdigest()


                    logger.info(f"Successfully downloaded {url} -> {doc_id}.pdf ({bytes_downloaded} bytes)")
                    return DocumentDownloadResult(
                        url=url,
                        success=True,
                        doc_id=doc_id,
                        file_path=str(target_file),
                        file_size_bytes=bytes_downloaded,
                        sha256_hash=sha256_hash,
                    )

            except httpx.TimeoutException:
                temp_file.unlink(missing_ok=True)
                return DocumentDownloadResult(
                    url=url, success=False, doc_id=doc_id, error_message="Download timed out"
                )
            except Exception as e:
                temp_file.unlink(missing_ok=True)
                logger.error(f"Error downloading document from {url}: {e}")
                return DocumentDownloadResult(
                    url=url, success=False, doc_id=doc_id, error_message=str(e)
                )

    async def download_batch(
        self, urls: List[str], known_hashes: Optional[Dict[str, str]] = None
    ) -> List[DocumentDownloadResult]:
        """Download a batch of URLs concurrently using the configured concurrency."""
        known_hashes = known_hashes or {}
        async with httpx.AsyncClient() as client:
            tasks = [
                self.download_document(client, url, known_hash=known_hashes.get(url))
                for url in urls
            ]
            return await asyncio.gather(*tasks)
