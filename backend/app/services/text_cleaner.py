"""
Text Cleaning and Normalization Service for University Documents.
Preserves critical identifiers, dates, enrollment numbers, and formatting while cleaning artifacts.
"""

import re
import unicodedata
from typing import Optional


class TextCleaner:
    """
    Cleans raw text extracted from PDFs, OCR, and DOCX files.
    Maintains semantic fidelity to official academic circulars.
    """

    # Preserve URLs and emails
    URL_REGEX = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    # Dates: DD-MM-YYYY, DD/MM/YYYY, etc.
    DATE_REGEX = re.compile(r"\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b")

    # Registration/Roll/Enrolment numbers: e.g. 00116403221, GGSIPU/JR/2024/101
    ENROLLMENT_REGEX = re.compile(r"\b\d{10,12}\b|\b[A-Z0-9/_-]{6,25}\b")

    @classmethod
    def clean_text(cls, text: Optional[str]) -> str:
        """
        Normalize Unicode, remove non-printable characters, clean broken line-wraps,
        and standardize whitespace while strictly preserving meaningful content.
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Replace null bytes and non-printable control characters (except newline, tab, carriage return)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", normalized)

        # 3. Fix hyphenated word breaks at end of line (e.g. "exam- \nination" -> "examination")
        cleaned = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", cleaned)

        # 4. Standardize horizontal whitespace
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # 5. Collapse excessive line breaks into maximum 2 newlines (paragraph boundary)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 6. Clean leading and trailing whitespace per line
        lines = [line.strip() for line in cleaned.split("\n")]
        cleaned = "\n".join(lines).strip()

        return cleaned

    # Alias for convenience
    clean = clean_text
