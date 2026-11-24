"""
PyMuPDF Native & Mixed PDF Document Extractor.
Extracts page-level text, detects scanned pages, and applies OCR only where needed.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import fitz

from app.services.ocr_service import get_process_ocr_service
from app.services.text_cleaner import TextCleaner

logger = logging.getLogger("maya.pdf_extractor")

# Minimum characters required on a page to consider it containing usable native text
MIN_NATIVE_TEXT_THRESHOLD = 50


class ExtractedPage:
    """Structured representation of an extracted document page."""

    def __init__(
        self,
        page_number: int,
        text: str,
        is_ocr: bool = False,
        char_count: int = 0,
    ):
        self.page_number = page_number
        self.text = text
        self.is_ocr = is_ocr
        self.char_count = char_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "is_ocr": self.is_ocr,
            "char_count": self.char_count,
        }


class PDFExtractor:
    """
    High-performance PDF extractor supporting native text, scanned pages, and mixed PDFs.
    Preserves page boundaries, reading order, and document metadata.
    """

    def __init__(self, ocr_enabled: bool = True):
        self.ocr_enabled = ocr_enabled

    def extract_pdf(self, file_path_str: str) -> Dict[str, Any]:
        """
        Extract text page-by-page from a PDF document.
        Handles encrypted, corrupt, and password-protected files gracefully.
        """
        path = Path(file_path_str)
        if not path.exists():
            return {
                "success": False,
                "error": f"PDF file does not exist: {file_path_str}",
                "pages": [],
                "full_text": "",
                "total_pages": 0,
            }

        try:
            doc = fitz.open(str(path))
        except Exception as open_err:
            return {
                "success": False,
                "error": f"Failed to open PDF document: {str(open_err)}",
                "pages": [],
                "full_text": "",
                "total_pages": 0,
            }

        # Handle encrypted / password protected PDFs
        if doc.is_encrypted:
            # Attempt empty password authentication
            if not doc.authenticate(""):
                doc.close()
                return {
                    "success": False,
                    "error": "PDF is password protected and cannot be opened.",
                    "pages": [],
                    "full_text": "",
                    "total_pages": 0,
                }

        total_pages = len(doc)
        extracted_pages: List[ExtractedPage] = []
        ocr_service = get_process_ocr_service() if self.ocr_enabled else None
        scanned_page_count = 0

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            try:
                page = doc[page_idx]
                raw_text = page.get_text("text") or ""
                cleaned_native = TextCleaner.clean_text(raw_text)

                # Check if native text is sufficient
                if len(cleaned_native) >= MIN_NATIVE_TEXT_THRESHOLD:
                    extracted_pages.append(
                        ExtractedPage(
                            page_number=page_num,
                            text=cleaned_native,
                            is_ocr=False,
                            char_count=len(cleaned_native),
                        )
                    )
                else:
                    # Page has insufficient or no native text -> scanned / image page
                    if self.ocr_enabled and ocr_service:
                        logger.info(f"Page {page_num} in {path.name} has insufficient native text ({len(cleaned_native)} chars). Applying OCR fallback...")
                        ocr_text = ocr_service.extract_from_page(page)
                        scanned_page_count += 1
                        extracted_pages.append(
                            ExtractedPage(
                                page_number=page_num,
                                text=ocr_text,
                                is_ocr=True,
                                char_count=len(ocr_text),
                            )
                        )
                    else:
                        extracted_pages.append(
                            ExtractedPage(
                                page_number=page_num,
                                text=cleaned_native,
                                is_ocr=False,
                                char_count=len(cleaned_native),
                            )
                        )
            except Exception as page_err:
                logger.error(f"Error extracting page {page_num} of {path.name}: {page_err}")
                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        text="",
                        is_ocr=False,
                        char_count=0,
                    )
                )

        # Extract basic document metadata
        metadata = doc.metadata or {}
        doc.close()

        full_text = "\n\n".join(
            p.text for p in extracted_pages if p.text.strip()
        )

        return {
            "success": True,
            "error": None,
            "total_pages": total_pages,
            "scanned_pages": scanned_page_count,
            "is_mixed": (scanned_page_count > 0 and scanned_page_count < total_pages),
            "is_scanned": (scanned_page_count == total_pages and total_pages > 0),
            "pages": [p.to_dict() for p in extracted_pages],
            "full_text": full_text,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
            },
        }
