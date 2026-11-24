"""
OCR Engine Service.
Provides process-local optical character recognition for scanned circulars and images.
Configured for bounded resolution (DPI=150) using the system Tesseract engine.
"""

from io import BytesIO
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Optional, Union
import fitz
from PIL import Image

from app.services.text_cleaner import TextCleaner

logger = logging.getLogger("maya.ocr_service")

# Locate Tesseract executable
TESSERACT_CMD = shutil.which("tesseract") or "tesseract"


class OCRService:
    """
    Process-local OCR engine for scanned pages and images.
    Uses Tesseract engine with bounded DPI to preserve memory.
    """

    def __init__(self, language: str = "eng", dpi: int = 150):
        self.language = language
        self.dpi = dpi
        self._is_available = self._check_tesseract()
        logger.info(f"Initialized OCRService with language='{language}', dpi={dpi}, tesseract_available={self._is_available}")

    def _check_tesseract(self) -> bool:
        """Check if Tesseract binary is executable."""
        try:
            res = subprocess.run([TESSERACT_CMD, "--version"], capture_output=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def extract_from_page(self, page: fitz.Page) -> str:
        """
        Extract text from a scanned PDF page.
        Renders at bounded DPI (150) to keep memory usage strictly controlled.
        """
        if not self._is_available:
            return ""

        temp_img_path = None
        try:
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                temp_img_path = tmp.name
                tmp.write(pix.tobytes("png"))

            # Run tesseract CLI
            cmd = [
                TESSERACT_CMD,
                temp_img_path,
                "stdout",
                "-l",
                self.language,
                "--dpi",
                str(self.dpi),
                "--oem",
                "1",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            if proc.returncode == 0 and proc.stdout:
                return TextCleaner.clean_text(proc.stdout)
            return ""
        except Exception as e:
            logger.warning(f"Tesseract OCR error on page {page.number}: {e}")
            return ""
        finally:
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.unlink(temp_img_path)
                except Exception:
                    pass

    def extract_from_image(self, image_input: Union[str, Path, Image.Image, bytes]) -> str:
        """
        Extract text from an image file (JPG, PNG, JPEG, or PIL Image).
        """
        if not self._is_available:
            return ""

        temp_img_path = None
        try:
            if isinstance(image_input, (str, Path)) and os.path.exists(str(image_input)):
                target_path = str(image_input)
            elif isinstance(image_input, Image.Image):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    temp_img_path = tmp.name
                    image_input.save(tmp, format="PNG")
                target_path = temp_img_path
            elif isinstance(image_input, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    temp_img_path = tmp.name
                    tmp.write(image_input)
                target_path = temp_img_path
            else:
                return ""

            cmd = [
                TESSERACT_CMD,
                target_path,
                "stdout",
                "-l",
                self.language,
                "--dpi",
                str(self.dpi),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            if proc.returncode == 0 and proc.stdout:
                return TextCleaner.clean_text(proc.stdout)
            return ""
        except Exception as e:
            logger.error(f"Image OCR extraction error: {e}")
            return ""
        finally:
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.unlink(temp_img_path)
                except Exception:
                    pass


# Process-local singleton cache
_local_ocr_service: Optional[OCRService] = None


def get_process_ocr_service() -> OCRService:
    """Return process-local singleton OCR service instance."""
    global _local_ocr_service
    if _local_ocr_service is None:
        _local_ocr_service = OCRService()
    return _local_ocr_service
