"""
DOCX and Image Document Extractor.
Extracts structured paragraphs, headings, and tables from Word documents (.docx)
and applies OCR to standalone images (.jpg, .jpeg, .png).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List
import docx

from app.services.ocr_service import get_process_ocr_service
from app.services.text_cleaner import TextCleaner

logger = logging.getLogger("maya.docx_extractor")


class DOCXExtractor:
    """Extracts text, headings, and tables from DOCX documents."""

    @classmethod
    def extract_docx(cls, file_path_str: str) -> Dict[str, Any]:
        path = Path(file_path_str)
        if not path.exists():
            return {
                "success": False,
                "error": f"DOCX file does not exist: {file_path_str}",
                "full_text": "",
                "paragraphs": [],
                "tables_count": 0,
            }

        try:
            doc = docx.Document(str(path))
            paragraphs: List[str] = []

            # Extract body paragraphs and headings
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs.append(text)

            # Extract table contents in structured row format
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        paragraphs.append(" | ".join(row_cells))

            full_text = TextCleaner.clean_text("\n\n".join(paragraphs))

            return {
                "success": True,
                "error": None,
                "full_text": full_text,
                "paragraphs_count": len(doc.paragraphs),
                "tables_count": len(doc.tables),
                "pages": [{"page_number": 1, "text": full_text, "is_ocr": False}],
                "total_pages": 1,
            }

        except Exception as e:
            logger.error(f"Error extracting DOCX {path.name}: {e}")
            return {
                "success": False,
                "error": f"DOCX extraction error: {str(e)}",
                "full_text": "",
                "paragraphs": [],
                "tables_count": 0,
            }


class ImageExtractor:
    """Extracts text from standalone images using OCR."""

    @classmethod
    def extract_image(cls, file_path_str: str) -> Dict[str, Any]:
        path = Path(file_path_str)
        if not path.exists():
            return {
                "success": False,
                "error": f"Image file does not exist: {file_path_str}",
                "full_text": "",
                "pages": [],
                "total_pages": 0,
            }

        ocr = get_process_ocr_service()
        text = ocr.extract_from_image(path)
        cleaned = TextCleaner.clean_text(text)

        return {
            "success": True,
            "error": None,
            "full_text": cleaned,
            "pages": [{"page_number": 1, "text": cleaned, "is_ocr": True}],
            "total_pages": 1,
        }
